> **Module:** [`ml/scripts/extract_features.py`](../ml/scripts/extract_features.py)
> **Phase:** 2 — Feature Extraction

# Phase 2 — Biomechanical Feature Extraction with MediaPipe Holistic

**Project:** DualSign — Real-Time Bidirectional ASL Translator
**Phase:** 2 — Dataset Preparation and Feature Extraction
**Task:** 2 — Transforming Video to Mathematical Representation
**Date:** 2026-04-20

---

## 1. Executive Summary

The central objective of this task was to solve one of the fundamental problems of machine learning applied to video: **a neural network cannot learn directly from raw pixels**. A modest 640×480 video at 25 FPS generates on the order of tens of millions of values per second, making both training and real-time inference in a web context unfeasible.

The adopted solution is the **extraction of semantically rich features**: instead of feeding the network with raw visual data, only the relevant biomechanical information is extracted — the three-dimensional coordinates of key points on the human body. This process, orchestrated via MediaPipe Holistic and OpenCV, transforms each video into a compact, deterministic mathematical matrix.

The quantifiable result of this task is decisive: **88 `.mp4` video files** from a dataset whose download takes several gigabytes have been distilled into **88 NumPy matrices (`.npy`) that together occupy 16.42 MB**. These files constitute the "pure fuel" that the Phase 3 neural network will consume directly to learn to distinguish the 10 MVP vocabulary words.

---

## 2. The Visual Proof of Concept (`test_mediapipe.py`)

### 2.1 What was done

Before launching any mass extraction process, a Proof-of-Concept (PoC) script was developed that opened a single dataset video (`data/filtered/hello/27172.mp4`) and ran the MediaPipe Holistic model on it frame by frame, rendering in real time the detected "skeleton" over the original image via an OpenCV pop-up window. The hands were visualised in white and the body posture in cyan to immediately differentiate both modalities.

### 2.2 Why this prior validation was mandatory

Skipping visual validation and going straight to mass extraction is a common methodological error in ML projects that can invalidate hours of computation. The PoC allowed verifying three critical conditions before committing resources:

- **Source data quality.** WLASL videos come from 19 heterogeneous sources (ASL websites, YouTube, etc.) with very varied resolutions, camera angles, and lighting. It was necessary to confirm that the model managed to detect landmarks in at least the majority of them.

- **Correct environment setup.** The coexistence of `mediapipe 0.10.33` and `opencv-python 4.13.0.92` in the same virtual environment can produce dynamic library loading conflicts (especially on macOS with `.dylib` files). The PoC confirmed the environment was functional end-to-end.

- **BGR↔RGB flow validation.** OpenCV loads images in BGR format (blue-green-red) for historical reasons, but MediaPipe requires the standard RGB format. An error in this conversion does not raise an exception — it produces silently incorrect results. The PoC allowed visually observing that landmarks were drawn at anatomically correct positions.

### 2.3 MediaPipe Holistic vs. hands-only detection

The most obvious alternative for a sign recognition project would be to use only the `mp.solutions.hands` module. However, this choice would have been technically incorrect for the following reasons:

**Sign language is not just hands.** In ASL, as in other sign languages, linguistic information is distributed across three simultaneous channels:

- **Hands and fingers** — handshape and movement are the primary channel. The 21 landmarks per hand capture the configuration of each joint.

- **Posture and arm trajectory** — many signs are distinguished from each other solely by the location in space where they are executed (e.g. signs produced near the chest vs. signs produced near the forehead). The 33 body pose landmarks capture this spatial information.

- **Facial expression and head** — in ASL, grammar is not transmitted with hands alone. Raised eyebrows mark yes/no questions; furrowed eyebrows mark wh-questions; head negation can modify the meaning of a sign. The 468 face mesh landmarks capture these non-manual grammatical markers.

Using `Holistic` instead of `Hands` **does not significantly penalise performance**, as the model runs all these analyses in a single inference pass over the frame. Using only `Hands` would have actively discarded relevant linguistic information, degrading the discriminative capacity of the final classifier.

---

## 3. The Extraction Pipeline (`extract_features.py`)

### 3.1 High-level flow

The pipeline can be described as a chain of three successive transformations applied to each dataset video:

```
Video .mp4  →  [MediaPipe Holistic]  →  Sequence of vectors  →  [Padding/Truncation]  →  Matrix .npy
(pixels)         (inference)           (coordinates)                                    (tensor)
```

