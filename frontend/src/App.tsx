import StreamPanel from "./components/StreamPanel";
import GestureReadout from "./components/GestureReadout";
import MappingLegend from "./components/MappingLegend";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <p className="app-header-title">
          Gesture Control
          <span>CV · 2026</span>
        </p>
        <div className="app-header-status">
          <span className="status-dot" />
          Live
        </div>
      </header>
      <main className="app-main">
        <StreamPanel />
        <div className="side-panel">
          <GestureReadout />
          <MappingLegend />
        </div>
      </main>
    </div>
  );
}
