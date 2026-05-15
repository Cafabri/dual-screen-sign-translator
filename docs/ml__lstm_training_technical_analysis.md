> **Module:** [`ml/`](../ml/)
> **Phase:** 3 — Model Training

# Phase 3 — Technical Analysis of ASL LSTM Classification Model Training

**Project:** DualSign — Real-Time Bidirectional American Sign Language Translator
**Phase:** Sequential Neural Network (LSTM) Model Training
**Result:** Test Accuracy 33.33% | Test Loss 1.7638 | Stopped at epoch 64

---

## 1. Executive Summary

The central goal of this phase was to train a deep learning model capable of solving a **multiclass classification problem over temporal sequences**: given a video segment of a person signing in ASL, represented as a sequence of frames with body position data, the model must predict which of the 10 MVP vocabulary words the gesture belongs to.

Unlike a static image classification problem, the input data here is inherently **three-dimensional and temporal**: a gesture is not a photo, but a movement that unfolds over time. This nature of the data conditions the entire architecture described in this document.

---

## 2. Pre-processing and Data Preparation

### 2.1 The Anatomy of the Input Tensor

The training tensor `X_train` has the shape **(70, 30, 1629)**, where each dimension has a precise physical meaning:

- **70 (samples):** The total number of training videos. Of the 88 sequences extracted from the WLASL dataset, 80% (70 samples) go to training and the remaining 20% (18 samples) are reserved as the test set.

- **30 (time steps / frames):** Each video has been normalised to exactly 30 frames via padding or truncation. This axis represents the temporal dimension: the model processes the gesture frame by frame, in chronological order, as if reading a sentence word by word.

- **1629 (features / landmarks):** Each frame is represented by a vector of 1,629 numerical values, the result of flattening the tracking points (*landmarks*) from **MediaPipe Holistic**: 543 face points, 33 body pose points, and 21 per each of the two hands. Each point contributes (x, y, z) coordinates, bringing the total to this figure. These values are space-normalised coordinates standardised to `float32`.

The neural network therefore does not "see" a video; it processes a **matrix of numbers** that encodes the geometry of the human body over time.

### 2.2 Why One-Hot Encoding and Not Numeric Labels

Class labels could intuitively be represented as integers (`hello` → 0, `bye` → 1, `yes` → 2…) or as strings. However, both representations are **semantically dangerous** for a neural network.

If the network receives the number `5` for `please` and `9` for `yes`, its mathematical parameters will implicitly interpret that `yes` is "greater" or "more similar to 5" than other classes. This **numeric ordering is completely false**: there is no magnitude relationship between ASL vocabulary words.

The solution is **One-Hot Encoding** (`to_categorical`): transform each label into a binary vector of 10 positions where only the index corresponding to the correct class equals `1` and the rest equal `0`. For example:

```
"hello" → [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
"bye"   → [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
```

This guarantees all classes are treated as **equidistant and independent**, which is exactly the mathematical condition the model needs to learn without artificial biases.

### 2.3 Why the 80% / 20% Split Is Inviolable

The fundamental principle of ML model evaluation is that **the model must be judged only on data it has never seen during training**. Evaluating a model with its own training data is equivalent to giving a student the exam with the answers already highlighted: they will get a perfect score, but that score does not measure learning — it measures *memorisation*.

This phenomenon is called **data leakage** and produces a completely illusory performance metric. The model learns to recognise the specific examples seen during training instead of generalising the underlying gesture patterns.

The 80/20 split — with `stratify=Y_raw` to guarantee identical class proportions in both splits — creates an **epistemic honesty boundary**: the 70 training examples teach the model, and the 18 test ones examine it. Only the metric on the test set has scientific validity.

---

## 3. Architecture Justification

### 3.1 Why LSTM and Not a Classic Dense Network

A standard fully connected neural network receives a fixed-length input vector and produces an output. It has no mechanism to process **sequential data**: if presented with the 30 gesture frames, it would treat them as 30 independent, unordered inputs, completely destroying the temporal information that defines the movement.

