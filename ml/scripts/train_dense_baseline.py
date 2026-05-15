import sys
import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import json
import config
from pipeline.loader import build_class_map, load_sequences_and_labels
from pipeline.preprocessor import split_and_encode
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping

DENSE_HISTORY_PATH = os.path.join("artifacts", "dashboard_data", "dense_history.json")


def build_dense_model(num_frames: int, num_features: int, num_classes: int) -> Sequential:
    model = Sequential([
        # Aplana la secuencia temporal — destruye el orden de los frames intencionalmente
        # para demostrar que sin memoria temporal el modelo no puede capturar el gesto
        Flatten(input_shape=(num_frames, num_features)),
        Dense(64, activation="relu"),
        Dropout(0.5),
        Dense(32, activation="relu"),
        Dropout(0.3),
        Dense(num_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=Adam(learning_rate=config.LEARNING_RATE),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def save_dense_history(history, test_loss: float, test_accuracy: float):
    os.makedirs(os.path.join("artifacts", "dashboard_data"), exist_ok=True)
    payload = {
        "loss":          history.history["loss"],
        "val_loss":      history.history["val_loss"],
        "accuracy":      history.history["accuracy"],
        "val_accuracy":  history.history["val_accuracy"],
        "test_loss":      test_loss,
        "test_accuracy":  test_accuracy,
    }
    with open(DENSE_HISTORY_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Dense] Historial guardado → {DENSE_HISTORY_PATH}")


def main():
    class_map = build_class_map(config.FEATURES_DIR)
    X, Y_raw = load_sequences_and_labels(config.FEATURES_DIR, class_map)

    X_train, X_test, Y_train, Y_test, _ = split_and_encode(
        X, Y_raw, len(class_map), config.TEST_SIZE, config.RANDOM_SEED
    )
    print(f"[Dense] Datos cargados — Train: {X_train.shape} | Test: {X_test.shape}\n")

    model = build_dense_model(
        num_frames=X_train.shape[1],
        num_features=X_train.shape[2],
        num_classes=Y_train.shape[1],
    )
    model.summary()

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=config.EARLY_STOPPING_PATIENCE,
        restore_best_weights=True,
    )

    print("\n[Dense] Entrenamiento iniciado...")
    history = model.fit(
        X_train, Y_train,
        validation_data=(X_test, Y_test),
        epochs=config.MAX_EPOCHS,
        callbacks=[early_stop],
        verbose=1,
    )

    test_loss, test_accuracy = model.evaluate(X_test, Y_test, verbose=0)
    print(f"\n[Dense] Test accuracy : {test_accuracy * 100:.2f}%")
    print(f"[Dense] Test loss     : {test_loss:.4f}")

    save_dense_history(history, test_loss, test_accuracy)


if __name__ == "__main__":
    main()
