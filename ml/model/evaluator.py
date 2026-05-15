from tensorflow.keras.models import Sequential


def evaluate_and_save(model: Sequential, X_test, Y_test, save_path: str):
    loss, accuracy = model.evaluate(X_test, Y_test, verbose=0)
    print(f"\n[Model] Test loss     : {loss:.4f}")
    print(f"[Model] Test accuracy : {accuracy * 100:.2f}%")

    model.save(save_path)
    print(f"[Model] Model saved → {save_path}")

    return loss, accuracy