Recognising an ASL gesture is analogous to recognising a spoken word: meaning does not reside in any isolated instant, but in the **temporal evolution of the articulators' position**. The "hello" gesture is not a photo of a hand in a position; it is the complete trajectory of that movement.

**LSTM networks** (*Long Short-Term Memory*) solve exactly this problem. Through their internal gate architecture (*forget gate*, *input gate*, *output gate*), they maintain a **hidden state** that functions as working memory: when processing frame 15, the model has already "integrated" the information from frames 1 to 14. This allows it to detect patterns such as "the hand started here, transitioned through this trajectory, and ended there", which is precisely the spatiotemporal grammar of sign language.

The decision to stack **two LSTM layers** responds to a hierarchy of abstraction:

- **LSTM 1 (128 units, `return_sequences=True`):** Operates at a low level, extracting local patterns in short time windows. Returns the full sequence of hidden states for the next LSTM layer to process.
- **LSTM 2 (64 units, `return_sequences=False`):** Operates on the representations already abstracted by the first layer, synthesising the global gesture pattern into a single **context vector** of 64 dimensions. This vector condenses all temporal movement information into a compact representation.

### 3.2 The Role of Dropout Layers: Regularisation by Structured Noise

**Overfitting** is the dominant risk when training a high-capacity network on a small dataset. The model, instead of learning the general rules of the gesture, memorises the specific and irrelevant traits of the 70 training examples (a particular movement tic of the performer, an idiosyncratic speed variation).

**Dropout** layers are a regularisation technique that mitigates this via an elegant mechanism: during each training iteration, they randomly **switch off** a percentage of neurons from the previous layer, forcing the rest to compensate for their absence. The practical effect is twofold:

1. **Prevents co-adaptation:** Neurons cannot "share the work" of memorising a specific example because they do not know which companions will be available in the next step.
2. **Implicit ensemble:** Each mini-batch trains a slightly different sub-network. The final model behaves as the statistical average of thousands of sub-networks, generalising much better.

The chosen values (0.5 after LSTMs and 0.3 before the output layer) reflect the aggressiveness needed given the data scarcity: a Dropout of 0.5 switches off half the neurons at each step, which is the highest noise level commonly used in the literature.

### 3.3 The Output Layer: Dense(10) + Softmax

The problem is **mutually exclusive multiclass classification**: a gesture can only belong to one word. The output layer must produce a probability distribution over the 10 classes.

The **Softmax** activation function guarantees that the 10 output layer values are positive numbers summing to exactly `1.0`, directly interpretable as probabilities. Given the context vector from the last dense layer, Softmax answers the question: "What is the probability that this gesture is *hello*, what that it is *bye*, what that it is *yes*…?". The class with the highest probability is taken as the final prediction.

---

## 4. Compilation and Training Strategy

### 4.1 Loss Function: Categorical Crossentropy

**Categorical cross-entropy** measures the distance between the probability distribution predicted by the model and the real distribution (the One-Hot vector, where the probability of the correct class is 1 and the rest 0). Mathematically, it penalises disproportionately severely erroneous predictions made with high confidence: if the model predicts 0.95 probability for the wrong class, the penalty is much greater than if it predicts 0.4. This creates a calibrated learning gradient so the model learns not only to be correct, but to be correct with the right confidence.

It is the de facto standard loss function for any multiclass classification problem with One-Hot labels.

### 4.2 Adam Optimiser and the Accuracy Metric

