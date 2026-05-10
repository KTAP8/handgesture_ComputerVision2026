import { useEffect, useRef, useState } from "react";
import { STREAM_URL } from "../api";
import GestureLabel from "./GestureLabel";

const RETRY_INTERVAL_MS = 3000;

export default function StreamPanel() {
  // Delay rendering the <img> until after mount to avoid a stale src
  // being baked in before the component is actually on the page.
  const [mounted, setMounted] = useState(false);

  // Incrementing this key forces React to remount the <img>, which
  // triggers a fresh connection to the MJPEG stream.
  const [streamKey, setStreamKey] = useState(0);

  const [showError, setShowError] = useState(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { setMounted(true); }, []);

  const scheduleRetry = () => {
    setShowError(true);
    // After the delay, hide the error state and bump the key to reconnect.
    retryTimer.current = setTimeout(() => {
      setShowError(false);
      setStreamKey((k) => k + 1);
    }, RETRY_INTERVAL_MS);
  };

  // Clean up any pending retry timer when the component unmounts.
  useEffect(() => {
    return () => { if (retryTimer.current) clearTimeout(retryTimer.current); };
  }, []);

  return (
    <div className="stream-panel">
      {showError && (
        <div className="stream-unavailable">
          <span className="stream-unavailable-icon">📷</span>
          <p>Stream unavailable</p>
          <p className="stream-unavailable-hint">
            retrying · flask:5001
          </p>
        </div>
      )}
      {mounted && (
        <img
          key={streamKey}
          src={STREAM_URL}
          alt="Webcam feed"
          style={{ display: showError ? "none" : "block" }}
          onError={scheduleRetry}
        />
      )}
      <div className="corner-marks" aria-hidden="true">
        <span className="corner tl" />
        <span className="corner tr" />
        <span className="corner bl" />
        <span className="corner br" />
      </div>
      <GestureLabel />
    </div>
  );
}
