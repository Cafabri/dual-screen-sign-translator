"""
Paso 1 — Filtrado del dataset WLASL para las 10 palabras MVP de DualSign.
Lee WLASL_v0.3.json, localiza los video_id de cada palabra y copia los .mp4
desde raw_data/videos/ a dataset/{palabra}/. Genera un log de resultados.
"""

import json
import shutil
import logging
from pathlib import Path

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
RAW_JSON    = BASE_DIR / "data" / "source" / "WLASL_v0.3.json"
VIDEOS_DIR  = BASE_DIR / "data" / "source" / "videos"
DATASET_DIR = BASE_DIR / "data" / "filtered"
LOG_FILE    = BASE_DIR / "data" / "source" / "filter_log.txt"

MVP_WORDS = ["hello", "bye", "yes", "no", "please",
             "thank you", "help", "water", "apple", "more"]

# ── Logger ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
log = logging.getLogger(__name__)


def load_mvp_instances(json_path: Path, target_words: list[str]) -> dict[str, list[str]]:
    """Devuelve un dict {gloss: [video_id, ...]} para las palabras objetivo."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    word_set = {w.lower() for w in target_words}
    instances_by_word: dict[str, list[str]] = {w: [] for w in target_words}

    for entry in data:
        gloss_lower = entry["gloss"].lower()
        if gloss_lower in word_set:
            for inst in entry["instances"]:
                instances_by_word[gloss_lower].append(inst["video_id"])

    return instances_by_word


def copy_videos(instances_by_word: dict[str, list[str]]) -> dict:
    """Copia los .mp4 a dataset/{palabra}/ y devuelve estadísticas."""
    stats = {}

    for word, video_ids in instances_by_word.items():
        word_label = word.replace(" ", "_")
        dest_dir = DATASET_DIR / word_label
        dest_dir.mkdir(parents=True, exist_ok=True)

        copied  = 0
        skipped = 0
        missing_ids = []

        for video_id in video_ids:
            src = VIDEOS_DIR / f"{video_id}.mp4"
            dst = dest_dir / f"{video_id}.mp4"

            if not src.exists():
                log.warning(f"  SKIP — {word}/{video_id}.mp4 no encontrado en raw_data/videos/")
                skipped += 1
                missing_ids.append(video_id)
                continue

            shutil.copy2(src, dst)
            log.info(f"  OK   — {word}/{video_id}.mp4 copiado")
            copied += 1

        stats[word] = {
            "total_en_json": len(video_ids),
            "copiados": copied,
            "faltantes": skipped,
            "ids_faltantes": missing_ids,
        }

    return stats


def print_summary(stats: dict) -> None:
    log.info("\n" + "=" * 60)
    log.info("RESUMEN DE FILTRADO")
    log.info("=" * 60)
    log.info(f"{'Palabra':<12} {'En JSON':>8} {'Copiados':>10} {'Faltantes':>11}")
    log.info("-" * 45)
    for word, s in stats.items():
        log.info(
            f"{word:<12} {s['total_en_json']:>8} {s['copiados']:>10} {s['faltantes']:>11}"
        )
    total_copied  = sum(s["copiados"]   for s in stats.values())
    total_missing = sum(s["faltantes"]  for s in stats.values())
    log.info("-" * 45)
    log.info(f"{'TOTAL':<12} {'':>8} {total_copied:>10} {total_missing:>11}")
    log.info("=" * 60)
    if total_missing > 0:
        log.warning(
            f"\n{total_missing} videos no encontrados — descarga raw_data/videos/ primero.\n"
            "Usa el script oficial: ia-entrenamiento/start_kit/video_downloader.py"
        )
    else:
        log.info("\nDataset MVP listo. Sin videos faltantes.")


def main() -> None:
    log.info("── DualSign · Filtrado WLASL MVP ──────────────────────────")
    log.info(f"JSON fuente : {RAW_JSON}")
    log.info(f"Videos src  : {VIDEOS_DIR}")
    log.info(f"Dataset dest: {DATASET_DIR}")
    log.info(f"Palabras MVP: {MVP_WORDS}\n")

    if not RAW_JSON.exists():
        log.error(f"No se encontró {RAW_JSON}. Abortando.")
        return

    instances_by_word = load_mvp_instances(RAW_JSON, MVP_WORDS)
    stats = copy_videos(instances_by_word)
    print_summary(stats)


if __name__ == "__main__":
    main()
