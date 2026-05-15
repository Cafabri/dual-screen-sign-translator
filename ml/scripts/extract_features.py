"""
Pipeline de extracción masiva de landmarks — DualSign Fase 2.

Lee todos los videos de dataset/, extrae los landmarks de MediaPipe Holistic
frame a frame y guarda una matriz NumPy por video en features/.

Dimensiones del vector por frame (1629 valores en total):
  Postura    : 33 puntos × 3 coords (x,y,z) =   99
  Cara       : 468 puntos × 3 coords         = 1,404
  Mano izq.  : 21 puntos × 3 coords          =   63
  Mano der.  : 21 puntos × 3 coords          =   63
  ─────────────────────────────────────────────────
  TOTAL                                      = 1,629

Forma final de la matriz por video: (MAX_FRAMES=30, 1629)
  - Videos con < 30 frames → padding con vectores de ceros al final.
  - Videos con > 30 frames → se conservan los primeros 30 frames.

Uso:
    cd ia-entrenamiento
    source venv/bin/activate
    python3 extract_features.py
"""

import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

# ── Constantes ─────────────────────────────────────────────────────────────────
MAX_FRAMES   = 30    # longitud temporal estándar (estandariza todos los videos)
FRAME_VECTOR = 1629  # 99 + 1404 + 63 + 63

BASE_DIR     = Path(__file__).parent.parent
DATASET_DIR  = BASE_DIR / "data" / "filtered"
FEATURES_DIR = BASE_DIR / "data" / "features"

# Número de puntos por componente (para construir vectores de ceros correctos)
N_POSE  = 33
N_FACE  = 468
N_HAND  = 21  # aplica a cada mano por separado

mp_holistic = mp.solutions.holistic


# ── Extracción de landmarks de un frame ───────────────────────────────────────

def landmarks_to_array(landmark_list, n_points: int) -> np.ndarray:
    """Convierte una lista de landmarks a un array plano de shape (n_points*3,).
    Si MediaPipe no detectó nada (None), devuelve ceros del mismo tamaño.
    """
    if landmark_list is None:
        return np.zeros(n_points * 3, dtype=np.float32)
    return np.array(
        [[lm.x, lm.y, lm.z] for lm in landmark_list.landmark],
        dtype=np.float32,
    ).flatten()


def extract_frame_vector(results) -> np.ndarray:
    """Concatena los cuatro bloques de landmarks en un vector de 1629 valores."""
    pose  = landmarks_to_array(results.pose_landmarks,       N_POSE)
    face  = landmarks_to_array(results.face_landmarks,       N_FACE)
    lhand = landmarks_to_array(results.left_hand_landmarks,  N_HAND)
    rhand = landmarks_to_array(results.right_hand_landmarks, N_HAND)
    return np.concatenate([pose, face, lhand, rhand])  # shape (1629,)


# ── Procesamiento de un video completo ────────────────────────────────────────

def process_video(video_path: Path, holistic) -> np.ndarray:
    """Extrae landmarks de cada frame y devuelve matriz de shape (MAX_FRAMES, 1629).

    El modelo Holistic recibido ya está inicializado (context manager externo)
    para evitar recrearlo en cada video y mejorar el rendimiento.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  [WARN] No se pudo abrir: {video_path.name} — rellenando con ceros")
        return np.zeros((MAX_FRAMES, FRAME_VECTOR), dtype=np.float32)

    frame_vectors: list[np.ndarray] = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # MediaPipe exige RGB; desactivar writeable mejora rendimiento
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = holistic.process(rgb)
        rgb.flags.writeable = True

        frame_vectors.append(extract_frame_vector(results))

        # Parar si ya tenemos suficientes frames (truncado anticipado)
        if len(frame_vectors) == MAX_FRAMES:
            break

    cap.release()

    # Padding: si hay menos frames de los requeridos, rellenar con ceros
    while len(frame_vectors) < MAX_FRAMES:
        frame_vectors.append(np.zeros(FRAME_VECTOR, dtype=np.float32))

    return np.array(frame_vectors, dtype=np.float32)  # shape (MAX_FRAMES, 1629)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not DATASET_DIR.exists():
        print(f"[ERROR] No se encontró {DATASET_DIR}")
        print("Ejecuta 1_filter_dataset.py primero.")
        sys.exit(1)

    videos = sorted(DATASET_DIR.glob("*/*.mp4"))
    total  = len(videos)

    if total == 0:
        print(f"[ERROR] No hay videos en {DATASET_DIR}")
        sys.exit(1)

    print(f"── DualSign · Extracción de Features ───────────────────────")
    print(f"Dataset : {DATASET_DIR}")
    print(f"Salida  : {FEATURES_DIR}")
    print(f"Videos  : {total}")
    print(f"Shape   : ({MAX_FRAMES}, {FRAME_VECTOR}) por video")
    print()

    FEATURES_DIR.mkdir(exist_ok=True)
    processed = 0

    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:

        for idx, video_path in enumerate(videos, 1):
            word = video_path.parent.name
            dest = FEATURES_DIR / word / f"{video_path.stem}.npy"
            dest.parent.mkdir(parents=True, exist_ok=True)

            matrix = process_video(video_path, holistic)
            np.save(dest, matrix)

            print(f"  [{idx:>3}/{total}] {word}/{video_path.name} → {matrix.shape}")
            processed += 1

    # Calcular tamaño total de features/ en MB
    total_bytes = sum(f.stat().st_size for f in FEATURES_DIR.rglob("*.npy"))
    total_mb    = total_bytes / (1024 ** 2)
    npy_count   = sum(1 for _ in FEATURES_DIR.rglob("*.npy"))

    print()
    print("=" * 55)
    print(f"  Videos procesados : {processed}/{total}")
    print(f"  Archivos .npy     : {npy_count}")
    print(f"  Tamaño features/  : {total_mb:.2f} MB")
    print("=" * 55)
    print()
    print("Verificación rápida:")
    print("  python3 -c \"import numpy as np; d=np.load('features/hello/27172.npy'); print(d.shape)\"")
    print("  → esperado: (30, 1629)")


if __name__ == "__main__":
    main()
