import sys
import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import config
from pipeline.loader import build_class_map, load_sequences_and_labels
from pipeline.preprocessor import split_and_encode, log_tensor_shapes
from model.architecture import build_lstm_model
from model.trainer import train_model
from model.evaluator import evaluate_and_save
from reporter.generator import generate_training_report


def main():
    class_map = build_class_map(config.FEATURES_DIR)
    print(f"[Data] Classes detected ({len(class_map)}): {class_map}\n")

    X, Y_raw = load_sequences_and_labels(config.FEATURES_DIR, class_map)
    print(f"[Data] Total sequences loaded: {len(X)}\n")

    X_train, X_test, Y_train, Y_test, sample_weight = split_and_encode(
        X, Y_raw, len(class_map), config.TEST_SIZE, config.RANDOM_SEED
    )
    print("[Data] Tensor shapes after split:")
    log_tensor_shapes(X_train, X_test, Y_train, Y_test)

    print("\n[Model] Building architecture...")
    model = build_lstm_model(
        num_frames=X_train.shape[1],
        num_features=X_train.shape[2],
        num_classes=Y_train.shape[1],
        learning_rate=config.LEARNING_RATE,
    )
    model.summary()

    print("\n[Model] Training started... (Ctrl+C to stop and save)\n")
    try:
        history = train_model(
            model, X_train, Y_train, X_test, Y_test,
            max_epochs=config.MAX_EPOCHS,
            patience=config.EARLY_STOPPING_PATIENCE,
            sample_weight=sample_weight,
        )
    except KeyboardInterrupt:
        print("\n[Model] Interrupted — saving current model weights...")
        model.save(config.MODEL_SAVE_PATH)
        print(f"[Model] Model saved to {config.MODEL_SAVE_PATH}. Exiting.")
        return

    test_loss, test_accuracy = evaluate_and_save(model, X_test, Y_test, config.MODEL_SAVE_PATH)

    generate_training_report(
        class_map, X_train, X_test, Y_train, Y_test,
        model, history, test_loss, test_accuracy,
        model_save_path=config.MODEL_SAVE_PATH,
        max_epochs=config.MAX_EPOCHS,
    )


if __name__ == "__main__":
    main()
