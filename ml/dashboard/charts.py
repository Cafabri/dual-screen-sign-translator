import numpy as np
import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

COLOR_LSTM  = "#636EFA"
COLOR_DENSE = "#EF553B"


def render_accuracy_comparison(lstm_history: dict, dense_history: dict):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(lstm_history["val_accuracy"]) + 1)),
        y=lstm_history["val_accuracy"],
        name="LSTM — Val Accuracy",
        line=dict(color=COLOR_LSTM, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=list(range(1, len(dense_history["val_accuracy"]) + 1)),
        y=dense_history["val_accuracy"],
        name="Dense — Val Accuracy",
        line=dict(color=COLOR_DENSE, width=2, dash="dash"),
    ))
    fig.update_layout(
        title="LSTM vs. Red Densa — Accuracy de Validación",
        xaxis_title="Época", yaxis_title="Val Accuracy",
        yaxis=dict(tickformat=".0%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    lstm_acc  = lstm_history["test_accuracy"]  * 100
    dense_acc = dense_history["test_accuracy"] * 100
    c1, c2, c3 = st.columns(3)
    c1.metric("LSTM — Test Accuracy",  f"{lstm_acc:.2f}%")
    c2.metric("Dense — Test Accuracy", f"{dense_acc:.2f}%")
    c3.metric("Ventaja LSTM", f"+{lstm_acc - dense_acc:.2f} pp")


def render_loss_curves(lstm_history: dict):
    epochs = list(range(1, len(lstm_history["loss"]) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=epochs, y=lstm_history["loss"],
        name="Train Loss", line=dict(color=COLOR_LSTM, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=epochs, y=lstm_history["val_loss"],
        name="Val Loss", line=dict(color=COLOR_LSTM, width=2, dash="dot"),
    ))
    fig.update_layout(
        title="Efecto del Dropout — Train Loss vs. Val Loss",
        xaxis_title="Época", yaxis_title="Loss",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_confusion_matrix(cm, class_names: list):
    cm_array = np.array(cm)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm_array, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names,
        ax=ax, linewidths=0.5,
    )
    ax.set_xlabel("Predicción", fontsize=11)
    ax.set_ylabel("Verdad", fontsize=11)
    ax.set_title("Matriz de Confusión — Conjunto de Test", fontsize=13)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_softmax_distribution(softmax_data: dict, class_names: list):
    selected_word = st.selectbox("Selecciona una palabra para inspeccionar:", class_names)
    samples = softmax_data.get("samples", {})

    if selected_word not in samples:
        st.warning(f"No hay muestras de '{selected_word}' en el conjunto de test.")
        return

    probs  = samples[selected_word]
    colors = [COLOR_LSTM if i == int(np.argmax(probs)) else "#D3D3D3" for i in range(len(class_names))]

    fig = go.Figure(go.Bar(
        x=class_names, y=probs, marker_color=colors,
        text=[f"{p:.1%}" for p in probs], textposition="outside",
    ))
    fig.add_hline(
        y=0.90, line_dash="dash", line_color="red",
        annotation_text="Umbral 90%", annotation_position="top right",
    )
    fig.update_layout(
        title=f"Distribución Softmax — Muestra real: '{selected_word}'",
        xaxis_title="Clase", yaxis_title="Confianza",
        yaxis=dict(range=[0, 1.2], tickformat=".0%"),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    predicted  = class_names[int(np.argmax(probs))]
    is_correct = predicted == selected_word
    st.metric(
        "Predicción del modelo",
        f"{predicted}  ({float(np.max(probs)):.1%})",
        delta="Correcto ✓" if is_correct else f"Incorrecto — predijo '{predicted}'",
    )
