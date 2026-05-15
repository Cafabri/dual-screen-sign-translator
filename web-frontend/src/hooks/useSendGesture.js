import { useRef, useState, useCallback } from 'react';

// Wrists below shoulders for this many frames → word confirmed, stay in signing.
const WORD_SEPARATOR_FRAMES = 8;

// Wrists below shoulders for this many frames → whole phrase sent, back to idle.
const SEND_HOLD_FRAMES = 25;

// Exported so HostPage can draw the separator mark on the progress bar.
export const WORD_SEPARATOR_RATIO = WORD_SEPARATOR_FRAMES / SEND_HOLD_FRAMES;

// Minimum frames both hands must be visible before recording is recognised.
const MIN_RECORDING_FRAMES = 5;

// Left/right hand sections in the feature vector (63 values each).
const LEFT_HAND_START  = 1503;
const LEFT_HAND_END    = 1566;
const RIGHT_HAND_START = 1566;
const RIGHT_HAND_END   = 1629;

// Pose section starts at index 0. Each landmark is [x, y, z].
// Left shoulder  (pose[11]): feat[34] = y
// Right shoulder (pose[12]): feat[37] = y
// Left wrist     (pose[15]): feat[46] = y
// Right wrist    (pose[16]): feat[49] = y
const LEFT_SHOULDER_Y_IDX  = 34;
const RIGHT_SHOULDER_Y_IDX = 37;
const LEFT_WRIST_Y_IDX     = 46;
const RIGHT_WRIST_Y_IDX    = 49;

const BELOW_SHOULDER_MARGIN = 0.35;

function handSectionIsPresent(featureVector, start, end) {
  for (let i = start; i < end; i++) {
    if (featureVector[i] !== 0) return true;
  }
  return false;
}

function bothHandsPresent(featureVector) {
  return handSectionIsPresent(featureVector, LEFT_HAND_START, LEFT_HAND_END)
      && handSectionIsPresent(featureVector, RIGHT_HAND_START, RIGHT_HAND_END);
}

function bothWristsBelowShoulders(featureVector) {
  const leftShoulderY  = featureVector[LEFT_SHOULDER_Y_IDX];
  const rightShoulderY = featureVector[RIGHT_SHOULDER_Y_IDX];
  if (leftShoulderY === 0 || rightShoulderY === 0) return false;

  const leftWristY  = featureVector[LEFT_WRIST_Y_IDX];
  const rightWristY = featureVector[RIGHT_WRIST_Y_IDX];
  if (leftWristY === 0 || rightWristY === 0) return false;

  return leftWristY  > leftShoulderY  + BELOW_SHOULDER_MARGIN
      && rightWristY > rightShoulderY + BELOW_SHOULDER_MARGIN;
}

/**
 * Gesture state machine for phrase capture.
 *
 * States:
 *   idle    — both hands absent
 *   signing — both hands visible, classifier running
 *
 * While signing, wrists-below-shoulders has two thresholds:
 *   WORD_SEPARATOR_FRAMES → fires isWordSeparatorActive (add word, keep signing)
 *   SEND_HOLD_FRAMES      → fires isSendGestureActive   (send phrase, back to idle)
 *
 * Raising hands before SEND_HOLD_FRAMES resets the counter. If the separator
 * already fired in that lowering, the word stays in the phrase.
 */
function useSendGesture() {
  const handsVisibleCountRef    = useRef(0);
  const sendHoldCountRef        = useRef(0);
  const separatorFiredRef       = useRef(false); // prevent double-firing per lowering
  const isRecordingRef          = useRef(false);

  const [isRecording, setIsRecording]                   = useState(false);
  const [sendGestureProgress, setSendGestureProgress]   = useState(0);
  const [isWordSeparatorActive, setIsWordSeparatorActive] = useState(false);
  const [isSendGestureActive, setIsSendGestureActive]   = useState(false);

  const addFrame = useCallback((featureVector) => {
    if (!isRecordingRef.current) {
      // ── IDLE ──────────────────────────────────────────────────────────────
      if (bothHandsPresent(featureVector)) {
        handsVisibleCountRef.current += 1;
        if (handsVisibleCountRef.current >= MIN_RECORDING_FRAMES) {
          isRecordingRef.current = true;
          setIsRecording(true);
          handsVisibleCountRef.current = 0;
        }
      } else {
        handsVisibleCountRef.current = 0;
      }
    } else {
      // ── SIGNING ───────────────────────────────────────────────────────────
      const wristsLowered = bothWristsBelowShoulders(featureVector);

      if (wristsLowered) {
        sendHoldCountRef.current += 1;
        const progress = Math.min(sendHoldCountRef.current / SEND_HOLD_FRAMES, 1);
        setSendGestureProgress(progress);

        // Threshold 1: word separator
        if (
          sendHoldCountRef.current >= WORD_SEPARATOR_FRAMES
          && !separatorFiredRef.current
        ) {
          separatorFiredRef.current = true;
          setIsWordSeparatorActive(true);
          setTimeout(() => setIsWordSeparatorActive(false), 0);
        }

        // Threshold 2: send phrase
        if (sendHoldCountRef.current >= SEND_HOLD_FRAMES) {
          sendHoldCountRef.current = 0;
          separatorFiredRef.current = false;
          isRecordingRef.current = false;
          setSendGestureProgress(0);
          setIsRecording(false);
          setIsSendGestureActive(true);
          setTimeout(() => setIsSendGestureActive(false), 0);
        }
      } else {
        // Wrists raised again — reset counter for next lowering
        if (sendHoldCountRef.current > 0) {
          sendHoldCountRef.current = 0;
          separatorFiredRef.current = false;
          setSendGestureProgress(0);
        }
      }
    }
  }, []);

  return {
    isRecording,
    isWordSeparatorActive,
    isSendGestureActive,
    sendGestureProgress,
    addFrame,
    handsVisibleCountRef,
  };
}

export default useSendGesture;
