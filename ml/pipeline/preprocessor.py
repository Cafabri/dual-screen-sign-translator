import numpy as np
from sklearn.model_selection import train_test_split
from tensorflow.keras.utils import to_categorical


def split_and_encode(X: np.ndarray, Y_raw: np.ndarray, num_classes: int, test_size: float, random_seed: int):
    Y_encoded = to_categorical(Y_raw, num_classes=num_classes)
    # stratify=Y_raw preserves class distribution across both splits
    X_train, X_test, Y_train, Y_test, sw_train, _ = train_test_split(
        X, Y_encoded, compute_sample_weights(Y_raw),
        test_size=test_size,
        random_state=random_seed,
        stratify=Y_raw,
    )
    return X_train, X_test, Y_train, Y_test, sw_train


def compute_sample_weights(Y_raw: np.ndarray) -> np.ndarray:
    class_counts = np.bincount(Y_raw)
    total = len(Y_raw)
    n_classes = len(class_counts)
    class_weights = total / (n_classes * class_counts.astype(np.float32))
    return class_weights[Y_raw].astype(np.float32)


def log_tensor_shapes(X_train, X_test, Y_train, Y_test):
    print(f"  X_train : {X_train.shape}  → (samples, frames, features)")
    print(f"  X_test  : {X_test.shape}")
    print(f"  Y_train : {Y_train.shape}  → (samples, num_classes)")
    print(f"  Y_test  : {Y_test.shape}")
