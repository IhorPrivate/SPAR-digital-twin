import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { pct } from "../format";

const EOL = 0.7;

export default function HealthChart({ data }) {
  if (!data?.length) return <p className="empty">No cycles to show.</p>;
  return (
    <div className="chart-wrap">
      <div className="legend">
        <span className="measured">Measured SOH</span>
        <span className="predicted">Predicted SOH</span>
        <span className="band">10–90 % band</span>
        <span className="forecast">Physics forecast</span>
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <XAxis dataKey="cycle" type="number" domain={["dataMin", "dataMax"]} tick={{ fontSize: 12 }} />
          <YAxis domain={[0.6, 1.05]} tickFormatter={(v) => pct(v, 0)} tick={{ fontSize: 12 }} width={56} />
          <Tooltip
            formatter={(v, name) => (Array.isArray(v) ? [`${pct(v[0])} – ${pct(v[1])}`, name] : [pct(v), name])}
            labelFormatter={(l) => `Cycle ${l}`}
          />
          <ReferenceLine y={EOL} stroke="#9a3b2a" strokeDasharray="4 4" label={{ value: "End of life", fontSize: 11, position: "insideBottomLeft" }} />
          <Area dataKey="band" stroke="none" fill="#cfe3e0" fillOpacity={0.9} isAnimationActive={false} name="Band" />
          <Line dataKey="measured" stroke="#1e2a30" dot={false} strokeWidth={1.6} isAnimationActive={false} name="Measured" />
          <Line dataKey="predicted" stroke="#2b7f78" dot={false} strokeWidth={1.4} isAnimationActive={false} name="Predicted" />
          <Line dataKey="forecast" stroke="#b0622a" dot={false} strokeDasharray="5 3" strokeWidth={1.4} isAnimationActive={false} name="Forecast" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
