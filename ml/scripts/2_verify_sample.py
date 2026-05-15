"""
Paso 2 — Verificación visual aleatoria del dataset MVP.
Para cada palabra en dataset/, selecciona 1 video al azar e imprime
su ruta relativa para poder hacer Cmd+Click / Ctrl+Click en VS Code.
"""

import random
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "data" / "filtered"

MVP_WORDS = ["hello", "bye", "yes", "no", "please",
             "thank you", "help", "water", "apple", "more"]


def pick_random_sample(word: str) -> Path | None:
    word_label = word.replace(" ", "_")
    word_dir = DATASET_DIR / word_label
    if not word_dir.exists():
        return None
    videos = list(word_dir.glob("*.mp4"))
    return random.choice(videos) if videos else None


def main() -> None:
    print("── DualSign · Verificación visual aleatoria ─────────────────")
    print(f"Directorio dataset: {DATASET_DIR}\n")

    any_found = False
    for word in MVP_WORDS:
        sample = pick_random_sample(word)
        if sample is None:
            print(f"  {'✗'} {word:<12} → sin videos en dataset/ (ejecuta 1_filter_dataset.py primero)")
        else:
            relative = sample.relative_to(BASE_DIR)
            print(f"  {'✓'} {word:<12} → {relative}")
            any_found = True

    print()
    if any_found:
        print("Abre cada ruta con Cmd+Click (Mac) o Ctrl+Click (Windows/Linux) en VS Code.")
    else:
        print("No hay videos aún. Descarga raw_data/videos/ y ejecuta 1_filter_dataset.py.")


if __name__ == "__main__":
    main()
