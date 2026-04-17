import StreamPanel from "./components/StreamPanel";
import MappingLegend from "./components/MappingLegend";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Gesture Control</h1>
      </header>
      <main className="app-main">
        <StreamPanel />
        <MappingLegend />
      </main>
    </div>
  );
}
