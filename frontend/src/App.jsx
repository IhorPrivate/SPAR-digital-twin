import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import CellRail from "./components/CellRail";
import HealthChart from "./components/HealthChart";
import MetricsPanel from "./components/MetricsPanel";
import TwinPanel from "./components/TwinPanel";
import { mergeSeries, withForecast } from "./format";

export default function App() {
  const [health, setHealth] = useState(null);
  const [cells, setCells] = useState([]);
  const [selected, setSelected] = useState(null);
  const [cycles, setCycles] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [twin, setTwin] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [training, setTraining] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const trained = Boolean(health?.trained);

  const loadCell = useCallback(async (cellId, isTrained) => {
    setError(null);
    try {
      setCycles(await api.cycles(cellId));
      if (isTrained) {
        const [p, t] = await Promise.all([api.predictions(cellId), api.twin(cellId)]);
        setPredictions(p);
        setTwin(t);
      } else {
        setPredictions(null);
        setTwin(null);
      }
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [h, c] = await Promise.all([api.health(), api.cells()]);
        setHealth(h);
        setCells(c);
        if (h.trained) setMetrics(await api.metrics().catch(() => null));
        if (c.length) setSelected(c[0].cell_id);
      } catch (e) {
        setError(`Backend unreachable: ${e.message}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (selected) loadCell(selected, trained);
  }, [selected, trained, loadCell]);

  const train = async () => {
    setTraining(true);
    setError(null);
    try {
      setMetrics(await api.train(true));
      setHealth(await api.health());
    } catch (e) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  };

  const ingest = async (measurement) => {
    setBusy(true);
    setError(null);
    try {
      setTwin(await api.ingest(selected, measurement));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const resetTwin = async () => {
    setBusy(true);
    try {
      await api.resetTwin(selected);
      setTwin(await api.twin(selected));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const series = predictions
    ? withForecast(mergeSeries(predictions), twin?.trajectory)
    : cycles.map((c) => ({ cycle: c.cycle, measured: c.soh }));

  return (
    <div className="app">
      <CellRail
        cells={cells}
        selected={selected}
        onSelect={setSelected}
        source={health?.data_source}
        trained={trained}
        training={training}
        onTrain={train}
      />
      <main className="main">
        <h2>{selected ? `Cell ${selected}` : "Battery health"}</h2>
        <p className="lede">
          State of health per discharge cycle. Measured capacity is drawn against the trained
          model's prediction and the power-law fade fitted by the twin.
        </p>
        {error && <p className="notice error" role="alert">{error}</p>}
        {!trained && !error && <p className="notice">Models are untrained. Train them to see predictions and twin state.</p>}
        <HealthChart data={series} />
        <MetricsPanel metrics={metrics} />
      </main>
      <TwinPanel twin={twin} trained={trained} busy={busy} onIngest={ingest} onReset={resetTwin} />
    </div>
  );
}
