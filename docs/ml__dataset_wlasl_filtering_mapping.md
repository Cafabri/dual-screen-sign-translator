> **Module:** [`ml/scripts/1_filter_dataset.py`](../ml/scripts/1_filter_dataset.py)
> **Phase:** 1 — Dataset Preparation

# Phase 1 — WLASL Dataset Filtering and Class Mapping

**Date:** 2026-04-20
**Phase:** 1 — Training Dataset Preparation
**MVP Vocabulary:** 10 core emergency-communication words

---

## 0. Data Origin and Reproducibility

The model was trained on a subset of the **WLASL (Word-Level American Sign Language)** dataset, downloaded from Kaggle in its pre-processed version:

> **Source:** [https://www.kaggle.com/datasets/risangbaskoro/wlasl-processed](https://www.kaggle.com/datasets/risangbaskoro/wlasl-processed)

The video files and the augmented dataset **are not included in this repository** due to their size. To replicate training from scratch:

1. Download the dataset from the link above and place the files in `ml/data/source/`.
2. Run `1_filter_dataset.py` to filter and organise the 88 MVP-vocabulary videos into `data/filtered/`.
3. Run `extract_features.py` to extract landmarks with MediaPipe and generate the 88 `.npy` tensors in `data/features/`.
4. Run `augment_features.py` to generate the **880 synthetic samples** (×10 Data Augmentation).
5. Run `train_model.py` to train the model. The result is saved as `modelo_dualsign.keras`.

---

## 1. Mapping Logic: JSON → MP4

The file `data/source/WLASL_v0.3.json` is the dataset's **master catalogue**. The relationship between the JSON and the video files is direct:

```
JSON                                           Disk
────────────────────────────────────────────────────────────────
entry.gloss = "hello"             →  folder data/filtered/hello/
  instance.video_id = "27171"     →  file   data/filtered/hello/27171.mp4
  instance.video_id = "70017"     →  file   data/filtered/hello/70017.mp4
  ...
```

The `video_id` field (numeric string) **is the exact filename of the `.mp4`** without extension. The script `1_filter_dataset.py`:

1. Reads the JSON and extracts all `video_id` values for each of the 10 MVP words.
2. Searches for `data/source/videos/{video_id}.mp4` on disk.
3. If found → copies it to `data/filtered/{word}/{video_id}.mp4`.
4. If not found → logs a `SKIP` in `data/source/filter_log.txt` and continues.

For compound words such as `"thank you"`, the folder is created as `data/filtered/thank_you/` (spaces → underscores) to avoid issues in shell and Python paths.

---

## 2. Filtering Statistics

> **Current status: 88 videos copied and ready for MediaPipe.**
> The 79 missing ones have expired URLs — this is not a script error.

| Word       | In JSON | Copied | Missing |
|------------|:-------:|:------:|:-------:|
| hello      | 13      | 4      | 9       |
| bye        | 7       | 5      | 2       |
| yes        | 22      | 12     | 10      |
| no         | 22      | 11     | 11      |
| please     | 15      | 7      | 8       |
| thank you  | 14      | 7      | 7       |
| help       | 22      | 14     | 8       |
| water      | 18      | 9      | 9       |
| apple      | 19      | 11     | 8       |
| more       | 15      | 8      | 7       |
| **TOTAL**  | **167** | **88** | **79**  |

### Why 79 videos are missing (and why this is not a bug)

The JSON catalogues **21,083 instances** in total. Of those, only **11,980 could be downloaded** because the rest had YouTube or external URLs that expired over time. The 11,980 files in `data/source/videos/` correspond **exactly** to 11,980 JSON entries — the mapping is 100% perfect.

Our 10 MVP words have 167 instances in the JSON. Of those, **88 are among the 11,980 downloaded** (52.7% success rate, in line with the dataset's global rate of ~57%). The remaining 79 are victims of dead URLs, not a script issue.

---

## 3. How to Recover the 79 Missing Videos (optional)

The dataset authors provide pre-processed videos on request for cases with expired URLs:

1. Run `python find_missing.py` in the official repo to generate `missing.txt`.
2. Fill in the form in the README of the `dxli94/WLASL` repo.
3. The authors send the links within ~7 days.

With the current 88 videos there is sufficient material to build and validate the MediaPipe pipeline. Recovering the 79 is a precision improvement, not a blocker.

---

## 4. Pipeline Status

| Component                                        | Status |
|--------------------------------------------------|--------|
| `data/source/WLASL_v0.3.json`                    | ✅ Ready |
| `data/source/videos/` (11,980 files)             | ✅ Ready |
| `scripts/1_filter_dataset.py`                    | ✅ Ready |
| `scripts/2_verify_sample.py`                     | ✅ Ready |
| `data/filtered/` (10 folders, 88 videos)         | ✅ Ready |
| Visual verification per word                     | ⏳ Pending (run `2_verify_sample.py`) |
| MediaPipe pipeline (landmark extraction)         | ⏳ Next phase |

---

## 5. Folder Architecture

```
ml/
├── data/
│   ├── source/
│   │   ├── WLASL_v0.3.json      ← Master catalogue (2,000 glosses / 21,083 instances)
│   │   ├── videos/              ← 11,980 downloaded source MP4s (unclassified)
│   │   └── filter_log.txt       ← Full log of each OK / SKIP
│   └── filtered/                ← Filtered dataset organised by class (88 videos)
│       ├── hello/        (4 videos)
│       ├── bye/          (5 videos)
│       ├── yes/         (12 videos)
│       ├── no/          (11 videos)
│       ├── please/       (7 videos)
│       ├── thank_you/    (7 videos)
│       ├── help/        (14 videos)
│       ├── water/        (9 videos)
│       ├── apple/       (11 videos)
│       └── more/         (8 videos)
└── scripts/
    ├── 1_filter_dataset.py      ← JSON → folder filtering script
    └── 2_verify_sample.py       ← Random visual verification script
```
