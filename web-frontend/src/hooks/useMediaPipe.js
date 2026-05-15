import { useEffect, useRef, useState } from 'react';

// @mediapipe/holistic and @mediapipe/drawing_utils are loaded as global <script>
// tags in index.html (CDN). Destructuring happens inside useEffect so React's
// module system never evaluates these before the scripts have executed.

// Must match the config used during Python feature extraction in ia-entrenamiento.
const HOLISTIC_CONFIG = {
  modelComplexity: 1,
  smoothLandmarks: true,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5,
};

const N_POSE = 33;
const N_FACE = 468;
const N_HAND = 21;

/**
 * Flattens a MediaPipe JS landmark array into [x,y,z, x,y,z, ...].
 * In the JS API, results.poseLandmarks etc. are plain arrays of {x,y,z},
 * unlike the Python API where they are objects with a .landmark property.
 * Returns a zero-filled array when MediaPipe detected nothing,
 * matching the Python training pipeline's fallback behaviour.
 */
function flattenLandmarks(landmarkArray, pointCount) {
  if (!landmarkArray || !landmarkArray.length) return new Float32Array(pointCount * 3);
  const buffer = new Float32Array(pointCount * 3);
  landmarkArray.forEach(({ x, y, z }, index) => {
    buffer[index * 3]     = x;
    buffer[index * 3 + 1] = y;
    buffer[index * 3 + 2] = z;
  });
  return buffer;
}

/**
 * Concatenates the four landmark blocks into a single 1629-value vector.
 * Order: pose (99) + face (1404) + left_hand (63) + right_hand (63).
 * This order must stay identical to extract_features.py in ia-entrenamiento.
 */
function buildFeatureVector(results) {
  const pose      = flattenLandmarks(results.poseLandmarks,      N_POSE);
  const face      = flattenLandmarks(results.faceLandmarks,      N_FACE);
  const leftHand  = flattenLandmarks(results.leftHandLandmarks,  N_HAND);
  const rightHand = flattenLandmarks(results.rightHandLandmarks, N_HAND);

  const vector = new Float32Array(
    pose.length + face.length + leftHand.length + rightHand.length
  );
  vector.set(pose,      0);
  vector.set(face,      pose.length);
  vector.set(leftHand,  pose.length + face.length);
  vector.set(rightHand, pose.length + face.length + leftHand.length);
  return vector; // Float32Array(1629)
}

function drawSkeletonOnCanvas(canvasCtx, results, canvasWidth, canvasHeight) {
  const {
    POSE_CONNECTIONS,
    FACEMESH_TESSELATION,
    HAND_CONNECTIONS,
  } = window;
  const { drawConnectors, drawLandmarks } = window;

  canvasCtx.save();
  canvasCtx.clearRect(0, 0, canvasWidth, canvasHeight);

  drawConnectors(canvasCtx, results.faceLandmarks, FACEMESH_TESSELATION,
    { color: '#C0C0C070', lineWidth: 1 });

  drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
    { color: '#00FF00', lineWidth: 2 });
  drawLandmarks(canvasCtx, results.poseLandmarks,
    { color: '#FF0000', lineWidth: 1, radius: 3 });

  drawConnectors(canvasCtx, results.leftHandLandmarks, HAND_CONNECTIONS,
    { color: '#CC0000', lineWidth: 2 });
  drawLandmarks(canvasCtx, results.leftHandLandmarks,
    { color: '#FF0000', lineWidth: 1, radius: 4 });

  drawConnectors(canvasCtx, results.rightHandLandmarks, HAND_CONNECTIONS,
    { color: '#00CC00', lineWidth: 2 });
  drawLandmarks(canvasCtx, results.rightHandLandmarks,
    { color: '#00FF00', lineWidth: 1, radius: 4 });

  canvasCtx.restore();
}

/**
 * Initialises MediaPipe Holistic and drives its frame loop.
 * WASM loads lazily on the first send() call — no initialize() needed.
 * isMediaPipeReady flips to true on the first onResults callback,
 * which confirms the WASM is fully loaded and inference is running.
 *
 * @param {React.RefObject} videoRef       — the live <video> element
 * @param {React.RefObject} canvasRef      — the overlay <canvas> element
 * @param {Function}        onFrameReady   — optional callback(Float32Array(1629))
 *                                           fired on every processed frame
 */
function useMediaPipe(videoRef, canvasRef, onFrameReady) {
  const animationFrameIdRef    = useRef(null);
  const latestFeatureVectorRef = useRef(null); // Float32Array(1629), updated every frame
  const onFrameReadyRef        = useRef(onFrameReady);
  const [isMediaPipeReady, setIsMediaPipeReady] = useState(false);

  // Keep the ref in sync so the effect closure always calls the latest callback
  // without needing to restart the MediaPipe loop on every render.
  useEffect(() => {
    onFrameReadyRef.current = onFrameReady;
  }, [onFrameReady]);

  useEffect(() => {
    const { Holistic } = window;

    const holistic = new Holistic({
      locateFile: (file) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/${file}`,
    });

    holistic.setOptions(HOLISTIC_CONFIG);

    holistic.onResults((results) => {
      // First callback confirms WASM has loaded and inference is running.
      setIsMediaPipeReady(true);

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      drawSkeletonOnCanvas(ctx, results, canvas.width, canvas.height);

      const featureVector = buildFeatureVector(results);
      latestFeatureVectorRef.current = featureVector;
      onFrameReadyRef.current?.(featureVector);
    });

    // Start the frame loop immediately — Holistic initialises the WASM
    // internally on the first send() and fires onResults when ready.
    // The try/catch ensures a single bad frame never kills the loop.
    const sendFrameLoop = async () => {
      const video = videoRef.current;
      if (video && !video.paused && video.readyState >= 2) {
        try {
          await holistic.send({ image: video });
        } catch {
          // Ignore per-frame errors and keep looping.
        }
      }
      animationFrameIdRef.current = requestAnimationFrame(sendFrameLoop);
    };

    animationFrameIdRef.current = requestAnimationFrame(sendFrameLoop);

    return () => {
      cancelAnimationFrame(animationFrameIdRef.current);
      holistic.close();
    };
  }, []);

  return { isMediaPipeReady, latestFeatureVectorRef };
}

export default useMediaPipe;
