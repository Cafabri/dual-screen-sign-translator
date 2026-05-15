import json
import os
import numpy as np
import streamlit as st
import tensorflow as tf

import config
from pipeline.loader import build_class_map, load_sequences_and_labels
from pipeline.preprocessor import split_and_encode

LSTM_HISTORY_PATH      = os.path.join("artifacts", "dashboard_data", "lstm_history.json")
DENSE_HISTORY_PATH     = os.path.join("artifacts", "dashboard_data", "dense_history.json")
CONFUSION_MATRIX_PATH  = os.path.join("artifacts", "dashboard_data", "confusion_matrix.json")
SOFTMAX_SAMPLES_PATH   = os.path.join("artifacts", "dashboard_data", "softmax_samples.json")


@st.cache_data
def load_history(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@st.cache_resource
def load_trained_model():
    if not os.path.exists(config.MODEL_SAVE_PATH):
        return None
    return tf.keras.models.load_model(config.MODEL_SAVE_PATH)


@st.cache_data
def load_test_split():
    if not os.path.exists(config.FEATURES_DIR):
        return None, None, None
    class_map = build_class_map(config.FEATURES_DIR)
    X, Y_raw = load_sequences_and_labels(config.FEATURES_DIR, class_map)
    _, X_test, _, Y_test, _ = split_and_encode(
        X, Y_raw, len(class_map), config.TEST_SIZE, config.RANDOM_SEED
    )
    return X_test, Y_test, list(class_map.keys())


@st.cache_data
def load_confusion_matrix_data() -> dict | None:
    if os.path.exists(CONFUSION_MATRIX_PATH):
        with open(CONFUSION_MATRIX_PATH) as f:
            return json.load(f)
    # Fallback: compute on the fly if model + features are present
    model = load_trained_model()
    X_test, Y_test, class_names = load_test_split()
    if model is None or X_test is None:
        return None
    import numpy as np
    from sklearn.metrics import confusion_matrix as sk_cm
    Y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    Y_true = np.argmax(Y_test, axis=1)
    cm = sk_cm(Y_true, Y_pred, labels=list(range(len(class_names)))).tolist()
    return {"cm": cm, "class_names": class_names}


@st.cache_data
def load_softmax_samples() -> dict | None:
    if os.path.exists(SOFTMAX_SAMPLES_PATH):
        with open(SOFTMAX_SAMPLES_PATH) as f:
            return json.load(f)
    # Fallback: compute on the fly if model + features are present
    model = load_trained_model()
    X_test, Y_test, class_names = load_test_split()
    if model is None or X_test is None:
        return None
    import numpy as np
    Y_true = np.argmax(Y_test, axis=1)
    samples = {}
    for idx, word in enumerate(class_names):
        indices = np.where(Y_true == idx)[0]
        if len(indices) > 0:
            probs = model.predict(X_test[indices[0]][np.newaxis, ...], verbose=0)[0].tolist()
            samples[word] = probs
    return {"class_names": class_names, "samples": samples}
