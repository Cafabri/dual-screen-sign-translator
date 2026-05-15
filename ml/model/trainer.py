from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.models import Sequential


def train_model(model: Sequential, X_train, Y_train, X_test, Y_test, max_epochs: int, patience: int, sample_weight=None):
    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=patience,
        restore_best_weights=True,
    )

    history = model.fit(
        X_train, Y_train,
        validation_data=(X_test, Y_test),
        epochs=max_epochs,
        batch_size=128,
        callbacks=[early_stop],
        verbose=1,
        sample_weight=sample_weight,
    )
    return history