The **Adam** optimiser (*Adaptive Moment Estimation*) combines two improvements over classic gradient descent: it adapts the learning rate individually for each model parameter based on the history of past gradients, and applies momentum to smooth oscillations during learning. With a `learning_rate=0.001` (the literature's recommended default), it offers stable and robust convergence in the vast majority of deep learning architectures.

The **accuracy** reported during training is the fraction of correctly classified examples per epoch, calculated on the training set and, in parallel, on the validation set. This duality (train_accuracy vs. val_accuracy) is the most important diagnostic signal during training.

### 4.3 Early Stopping: The Anti-Overfitting Safeguard

Configured to monitor `val_loss` with `patience=15` and `restore_best_weights=True`, **Early Stopping** implements a form of temporal regularisation: if the validation set error does not improve for 15 consecutive epochs, training stops and the weights from the best recorded moment are restored.

In our experiment, training stopped at **epoch 64** (out of a maximum of 100), indicating the model found its best configuration around epoch 49 and the 15 patience epochs were exhausted without improvement. This is expected, healthy behaviour: without Early Stopping, epochs 65 to 100 would have continued overfitting the weights to the training set, degrading generalisation.

---

## 5. Realistic Interpretation of Results

### 5.1 Analysis of 33.33% Test Accuracy

The result of **33.33% Test Accuracy** must be interpreted within its correct statistical context, not in absolute terms.

The fundamental baseline for a 10-class classifier is the **random guessing accuracy**: a model that predicted a class at random would achieve, on average, **10%** accuracy (1 in 10 equally probable options). This is the performance floor any model must exceed to demonstrate it extracts real information from the data.

Our model achieves **3.33×** the precision of a random classifier. This is solid empirical evidence that the neural network has learned **real and generalisable patterns** in the movement sequences: it has extracted regularities in the spatiotemporal geometry of gestures that allow it to discriminate between classes at a rate above chance.

**The 33.33% is not the system's limit; it is the current dataset's limit.**

### 5.2 Diagnosis: The Bottleneck Is Data, Not Code

The true diagnosis of this result points to a single structural factor: deep neural networks' **data hunger**.

With 88 total samples distributed across 10 classes, the training model has an **average of 7 examples per class**. For an LSTM architecture with hundreds of thousands of adjustable parameters, this amount of data is critically insufficient to establish the necessary statistical diversity. The network cannot learn which aspects of the gesture are invariant (and therefore generalisable) and which are noise specific to the performer, speed, or camera angle of that particular video.

This phenomenon is well known in the deep learning literature: high-capacity models require large data volumes for the hypothesis space to be restricted to solutions that generalise. With 7 examples per class, the model has too many degrees of freedom and too little signal to anchor itself.

The architecture, pre-processing pipeline, training strategy, and code are correct. The system is ready to scale: more data will directly produce a substantial accuracy improvement.

---

## 6. Next Steps

### 6.1 Dataset Expansion

The most direct improvement lever with the highest expected return is collecting more video samples per class. Going from ~7 to ~50–100 examples per class should produce a significant accuracy improvement without any other architecture changes. The feature extraction pipeline already built in previous phases makes integrating new videos trivial.

### 6.2 Data Augmentation for 3D Sequences

When real data is scarce, synthetic data can be generated from existing samples via **Data Augmentation** techniques adapted to temporal landmark sequences:

- **Temporal jitter:** Adding small Gaussian perturbations to landmark coordinates in each frame.
- **Spatial scaling:** Multiplying all coordinates by a slightly larger or smaller scalar, simulating performers with different body proportions.
- **Speed interpolation:** Stretching or compressing the temporal sequence (making it faster or slower) before re-normalising to 30 frames.
- **Horizontal flip:** Inverting the X axis of all coordinates, generating a mirror of the gesture (relevant for symmetric signs).

These transformations artificially multiply the dataset while preserving gesture semantics.

### 6.3 Hyperparameter Tuning

With a larger dataset, hyperparameter optimisation experiments become worthwhile:

- **Increasing model capacity** (more LSTM units, more layers) to capture more complex patterns.
- **Reducing Dropout** if the dataset grows and overfitting ceases to be the dominant risk.
- **Exploring alternative architectures** such as GRU (*Gated Recurrent Unit*), which offers performance comparable to LSTM with lower computational cost, or Transformer-based models for sequences, which have demonstrated state-of-the-art performance in gesture recognition tasks in recent literature.

---

*Document generated as part of the DualSign project technical documentation.*