### 3.2 The anatomy of the data: from frame to vector

The heart of the pipeline is the `extract_frame_vector` function, which takes MediaPipe's inference results for a single frame and converts them into a fixed-length one-dimensional numerical vector.

For each of the four anatomical components — pose, face, left hand, and right hand — the extraction process is identical:

1. **Obtain the landmark list.** MediaPipe returns, for each component, a list of objects where each element represents a key point on the body. Each point contains three coordinates: `x` and `y` normalised to the range `[0.0, 1.0]` relative to the frame dimensions, and `z` representing relative depth (estimated distance of that point from the body's midplane).

2. **Flatten to a one-dimensional array.** The `(x, y, z)` pairs of each point are concatenated sequentially into a flat array. For the pose component, for example, the 33 points generate a vector of 99 values: `[x₁, y₁, z₁, x₂, y₂, z₂, ..., x₃₃, y₃₃, z₃₃]`.

3. **Concatenate the four blocks.** The four partial vectors are joined into a single array in a fixed, invariant order: `[pose | face | left_hand | right_hand]`. This order must remain consistent throughout the project lifetime, as the neural network will learn that positions 0–98 always correspond to pose, positions 99–1502 to face, and so on.

The resulting length table is as follows:

| Component      | Key points | Coordinates per point | Values in vector |
|----------------|:----------:|:---------------------:|:----------------:|
| Pose           | 33         | 3 (x, y, z)           | 99               |
| Face (FaceMesh)| 468        | 3 (x, y, z)           | 1,404            |
| Left hand      | 21         | 3 (x, y, z)           | 63               |
| Right hand     | 21         | 3 (x, y, z)           | 63               |
| **Total**      |            |                       | **1,629**        |

### 3.3 Handling null values: robustness against failed detections

A critical aspect of the pipeline design is the management of cases where MediaPipe does not detect any of the components in a given frame. This happens legitimately: in certain frames, a hand may be out of frame, partially occluded by the body, or moving rapidly in a way that degrades inference quality.

The naive response would be to discard those frames or treat the `None` returned by MediaPipe as an error. Neither option is correct. Discarding frames makes the video's temporal vector non-uniform. Propagating `None` interrupts the process with an exception.

The implemented solution is **zero-fill**. When `landmark_list` is `None` for a component, it is replaced by a vector of zeros with the same dimension it would have had if detected. This preserves three essential properties:

- **Constant dimensionality.** Every frame always produces exactly 1,629 values, without exception.
- **Coherent semantics.** Zero is not a valid coordinate value within the human body in MediaPipe's normalised space (real coordinates oscillate between 0.0 and 1.0). The neural network can learn to interpret blocks of zeros as "this body part was not visible in this frame".
- **No statistical bias.** Filling with the mean or random values would introduce artificial noise; zero is the most neutral representation of missing information.

### 3.4 Temporal standardisation: Padding and Truncation

#### The underlying problem

Neural networks process data organised in **tensors** (multi-dimensional arrays of fixed dimensions). A network that accepts frame sequences as input expects all training samples to have exactly the same temporal length. WLASL videos, however, have heterogeneous durations: a sign executed quickly may span barely 8–10 frames, while a slower or more didactic version of the same sign may extend to 60 or more frames.

This problem is known in ML as the **variable-length sequences problem** and requires a standardisation solution before training.

#### The fix: fixed `MAX_FRAMES = 30`

The value of 30 frames was chosen because the WLASL dataset was encoded at 25 FPS. A lexical sign in ASL typically lasts between 0.5 and 1.5 seconds, which equals 12–37 frames. A limit of 30 frames captures the vast majority of complete signs without unnecessary excess padding.

The mechanism works in two directions:

- **Truncation.** If a video contains more than 30 useful frames, the pipeline stops reading at frame 30. The beginning of the sign is preserved, where the most relevant handshape configuration information is concentrated for classification.

- **Padding.** If a video has fewer than 30 frames, enough zero vectors are appended at the end to complete the sequence. End-padding (rather than start-padding) is the standard convention to avoid perturbing the sign representation, which always begins at position 0.

The direct consequence of this standardisation is that every video, regardless of its original duration, is represented as a matrix with dimensions exactly **(30, 1,629)**. This guarantees that the future model's input tensor has a fixed, predictable shape — a sine qua non condition for training.

---

## 4. Efficiency and Storage

### 4.1 Why NumPy `.npy` instead of CSV or images

The choice of storage format has direct implications on training cycle speed. There are three common alternatives, each with different trade-offs:

**CSV (comma-separated values):** A human-readable format, but completely inadequate for high-dimensionality data. Storing a (30, 1,629) matrix in CSV would require serialising 48,870 numbers as text strings with separators, multiplying the disk size and parsing time. Each training access would involve text-to-float32 conversion, a computationally expensive operation.

**Images (JPEG/PNG):** Saving each frame as an individual image preserves visual information but contradicts the project's goal. It would save exactly the type of data from which we wanted to escape: raw pixels that require another MediaPipe pass to be useful. The training cycle would be as slow as the original extraction.

**NumPy `.npy`:** NumPy's native binary format stores the array in its exact memory representation, including type metadata (`float32`) and shape (`(30, 1629)`). Loading with `np.load()` is practically instantaneous because the file is mapped directly to RAM with no conversion step. The absence of text parsing and the memory alignment make it 10–100× faster than CSV for arrays of this size.

Furthermore, `float32` (4 bytes per value) instead of `float64` (8 bytes) halves the size with negligible precision loss for coordinates normalised in `[0.0, 1.0]`.

### 4.2 The data reduction: from gigabytes to 16.42 MB

The magnitude of the achieved compression deserves analysis:

A typical WLASL dataset video at 640×480 pixels, 25 FPS, and 3 colour channels stores approximately 23 MB of uncompressed pixel data per second of video. H.264 compression in MP4 reduces this to about 500 KB–2 MB per file, but it is still dense visual data.

Against this, each `.npy` file occupies approximately **191 KB** (30 frames × 1,629 values × 4 bytes / 1024² ≈ 0.186 MB). The pipeline extracts the essential — the skeleton of the movement — and discards all visual noise: skin texture, clothing colour, background, lighting, video compression artefacts.

This reduction has an important practical consequence: during neural network training, **loading the entire dataset into RAM simultaneously is perfectly feasible**. 16.42 MB is a trivial amount for any modern computer. This eliminates the need for on-disk batching strategies, enormously simplifying the training code and reducing data input latency to nearly zero.

---

## 5. Conclusion and Next Steps

### 5.1 What has been built

At the conclusion of this task, DualSign's data processing system has completed its preparation phase. The `data/features/` directory represents the transition from the video domain to the linear algebra domain: from ambiguous, expensive visual signals to dense, consistent numerical tensors ready for computation.

The resulting architecture of the `data/features/` folder directly reflects the structure of the classification problem:

```
data/features/
├── hello/       ← Class 0: 4 matrices (30, 1629)
├── bye/         ← Class 1: 5 matrices (30, 1629)
├── yes/         ← Class 2: 12 matrices (30, 1629)
├── no/          ← Class 3: 11 matrices (30, 1629)
├── please/      ← Class 4: 7 matrices (30, 1629)
├── thank_you/   ← Class 5: 7 matrices (30, 1629)
├── help/        ← Class 6: 14 matrices (30, 1629)
├── water/       ← Class 7: 9 matrices (30, 1629)
├── apple/       ← Class 8: 11 matrices (30, 1629)
└── more/        ← Class 9: 8 matrices (30, 1629)
```

### 5.2 How it connects to Phase 3

Phase 3 of DualSign consists of designing, training, and evaluating a neural network capable of mapping a landmark sequence to one of the 10 MVP vocabulary classes. The format of the data prepared in this task directly determines the model architecture:

- **Model input:** A tensor of shape `(batch_size, 30, 1629)`, where `batch_size` is the number of examples processed in parallel, `30` is the temporal dimension, and `1629` is the feature dimension per frame.

- **Suitable architecture type:** The temporal dimension of the input suggests using architectures designed for sequences, such as **recurrent networks** (LSTM, GRU) or **temporal Transformers**, both capable of capturing the inter-frame dependencies that encode sign movement.

- **Model output:** A vector of 10 probabilities (one per class) via a softmax layer, from which the prediction is extracted as the maximum activation index.

In short, the `data/features/` folder is not a disposable intermediate product: it is the **data contract** between the pre-processing pipeline and the learning system. All the engineering in Task 2 was designed so that this contract is simple, efficient, and extensible — properties that will directly determine the speed and quality of training in the next phase.
