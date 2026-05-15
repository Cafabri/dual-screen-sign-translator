from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam


def build_lstm_model(num_frames: int, num_features: int, num_classes: int, learning_rate: float) -> Sequential:
    model = Sequential([
        # LSTM 1: recibe la secuencia completa frame a frame y la pasa íntegra a la siguiente capa
        LSTM(128, return_sequences=True, input_shape=(num_frames, num_features)),
        Dropout(0.5),

        # LSTM 2: consume la secuencia y la comprime en un único vector de contexto
        LSTM(64, return_sequences=False),
        Dropout(0.5),

        # Dense intermedia: razona sobre el vector de contexto antes de clasificar
        Dense(64, activation="relu"),
        Dropout(0.3),

        # Output: una probabilidad por cada clase (palabra del MVP)
        Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
        jit_compile=False,
    )
    return model
