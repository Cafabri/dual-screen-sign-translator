import io
import json
import os
from datetime import datetime
import numpy as np
from sklearn.metrics import confusion_matrix as sk_confusion_matrix
from tensorflow.keras.models import Sequential

LOGS_DIR = os.path.join("..", "docs", "training_logs")
DASHBOARD_DATA_DIR = os.path.join("artifacts", "dashboard_data")


def capture_model_summary(model: Sequential) -> str:
    buffer = io.StringIO()
    model.summary(print_fn=lambda line: buffer.write(line + "\n"))
    return buffer.getvalue()


def build_epoch_table(history) -> str:
    epochs_ran = len(history.history["loss"])
    return "\n".join([
        f"| {i + 1} | {history.history['loss'][i]:.4f} | {history.history['accuracy'][i]:.4f} "
        f"| {history.history['val_loss'][i]:.4f} | {history.history['val_accuracy'][i]:.4f} |"
        for i in range(epochs_ran)
    ])


def build_class_table(class_map: dict) -> str:
    return "\n".join(f"| `{word}` | {idx} |" for word, idx in class_map.items())


def generate_training_report(
    class_map: dict,
    X_train, X_test, Y_train, Y_test,
    model: Sequential,
    history,
    test_loss: float,
    test_accuracy: float,
    model_save_path: str,
    max_epochs: int,
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_filename = os.path.join(LOGS_DIR, log_filename)

    epochs_ran = len(history.history["loss"])
    best_val_accuracy = max(history.history["val_accuracy"])
    best_val_loss = min(history.history["val_loss"])

    report = f"""# Log de Ejecución — Entrenamiento LSTM ({datetime.now().strftime('%Y-%m-%d')})

**Fecha:** {timestamp}
**Modelo guardado en:** `{model_save_path}`

---

## Clases del Modelo ({len(class_map)})

| Palabra | Índice |
|---------|--------|
{build_class_table(class_map)}

---

## Dimensiones de los Tensores

| Tensor | Shape |
|--------|-------|
| X_train | `{X_train.shape}` |
| X_test  | `{X_test.shape}` |
| Y_train | `{Y_train.shape}` |
| Y_test  | `{Y_test.shape}` |

---

## Arquitectura de la Red

```
{capture_model_summary(model)}
```

---

## Resultados del Entrenamiento

| Métrica | Valor |
|---------|-------|
| Épocas ejecutadas | {epochs_ran} / {max_epochs} |
| Mejor `val_accuracy` | {best_val_accuracy * 100:.2f}% |
| Mejor `val_loss` | {best_val_loss:.4f} |
| **Test accuracy final** | **{test_accuracy * 100:.2f}%** |
| **Test loss final** | **{test_loss:.4f}** |

---

## Historial por Época

| Época | Loss | Accuracy | Val Loss | Val Accuracy |
|-------|------|----------|----------|--------------|
{build_epoch_table(history)}
"""

    with open(report_filename, "w", encoding="utf-8") as report_file:
        report_file.write(report)

    print(f"[Reporter] Log guardado → {report_filename}")

    _save_history_json(history, test_loss, test_accuracy)
    _save_confusion_matrix_json(model, X_test, Y_test, class_map, test_accuracy)
    _save_softmax_samples_json(model, X_test, Y_test, class_map)


def _save_history_json(history, test_loss: float, test_accuracy: float):
    os.makedirs(DASHBOARD_DATA_DIR, exist_ok=True)
    payload = {
        "loss":         history.history["loss"],
        "val_loss":     history.history["val_loss"],
        "accuracy":     history.history["accuracy"],
        "val_accuracy": history.history["val_accuracy"],
        "test_loss":     test_loss,
        "test_accuracy": test_accuracy,
    }
    path = os.path.join(DASHBOARD_DATA_DIR, "lstm_history.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Reporter] Historial JSON guardado → {path}")


def _save_confusion_matrix_json(model, X_test, Y_test, class_map: dict, test_accuracy: float):
    os.makedirs(DASHBOARD_DATA_DIR, exist_ok=True)
    Y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    Y_true = np.argmax(Y_test, axis=1)
    class_names = list(class_map.keys())
    cm = sk_confusion_matrix(Y_true, Y_pred, labels=list(range(len(class_names))))
    payload = {
        "cm": cm.tolist(),
        "class_names": class_names,
        "test_accuracy": test_accuracy,
    }
    path = os.path.join(DASHBOARD_DATA_DIR, "confusion_matrix.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Reporter] Matriz de confusión JSON guardada → {path}")


def _save_softmax_samples_json(model, X_test, Y_test, class_map: dict):
    os.makedirs(DASHBOARD_DATA_DIR, exist_ok=True)
    class_names = list(class_map.keys())
    Y_true = np.argmax(Y_test, axis=1)
    samples = {}
    for idx, word in enumerate(class_names):
        indices = np.where(Y_true == idx)[0]
        if len(indices) > 0:
            probs = model.predict(X_test[indices[0]][np.newaxis, ...], verbose=0)[0].tolist()
            samples[word] = probs
    payload = {"class_names": class_names, "samples": samples}
    path = os.path.join(DASHBOARD_DATA_DIR, "softmax_samples.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[Reporter] Muestras softmax JSON guardadas → {path}")
