import { useEffect, useRef, useState } from "react";
import { STREAM_URL } from "../api";
import GestureLabel from "./GestureLabel";

const RETRY_INTERVAL_MS = 3000;

export default function StreamPanel() {
  const [streamKey, setStreamKey] = useState(0);
  const [showError, setShowError] = useState(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleRetry = () => {
    setShowError(true);
    retryTimer.current = setTimeout(() => {
      setShowError(false);
      setStreamKey((k) => k + 1); // remounts <img> to retry
    }, RETRY_INTERVAL_MS);
  };

  useEffect(() => {
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, []);

  return (
    <div className="stream-panel">
      {showError && (
        <div className="stream-unavailable">
          <span>📷</span>
          <p>Stream unavailable</p>
          <p className="stream-unavailable-hint">
            Retrying… make sure Flask is running on port 5001
          </p>
        </div>
      )}
      <img
        key={streamKey}
        src={STREAM_URL}
        alt="Webcam feed"
        style={{ display: showError ? "none" : "block" }}
        onError={scheduleRetry}
      />
      <GestureLabel />
    </div>
  );
}
