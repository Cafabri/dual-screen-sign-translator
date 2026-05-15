"""
PoC Visual — MediaPipe Holistic sobre un video del dataset DualSign MVP.

Objetivo: confirmar visualmente que MediaPipe detecta manos y postura
correctamente en nuestros videos antes de lanzar la extracción masiva.

Uso:
    cd ia-entrenamiento
    source venv/bin/activate
    python3 test_mediapipe.py

Controles: presiona 'q' para salir antes de que termine el video.
"""

import sys
from pathlib import Path

import cv2
import mediapipe as mp

# ── Video de prueba estático ───────────────────────────────────────────────────
# Usamos el primer video disponible en dataset/hello/
TEST_VIDEO = Path(__file__).parent.parent / "data" / "filtered" / "hello" / "27172.mp4"

# ── Inicialización de MediaPipe ────────────────────────────────────────────────
mp_holistic = mp.solutions.holistic
mp_drawing  = mp.solutions.drawing_utils

# Estilos visuales para diferenciar manos (blanco) y postura (cian)
hand_style = mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=3)
pose_style = mp_drawing.DrawingSpec(color=(0, 255, 255),  thickness=2, circle_radius=2)


def print_video_info(cap: cv2.VideoCapture, path: Path) -> None:
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video  : {path}")
    print(f"Tamaño : {width}x{height}  |  FPS: {fps:.1f}  |  Frames totales: {frames}")
    print("Presiona 'q' para salir.\n")


def run_poc() -> None:
    if not TEST_VIDEO.exists():
        print(f"[ERROR] Video no encontrado: {TEST_VIDEO}")
        print("Asegúrate de haber ejecutado 1_filter_dataset.py primero.")
        sys.exit(1)

    cap = cv2.VideoCapture(str(TEST_VIDEO))
    if not cap.isOpened():
        print(f"[ERROR] OpenCV no pudo abrir el video: {TEST_VIDEO}")
        sys.exit(1)

    print_video_info(cap, TEST_VIDEO)

    # Holistic detecta manos + postura + cara en un solo pase
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # El video terminó normalmente
                break

            # MediaPipe requiere RGB; OpenCV entrega BGR por defecto
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Procesamos el frame con el modelo (desactivar writeable mejora perf)
            rgb_frame.flags.writeable = False
            results = holistic.process(rgb_frame)
            rgb_frame.flags.writeable = True

            # Convertir de vuelta a BGR para dibujar con OpenCV
            bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

            # Dibujar esqueleto de mano izquierda
            mp_drawing.draw_landmarks(
                bgr_frame,
                results.left_hand_landmarks,
                mp_holistic.HAND_CONNECTIONS,
                hand_style, hand_style,
            )

            # Dibujar esqueleto de mano derecha
            mp_drawing.draw_landmarks(
                bgr_frame,
                results.right_hand_landmarks,
                mp_holistic.HAND_CONNECTIONS,
                hand_style, hand_style,
            )

            # Dibujar postura del cuerpo (brazos, hombros, etc.)
            mp_drawing.draw_landmarks(
                bgr_frame,
                results.pose_landmarks,
                mp_holistic.POSE_CONNECTIONS,
                pose_style, pose_style,
            )

            cv2.imshow("MediaPipe PoC — DualSign", bgr_frame)

            # Salir si el usuario presiona 'q'
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Salida manual por el usuario.")
                break

    cap.release()
    cv2.destroyAllWindows()
    print("PoC completado. Ventana cerrada.")


if __name__ == "__main__":
    run_poc()
