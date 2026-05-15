import { useRef, useState, useEffect } from 'react';

const CAMERA_CONSTRAINTS = {
  video: { facingMode: 'user', width: 640, height: 480 },
  audio: false,
};

function useWebcam() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [cameraError, setCameraError] = useState(null);

  const startVideoStreaming = async () => {
    if (streamRef.current) return;

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
      streamRef.current = mediaStream;

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }

      setIsStreaming(true);
      setCameraError(null);
    } catch (error) {
      const isDenied = error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError';
      setCameraError(isDenied
        ? 'Camera access was denied. Please allow camera permissions and reload.'
        : `Could not access camera: ${error.message}`
      );
    }
  };

  const stopVideoStreaming = () => {
    if (!streamRef.current) return;

    streamRef.current.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsStreaming(false);
  };

  useEffect(() => {
    return () => stopVideoStreaming();
  }, []);

  return { videoRef, isStreaming, cameraError, startVideoStreaming, stopVideoStreaming };
}

export default useWebcam;
