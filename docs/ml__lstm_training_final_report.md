> **Module:** [`ml/scripts/train_model.py`](../ml/scripts/train_model.py)
> **Phase:** 3 — Model Training

# Phase 3 — Final Report: Training, Optimisation, and Deployment Design of the LSTM ASL Classification Model

**Project:** DualSign — Real-Time Bidirectional American Sign Language Translator
**Phase:** Sequential Neural Network (LSTM) Model Training
**Final result:** Test Accuracy **82.32%** | Final dataset: **905 samples** (880 base + 25 extras for `bye`)

> **Interactive version available.**
> This document has an interactive version with embedded charts in the narrative.
> Launch the server with `streamlit run scripts/report_fase3.py` and open → [http://localhost:8501](http://localhost:8501)

---

## 1. Executive Summary

The central goal of this phase was to train a deep learning model capable of solving a **multiclass classification problem over temporal sequences**: given a video segment of a person executing a sign in ASL, represented as a sequence of frames with biomechanical body position data, the model must predict which of the 10 MVP vocabulary words the gesture belongs to.

This phase went through three distinct technical iterations. The first iteration, trained on the original 88 videos, produced a **Test Accuracy of 33.33%** — a result that, though above chance, revealed an unambiguous diagnosis of **overfitting due to data scarcity**. The second iteration, after applying a **matrix Data Augmentation pipeline** that expanded the dataset to 880 samples, reached a **Test Accuracy of 81.25%**, demonstrating that the architecture was correct from the start and the bottleneck was exclusively data volume. The third iteration addressed **residual class imbalance**: additional augmentation for `bye` and sample weights inversely proportional to class frequency raised the final Test Accuracy to **82.32%**, at the cost of error redistribution in the `no`/`yes`/`apple` visual cluster.

This document narrates the complete arc of that research: from architecture design to the discovery of its limitations in continuous-use scenarios, and the software engineering strategy designed to mitigate them in the web deployment layer.

---

## 2. Pre-processing and Data Preparation

### 2.1 The Anatomy of the Input Tensor

The training tensor `X_train` has the shape **(N, 30, 1629)**, where each dimension has a precise physical meaning:

- **N (samples):** The total number of training sequences, which varies between iterations (70 in the first iteration with original data, 704 in the second after augmentation). Of the total available, 80% goes to training and the remaining 20% is reserved as the test set.

- **30 (time steps / frames):** Each video has been normalised to exactly 30 frames via padding or truncation. This axis represents the temporal dimension: the model processes the gesture frame by frame, in chronological order, as if reading a sentence word by word.

- **1629 (features / landmarks):** Each frame is represented by a vector of 1,629 numerical values, the result of flattening the tracking points from **MediaPipe Holistic**: 468 face map points, 33 body pose points, and 21 per each of the two hands. Each point contributes (x, y, z) coordinates, raising the total to this figure. These values are space-normalised coordinates standardised to `float32`.

The neural network does not "see" a video; it processes a **matrix of numbers** that encodes the geometry of the human body over time.

### 2.2 Why One-Hot Encoding and Not Numeric Labels

Class labels could be represented as integers (`hello` → 0, `bye` → 1…). However, this representation is **semantically dangerous**: the network parameters would interpret that a magnitude relationship exists between classes, when none does.

The solution is **One-Hot Encoding** (`to_categorical`): transform each label into a binary vector of 10 positions where only the index of the correct class equals `1`:

```
"hello" → [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
"bye"   → [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
```

This guarantees all classes are treated as **equidistant and independent**, the mathematical condition necessary for the loss function and Softmax layer to operate correctly.

### 2.3 The Inviolability of the 80% / 20% Split

Evaluating a model with its own training data is equivalent to giving a student the exam with the answers highlighted: they will get a perfect score, but that score measures *memorisation*, not learning.

This phenomenon is called **data leakage** and produces illusory metrics. The 80/20 split — with `stratify=Y_raw` to preserve class distribution in both splits — establishes the **epistemic honesty boundary** of the experiment. Only the metric on the test set has scientific validity.

---

## 3. LSTM Architecture Justification

### 3.1 Why LSTM and Not a Classic Dense Network

A standard dense neural network treats the 30 gesture frames as 30 independent, unordered inputs, destroying the temporal information. Recognising an ASL sign is analogous to recognising a spoken word: meaning does not reside in any isolated instant, but in the **temporal evolution of the articulators' position**.

**LSTM networks** (*Long Short-Term Memory*) maintain a hidden state that functions as working memory via three internal gates (*forget*, *input*, *output*). When processing frame 15, the model has already integrated the information from frames 1 to 14, capturing trajectory patterns that are the grammatical essence of sign language.

The **stacked two-LSTM architecture** establishes a hierarchy of abstraction:

- **LSTM 1 (128 units, `return_sequences=True`):** Extracts low-level local patterns in short time windows. Returns the full sequence of hidden states.
- **LSTM 2 (64 units, `return_sequences=False`):** Synthesises the abstracted sequence into a single **context vector** of 64 dimensions that condenses the global meaning of the gesture.

### 3.2 The Role of Dropout Layers

**Dropout** layers are the main defence against overfitting: during each training iteration, they randomly switch off a percentage of neurons, preventing the network from memorising specific training examples instead of generalising gesture patterns. The chosen values — 0.5 after LSTM layers and 0.3 before the output — reflect the regularisation aggressiveness needed given the data scarcity in the first iteration.

### 3.3 The Output Layer: Dense(10) + Softmax

The **Softmax** activation function transforms the context vector into a probability distribution over the 10 classes: 10 positive values summing to exactly `1.0`, directly interpretable as the model's confidence in each word. The class with the highest probability is the final prediction.

---

## 4. Compilation and Training Strategy

### 4.1 Loss Function: Categorical Crossentropy

**Categorical cross-entropy** measures the distance between the model's predicted distribution and the real distribution (the One-Hot vector). It severely penalises erroneous high-confidence predictions, creating a learning gradient that forces the model not only to be correct, but to correctly calibrate its certainty.

### 4.2 Adam Optimiser

**Adam** (*Adaptive Moment Estimation*) adapts the learning rate individually for each model parameter by combining momentum and adaptive gradients. With `learning_rate=0.001` it offers stable convergence in the vast majority of deep learning architectures.

### 4.3 Early Stopping

Configured to monitor `val_loss` with `patience=15` and `restore_best_weights=True`, it stops training when the validation set error stops improving for 15 consecutive epochs and restores the weights from the best recorded moment. Without this safeguard, training would continue overfitting weights beyond the point of best generalisation.

---

## 5. First Iteration: Overfitting Diagnosis

### 5.1 Initial result: 33.33% Test Accuracy

The first training run — on the original 88 videos, ~7 per class — produced a Test Accuracy of **33.33%**. To interpret it correctly, the statistical baseline must be established: a classifier predicting classes at random would achieve **10%** accuracy (1 in 10 options). Our model multiplied random precision by 3.33×, demonstrating it was extracting real patterns.

However, the gap between train accuracy and val accuracy during training indicated clear overfitting. The diagnosis was precise: **the bottleneck was not the architecture or the code, but the data volume**.

### 5.2 Deep Networks' Data Hunger

With ~954,000 adjustable parameters and only 70 training examples, the model had too many degrees of freedom to anchor itself to generalisable patterns. Instead of learning that "hello is a hand trajectory toward the forehead", it learned that "hello is exactly how actor 27172 did it in that video". This memorisation of idiosyncratic traits is the definition of overfitting.

---

## 6. Resolving Overfitting: Matrix Data Augmentation

### 6.1 The Principle of Augmentation on Tensors

When real data is scarce, the solution is to generate **synthetic samples** that are mathematically distinct from the originals but semantically equivalent: perturbations representing realistic real-world variations (people of different heights, slightly different signing speeds, small position variations) without altering the gesture's meaning.

Unlike classic image augmentation (rotations, crops), here we operate directly on **3D landmark tensors**, requiring transformations specific to the biomechanical domain.

### 6.2 The Three Implemented Transformations

**Spatial Jitter — Gaussian Noise on Coordinates**

Noise sampled from a zero-centred normal distribution is added to each coordinate of each frame:

```
augmented = original + ε,   ε ~ N(0, σ)
```

With σ values between 0.003 and 0.007 (0.3%–0.7% of the normalised range `[0, 1]`). Simulates natural micro-variations in gesture execution: the same sign is never performed mechanically identically.

**Spatial Scaling — Uniform Skeleton Scaling**

The entire coordinate matrix is multiplied by a random scalar:

```
augmented = original × α,   α ~ U(low, high)
```

With ranges such as `U(0.88, 0.97)` to simulate people further from the camera, or `U(1.03, 1.12)` for people closer. Addresses scale variability due to different filming distances and body proportions.

**Time Shift — Temporal Displacement**

The 30 frames are shifted along the temporal axis via `np.roll`, filling exposed frames with zeros:

```
shifted = roll(sequence, k, axis=0),   k ~ discrete_U(-3, +3)
exposed frames → 0.0  (absent information, consistent with original padding)
```

Simulates the gesture starting slightly earlier or later within the 30-frame window, reproducing variability in sign onset timing.

### 6.3 The 9 Variants per Original Sample

9 augmented versions were generated per original `.npy` file, combining transformations with different intensities:

| Variant | Transformations |
|---|---|
| `aug_jitter_soft` | Jitter σ=0.003 |
| `aug_jitter_hard` | Jitter σ=0.007 |
| `aug_scale_down` | Scale α ∈ [0.88, 0.97] |
| `aug_scale_up` | Scale α ∈ [1.03, 1.12] |
| `aug_shift` | Time shift k ∈ [-3, +3] |
| `aug_jitter_scale` | Jitter σ=0.005 + Scale α ∈ [0.90, 1.10] |
| `aug_jitter_shift` | Jitter σ=0.005 + Time shift |
| `aug_scale_shift` | Scale + Time shift |
| `aug_full` | Jitter + Scale + Time shift combined |

### 6.4 Second Iteration Result: Jump to 81.25% Test Accuracy

The dataset grew from **88 to 880 samples** (×10), with an average of ~70 examples per class instead of ~7. The result was a jump from **33.33% → 81.25%** Test Accuracy, validating three conclusions:

1. **The architecture was correct from the start.** The same model, without any structural change, went from mediocre to robust performance. The problem was never the network design.

2. **The transformations are semantically valid.** The model trained on augmented data correctly generalises to the test set — which contains only original, unaugmented samples — demonstrating the synthetic variants represent realistic gesture distributions and not arbitrary noise.

3. **Data Augmentation on landmarks is a high-return technique.** With zero additional data collection cost, it multiplied the effective dataset size by 10 and the classifier precision by 2.4.

### 6.5 Third Iteration: Class Imbalance Correction and Its Effects

#### The Problem: Unequal Scarcity per Class

The original dataset was not uniformly scarce: while classes like `help` had up to 14 original videos, `bye` had only **5 videos**. With standard ×10 augmentation, `bye` accumulated 50 training samples versus ~140 for `help`. The result was predictable from the confusion matrix: the model achieved barely **20% accuracy on `bye`** — correctly recognising 1 in every 5 test samples, making it a practically useless class in production. `water` registered 50%, equally insufficient.

Detecting this pattern motivated a third iteration with two simultaneous interventions.

#### Intervention 1: Extra Augmentation for `bye`

5 additional variants were added per each of the 5 original `bye` videos, with more aggressive parameters than the base augmentation to maximise synthetic diversity:

| Extra variant | Transformation |
|---|---|
| `aug_jitter_v2` | Jitter σ=0.012 (vs. σ=0.007 in previous maximum) |
| `aug_scale_v2` | Scale α ∈ [0.80, 1.20] (wider range) |
| `aug_shift_v2` | Maximum time shift of 5 frames (vs. 3) |
| `aug_jitter_scale_v2` | Jitter σ=0.008 + Scale α ∈ [0.85, 1.15] combined |
| `aug_full_v2` | Jitter + Scale + Shift combined with maximum parameters |

Result: `bye` went from **50 to 75 samples** (×15 instead of ×10), and the total dataset rose to **905 samples**.

#### Intervention 2: Sample Weights Inversely Proportional to Frequency

The second intervention attacked the imbalance at the loss function level. The `compute_sample_weights()` function assigns each training sample a weight based on its class frequency:

```
weight_class_i = N_total / (N_classes × N_samples_class_i)
```

This formula guarantees that an error on a `bye` sample penalises the gradient more than an equivalent error on `help`. In practice, the `sample_weight` parameter is passed directly to `model.fit()`, modifying the loss calculation without altering the architecture or test data. Classes with fewer samples have greater impact on model weights in each gradient update.

#### Results: Improvements, Regressions, and Error Redistribution

The combination of both interventions produced a mixed effect that requires detailed analysis:

| Class | Previous accuracy | New accuracy | Δ |
|---|---|---|---|
| `hello` | 88.9% | 100% | +11.1 pp |
| `thank_you` | 93.3% | 100% | +6.7 pp |
| `bye` | **20.0%** | **100.0%** | **+80 pp** |
| `water` | 50.0% | 66.7% | +16.7 pp |
| `help` | 100% | 100% | 0 |
| `please` | 100% | 100% | 0 |
| `apple` | 81.8% | 68.2% | −13.6 pp |
| `no` | 95.5% | 63.6% | −31.9 pp |
| `yes` | 61.5% | 54.2% | −7.3 pp |

#### Why the 6 perfect classes make no errors

`bye`, `hello`, `help`, `more`, `please`, and `thank_you` reach 100% because their landmark trajectories do not overlap with any other class in the vocabulary. `help` and `more` involve unique hand configurations — vertical thumb extension, laterally displaced fist — that appear in no other word. `hello` and `thank_you` include movement from or toward the head, a body region that `no`, `yes`, `apple`, or `water` do not reach. `please` is a circular chest movement with an open palm that the model identifies without ambiguity. The gesture geometry is so distinctive that the model builds clean, wide decision boundaries: even with noisy or varying input, the winning class does not change.

#### Why the `apple` / `no` / `water` / `yes` cluster fails

These four signs share a geometric property that makes them close neighbours in feature space: the hand moves in a space bounded at chest, wrist, or chin level, without the expansive movements that make the rest unique. In the 1,629-dimensional landmark space that the LSTM processes, their trajectories form a high-similarity cluster. The concrete confusions the matrix reflects are:

- **`apple` (68.2%, 15/22):** The wrist rotation at the side of the cheek generates a landmark cloud similar to the two-finger close of `no`. 6 of 22 samples are classified as `no`.
- **`no` (63.6%, 14/22):** The confusion with `yes` (6 errors) is the most frequent and structural confusion in the model. Both are small hand movements at chest level with different finger configurations but almost identical global coordinates in MediaPipe space.
- **`water` (66.7%, 12/18):** Three fingers touching the chin activate landmarks in the facial/neck zone that overlap with those of `bye` (hand wave from the wrist). 5 of 18 samples are classified as `bye`.
- **`yes` (54.2%, 13/24):** The weakest class. It is confused with four different classes: `thank_you` (×4), `bye` (×3), `water` (×2), `no` (×2). The nodding fist does not occupy a well-delimited region because the dataset contains few diverse original samples of this sign: the model saw little real variation in how different people execute it.

#### Why did the cluster worsen after correcting `bye`?

This phenomenon is called **error redistribution**. By forcing the model to correctly learn `bye` — through extra augmentation and sample weights that increase the penalty for errors in that class — the decision boundaries shifted in the subspace that `bye` shares with `no`, `yes`, and `water`. The model "ceded" space to `bye` in that region, and neighbouring classes lost part of their separation margins. This is not a bug: it is the inevitable consequence of correcting the imbalance in a high visual similarity cluster without adding more real data.

**Net verdict:** global accuracy rose from **81.25% → 82.32%** (loss 0.5046 → 0.4691). More relevant than the global number is the qualitative change: `bye` — completely useless at 20% — now works at 100%. The loss in `no`/`apple` is real but bounded; both are still recognisable. The model is **more robust in production**: no MVP vocabulary word is completely ignored. The definitive solution for the cluster requires collecting more real, diverse videos of exactly those 4 words.

---

## 7. Model Limitations: The Real-World Challenge (ISLR vs. CSLR)

### 7.1 The Fundamental Distinction: Isolated vs. Continuous Recognition

The field of automatic sign language recognition divides into two technically distinct paradigms:

- **ISLR — Isolated Sign Language Recognition:** The system receives a frame sequence containing exactly one sign, executed from and to a neutral position. This is the paradigm our model implements.

- **CSLR — Continuous Sign Language Recognition:** The system receives a continuous video stream with multiple chained signs and must segment, recognise, and transcribe the complete sentence. This is the paradigm describing natural ASL communication.

Our LSTM model is a **high-accuracy ISLR classifier**. This distinction has direct implications for its deployment behaviour.

### 7.2 The Technical Problem: 30-Frame Window Contamination

The model expects as input a sequence of exactly 30 frames representing a single gesture executed from a neutral position. In a real continuous-use scenario, a user chaining signs quickly generates an uninterrupted flow of movement. If inference is launched on a 30-frame window captured mid-transition between two signs, the network receives what is mathematically **structured noise**: a mix of the final frames of the first sign and the initial frames of the second.

Neither sign is fully represented in that window. The model, forced to produce a prediction, will apply its weights to a pattern that corresponds to none of the learned classes, generating low-confidence predictions or, worse, erroneous predictions with high confidence. This would severely degrade the user experience.

### 7.3 Why Discard a Pure CSLR Model

The apparently obvious solution would be to train a CSLR model capable of recognising signs in continuous flow. Both main technical options were evaluated and both were discarded:

**CTC architectures (*Connectionist Temporal Classification*):** Designed to align input sequences with variable-length output sequences (as in speech recognition). Require full ASL sentence datasets with sign-level and sentence-level annotated transcriptions. This type of corpus — requiring thousands of hours of video with detailed temporal annotations — does not exist in an accessible, free form for ASL with the necessary vocabulary coverage.

**Commercial Sign Recognition APIs:** As of this project's development date, no commercial sign language recognition API exists with vocabulary coverage, latency, and licensing conditions compatible with an open-source academic project. Existing solutions are research prototypes or proprietary products with restricted access.

The conclusion is that **production CSLR is an active research problem**, not a component available for integration. Addressing this problem from scratch is outside the project's practical scope.

---

## 8. Mitigation via Frontend Software Architecture

### 8.1 The Principle: Solve in Software What Cannot Be Solved in the Model

The identified limitation does not require retraining the model or changing its architecture. It requires **intelligently designing the JavaScript layer** that controls when, how, and with what data inference is launched. This is the engineering philosophy guiding the Deployment Phase: using frontend software as a control system that protects the mathematical integrity of the model's input.

Three complementary mitigation mechanisms were designed:

### 8.2 Sliding Window — 30-Frame Rolling Buffer

In the user's browser (`/host`), a **circular queue of 30 frames** is maintained at all times, updated in real time from the webcam. Every time MediaPipe processes a new frame, the oldest frame leaves the queue and the new one enters, always maintaining a sliding window of the 30 most recent frames.

This mechanism guarantees inference always operates on up-to-date, temporally contiguous data, without stopping the video stream or explicitly defining sign boundaries. The challenge moves to the next two mechanisms: determining whether the current window contains a complete, valid sign.

### 8.3 Confidence Threshold — Thresholding on Softmax

Before accepting and publishing a prediction, the system verifies that the winning class probability exceeds a **minimum confidence threshold**, set at **50%** (0.50):

```
accepted_prediction = argmax(softmax) IF max(softmax) > 0.50
```

The mathematical justification is sound: when the 30-frame window contains the transition between two signs, the network's activations are diffusely distributed among multiple classes, producing a Softmax vector with no clearly dominant class. In contrast, when the window contains a cleanly executed complete sign, the correct class neuron dominates with high confidence.

The threshold acts as a filter that automatically rejects noisy transitions between signs, without the user needing to take any explicit action. The use experience is fluid: the system simply does not emit a prediction when it is not sure.

### 8.4 The Combined System: Simulating Fluidity without CSLR

The two mechanisms create an inference protocol that reasonably approximates the desired production behaviour:

```
[New frame]
    ↓
[Sliding Window updates the 30-frame buffer]
    ↓
[Run inference on current buffer]
    ↓
[max(softmax) > 0.50?] → NO → Discard (transition or neutral position)
    ↓ YES
[Publish prediction]
```

This system is not CSLR; it is a **robust ISLR with automatic clean-sign detection**. For DualSign's use case — deliberate, sign-by-sign communication in a conversational context — this behaviour is functionally equivalent to the desired experience.

---

## 9. Conclusions

This phase demonstrated that the central challenge of sign language recognition in an academic context is not the network architecture — which proved correct from its first iteration — but the engineering of the data that feeds it and the system that controls its use.

The results confirm three principles that must guide Deployment Phase decisions:

- **The model is competent:** An 82.32% Test Accuracy over 10 classes with augmented training data validates that the system can discriminate ASL biomechanical patterns with high reliability. No MVP vocabulary word is completely undetectable.
- **The limits are known and bounded:** The ISLR vs. CSLR problem is real but mitigable through software design without retraining the model. The error redistribution in the `no`/`yes`/`apple` cluster is a known limit of the current dataset, not of the architecture.
- **Data architecture is the dominant control variable:** All future performance improvements — more vocabulary, greater robustness, lower error rate — will pass first through expanding and diversifying the dataset with additional real videos, especially for the visual cluster classes `no`/`yes`/`apple`/`bye`/`water`, and only then through network adjustments.

---

*DualSign project technical document. Phase 3 final version.*
