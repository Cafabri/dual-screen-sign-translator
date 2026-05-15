import sys
import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import streamlit as st
from dashboard.loaders import (
    load_history, load_confusion_matrix_data, load_softmax_samples,
    LSTM_HISTORY_PATH, DENSE_HISTORY_PATH,
)
from dashboard.charts import (
    render_accuracy_comparison, render_loss_curves,
    render_confusion_matrix, render_softmax_distribution,
)

def main():
    st.set_page_config(
        page_title="DualSign — Panel de Análisis",
        page_icon="🤟",
        layout="wide",
    )
    st.title("🤟 DualSign — Panel de Análisis del Modelo LSTM")
    st.caption("Vocabulario ASL · 10 palabras · LSTM(128) → LSTM(64) → Dense(10, Softmax)")
    st.divider()

    lstm_history  = load_history(LSTM_HISTORY_PATH)
    dense_history = load_history(DENSE_HISTORY_PATH)
    cm_data       = load_confusion_matrix_data()
    softmax_data  = load_softmax_samples()
    class_names   = cm_data["class_names"] if cm_data else (
        softmax_data["class_names"] if softmax_data else []
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("① LSTM vs. Red Densa")
        if lstm_history and dense_history:
            render_accuracy_comparison(lstm_history, dense_history)
        else:
            missing = []
            if not lstm_history:  missing.append("`scripts/train_model.py`")
            if not dense_history: missing.append("`scripts/train_dense_baseline.py`")
            st.info(f"Ejecuta {' y '.join(missing)} para generar los datos.")

    with col_right:
        st.subheader("② Efecto del Dropout")
        if lstm_history:
            render_loss_curves(lstm_history)
        else:
            st.info("Ejecuta `scripts/train_model.py` primero.")

    st.divider()

    st.subheader("③ Matriz de Confusión")
    if cm_data is not None:
        render_confusion_matrix(cm_data["cm"], cm_data["class_names"])
    else:
        st.info("Ejecuta `scripts/train_model.py` para generar los datos.")

    st.divider()

    st.subheader("④ Distribución de Confianza (Softmax)")
    if softmax_data is not None:
        render_softmax_distribution(softmax_data, softmax_data["class_names"])
    else:
        st.info("Ejecuta `scripts/train_model.py` para generar los datos.")


if __name__ == "__main__":
    main()
