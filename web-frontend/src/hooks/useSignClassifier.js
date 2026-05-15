import { useEffect, useRef, useState, useCallback } from 'react';
import * as tf from '@tensorflow/tfjs';

const MODEL_URL = '/models/model.json';
const WINDOW_SIZE = 30;         // frames per sequence — must match training
const FEATURES_PER_FRAME = 1629;
const CONFIDENCE_THRESHOLD = 0.50;
const INFERENCE_EVERY_N_FRAMES = 5; // run inference at ~6 fps, not 30 fps

// Alphabetical order produced by sorted(os.listdir()) in data/loader.py.
// This array must stay in sync with the Python training pipeline.
const CLASS_LABELS = [
  'apple',
  'bye',
  'hello',
  'help',
  'more',
  'no',
  'please',
  'thank_you',
  'water',
  'yes',
];

/**
 * Maintains a FIFO sliding window of landmark frames and runs LSTM inference
 * whenever the window is full. Returns the top prediction when confidence
 * exceeds CONFIDENCE_THRESHOLD, or null while the model is warming up.
 */
function useSignClassifier() {
  const modelRef            = useRef(null);
  const windowBufferRef     = useRef([]); // Array of Float32Array(1629)
  const framesSinceLastRunRef = useRef(0);
  const isInferencePendingRef = useRef(false);

  const lastPredictedLabelRef       = useRef(null);
  const consecutivePredictionCount  = useRef(0);

  const [isModelReady, setIsModelReady]         = useState(false);
  const [predictedGloss, setPredictedGloss]     = useState(null);
  const [stableGloss, setStableGloss]           = useState(null);
  const [confidence, setConfidence]             = useState(0);
  const [allProbabilities, setAllProbabilities] = useState([]);

  useEffect(() => {
    tf.loadLayersModel(MODEL_URL)
      .then((model) => {
        modelRef.current = model;
        setIsModelReady(true);
      })
      .catch((err) => console.error('[Classifier] Model load failed:', err));
  }, []);

  const runInference = useCallback(async () => {
    if (isInferencePendingRef.current || !modelRef.current) return;
    if (windowBufferRef.current.length < WINDOW_SIZE) return;

    isInferencePendingRef.current = true;

    // Build a [1, 30, 1629] tensor from the current window snapshot.
    const flat = new Float32Array(WINDOW_SIZE * FEATURES_PER_FRAME);
    windowBufferRef.current.forEach((frameVector, frameIndex) => {
      flat.set(frameVector, frameIndex * FEATURES_PER_FRAME);
    });

    const inputTensor = tf.tensor3d(flat, [1, WINDOW_SIZE, FEATURES_PER_FRAME]);
    const predictionTensor = modelRef.current.predict(inputTensor);
    const probabilities = await predictionTensor.data();

    inputTensor.dispose();
    predictionTensor.dispose();

    const topIndex = probabilities.indexOf(Math.max(...probabilities));
    const topConfidence = probabilities[topIndex];

    const probabilityList = CLASS_LABELS.map((label, i) => ({
      label,
      probability: probabilities[i],
    }));

    setAllProbabilities(probabilityList);

    if (topConfidence >= CONFIDENCE_THRESHOLD) {
      const label = CLASS_LABELS[topIndex];

      // Require 2 consecutive identical predictions before promoting to stableGloss.
      // This prevents a single transient prediction (e.g. "hello" during hand lowering)
      // from overwriting a gloss the user intentionally signed.
      if (label === lastPredictedLabelRef.current) {
        consecutivePredictionCount.current += 1;
      } else {
        lastPredictedLabelRef.current = label;
        consecutivePredictionCount.current = 1;
      }

      if (consecutivePredictionCount.current >= 2) {
        setStableGloss(label);
      }

      setPredictedGloss(label);
      setConfidence(topConfidence);
    } else {
      consecutivePredictionCount.current = 0;
      lastPredictedLabelRef.current = null;
      setPredictedGloss(null);
      setConfidence(0);
    }

    isInferencePendingRef.current = false;
  }, []);

  /**
   * Called by useMediaPipe on every processed frame via onFrameReady.
   * Adds the frame to the FIFO window and triggers inference periodically.
   */
  const addFrame = useCallback((featureVector) => {
    const buffer = windowBufferRef.current;
    buffer.push(featureVector);
    if (buffer.length > WINDOW_SIZE) buffer.shift();

    framesSinceLastRunRef.current += 1;

    if (
      buffer.length === WINDOW_SIZE &&
      framesSinceLastRunRef.current >= INFERENCE_EVERY_N_FRAMES
    ) {
      framesSinceLastRunRef.current = 0;
      runInference();
    }
  }, [runInference]);

  return { isModelReady, predictedGloss, stableGloss, confidence, allProbabilities, addFrame };
}

export default useSignClassifier;
