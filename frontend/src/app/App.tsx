import { useState, useEffect, useCallback, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell,
} from "recharts";
import {
  Activity, AlertTriangle, CheckCircle, Clock, Database,
  Server, TrendingUp, Search, RefreshCw, Layers,
  Wifi, BarChart2, ChevronRight,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path: string) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`GET ${path} ${r.status}`);
  return r.json();
}

// ── Primitives ────────────────────────────────────────────────────────

const RISK_COLOR: Record<string, string> = {
  NORMAL: "#16a34a",
  MINOR: "#d97706",
  MODERATE: "#ea580c",
  MAJOR: "#dc2626",
};
const DIST_COLORS = ["#2563eb", "#d97706", "#ea580c", "#dc2626"];

const STATUS_STYLE: Record<string, string> = {
  SUCCESS: "bg-green-50 text-green-700",
  RUNNING: "bg-blue-50 text-blue-700",
  WARNING: "bg-amber-50 text-amber-700",
  FAILED: "bg-red-50 text-red-700",
  HEALTHY: "bg-green-50 text-green-700",
  ACTIVE: "bg-blue-50 text-blue-700",
  ARCHIVED: "bg-gray-100 text-gray-500",
  INFO: "bg-gray-100 text-gray-500",
};

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold" style={{ background: color + "18", color }}>
      {text}
    </span>
  );
}

function StatusTag({ s }: { s: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLE[s] || STATUS_STYLE.INFO}`}>
      {s}
    </span>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded border border-gray-200 p-4 ${className}`}>{children}</div>;
}

function SLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">{children}</p>;
}

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded px-3 py-2 text-xs shadow-sm">
      <p className="text-gray-500 mb-1">{label}</p>
      {payload.map((p: any) => {
        const val = typeof p.value === "number"
          ? (Number.isInteger(p.value) ? p.value : p.value.toFixed(3))
          : p.value;
        return <p key={p.dataKey} style={{ color: p.color }}>{p.name}: {val}</p>;
      })}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────

const NAV = [
  { id: "overview", label: "Overview", icon: Activity, group: "user" },
  { id: "monitoring", label: "Monitoring", icon: Server, group: "system" },
  { id: "model-registry", label: "Model Registry", icon: Layers, group: "system" },
  { id: "pipeline-logs", label: "Pipeline Logs", icon: Database, group: "system" },
] as const;

type PageId = (typeof NAV)[number]["id"];

function NOAALogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="7" fill="#1d4ed8" />
      <path d="M4 20 Q8 16 12 20 Q16 24 20 20 Q24 16 28 20 L28 28 L4 28 Z" fill="white" fillOpacity="0.15" />
      <path d="M4 22 Q8 18 12 22 Q16 26 20 22 Q24 18 28 22 L28 28 L4 28 Z" fill="white" fillOpacity="0.25" />
      <rect x="15" y="7" width="2" height="14" rx="1" fill="white" fillOpacity="0.9" />
      <rect x="17" y="9" width="4" height="1" rx="0.5" fill="white" fillOpacity="0.7" />
      <rect x="17" y="12" width="3" height="1" rx="0.5" fill="white" fillOpacity="0.7" />
      <rect x="17" y="15" width="4" height="1" rx="0.5" fill="white" fillOpacity="0.7" />
      <circle cx="16" cy="19" r="2.5" fill="#60a5fa" stroke="white" strokeWidth="1" />
    </svg>
  );
}

function Sidebar({ active, onNav }: { active: PageId; onNav: (id: PageId) => void }) {
  return (
    <aside className="w-52 flex-shrink-0 flex flex-col border-r border-gray-200 bg-white h-full">
      <div className="px-4 py-4 border-b border-gray-200 flex items-center gap-3">
        <NOAALogo />
        <div>
          <p className="text-sm font-semibold text-gray-900 leading-none">NOAA WLS</p>
          <p className="text-xs text-gray-400 mt-1">Station 8638610</p>
        </div>
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">
        <p className="px-4 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Risk Dashboard</p>
        {NAV.filter(n => n.group === "user").map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => onNav(id)}
            className={`w-full flex items-center gap-2.5 px-4 py-2 text-sm text-left transition-colors ${active === id ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
        <p className="px-4 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mt-4 mb-1">System</p>
        {NAV.filter(n => n.group === "system").map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => onNav(id)}
            className={`w-full flex items-center gap-2.5 px-4 py-2 text-sm text-left transition-colors ${active === id ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-200">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-gray-500">Live · Sewells Point, VA</span>
        </div>
      </div>
    </aside>
  );
}

// ── Header ────────────────────────────────────────────────────────────

function Header({ title, sub, lastUpdated, onRefresh }: { title: string; sub: string; lastUpdated?: string; onRefresh?: () => void }) {
  return (
    <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 flex-shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-gray-900">{title}</h1>
        <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
      </div>
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <span className="flex items-center gap-1"><Clock size={12} /> {lastUpdated || "..."}</span>
        <button onClick={onRefresh} className="flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>
    </div>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────

function usePoll<T>(fetcher: () => Promise<T>, intervalMs = 30000) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async () => {
    try {
      setLoading(false);
      setData(await fetcherRef.current());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => { load(); const id = setInterval(load, intervalMs); return () => clearInterval(id); }, [load, intervalMs]);

  return { data, loading, error, refresh: load };
}

const RANGE_OPTS = [
  { label: "30d", value: 30 },
  { label: "60d", value: 60 },
  { label: "1y", value: 365 },
  { label: "3y", value: 1095 },
  { label: "5y", value: 1825 },
];

function RangeSelect({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-1">
      {RANGE_OPTS.map(o => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={`px-2 py-1 text-xs rounded border transition-colors ${value === o.value ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ── Overview page ─────────────────────────────────────────────────────

function OverviewPage({ lastUpdated, onRefresh }: { lastUpdated?: string; onRefresh?: () => void }) {
  const [range, setRange] = useState(60);
  const [predRange, setPredRange] = useState(30);
  const current = usePoll(() => fetchJson("/api/v1/water-level/current"), 30000);
  const next = usePoll(() => fetchJson("/api/v1/predictions/next"), 30000);
  const hist = usePoll(() => fetchJson(`/api/v1/water-level/historical?days=${range}`), 60000);
  const riskDist = usePoll(() => fetchJson(`/api/v1/risk/distribution?days=${range}`), 60000);
  const vsActual = usePoll(() => fetchJson(`/api/v1/predictions/vs-actual?days=${predRange}`), 60000);
  const recentPred = usePoll(() => fetchJson("/api/v1/predictions/recent?limit=10"), 30000);
  const monthlyAvg = usePoll(() => fetchJson("/api/v1/water-level/monthly-average"), 120000);
  const hourlyAvg = usePoll(() => fetchJson("/api/v1/water-level/hourly-average"), 120000);

  useEffect(() => { hist.refresh(); riskDist.refresh(); }, [range]);
  useEffect(() => { vsActual.refresh(); }, [predRange]);

  const cv = current.data?.value ?? null;
  const nv = next.data?.value ?? null;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
      <Header title="Water Level Prediction & Rob Risk Dashboard" sub="Station 8638610 · Sewells Point, Virginia" lastUpdated={lastUpdated} onRefresh={onRefresh} />

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Current Water Level", value: cv != null ? `${cv.toFixed(3)} m` : "—", sub: current.data?.source === "raw_stream" ? "Live (6-min)" : "Hourly", color: "#1d4ed8" },
          { label: "Predicted Next Hour", value: nv != null ? `${nv.toFixed(3)} m` : "—", sub: next.data?.prediction_time ? `Last predicted: ${new Date(next.data.prediction_time).toLocaleString()}` : "—", color: "#1d4ed8" },
          { label: "Current Risk", value: current.data?.risk_level || "—", sub: "NORMAL < 0.534 m", risk: true, level: current.data?.risk_level || "NORMAL" },
          { label: "Predicted Risk", value: next.data?.risk || "—", sub: "Next hour forecast", risk: true, level: next.data?.risk || "NORMAL" },
        ].map((k, i) => (
          <Card key={i}>
            <p className="text-xs text-gray-500 mb-2">{k.label}</p>
            {k.risk
              ? <p className="text-2xl font-semibold" style={{ color: RISK_COLOR[k.level!] || "#6b7280" }}>{k.value}</p>
              : <p className="text-2xl font-semibold" style={{ color: k.color }}>{k.value}</p>}
            <p className="text-xs text-gray-400 mt-1">{k.sub}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Threshold legend */}
        <Card>
          <SLabel>Flood Thresholds (MHHW)</SLabel>
          <div className="space-y-2">
            {[
              { level: "NORMAL", range: "< 0.534 m" },
              { level: "MINOR", range: "0.534 – 0.825 m" },
              { level: "MODERATE", range: "0.825 – 1.204 m" },
              { level: "MAJOR", range: "≥ 1.204 m" },
            ].map(t => (
              <div key={t.level} className="flex items-center justify-between py-1 border-b border-gray-100 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: RISK_COLOR[t.level] }} />
                  <span className="text-sm font-medium" style={{ color: RISK_COLOR[t.level] }}>{t.level}</span>
                </div>
                <span className="text-xs text-gray-500">{t.range}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 rounded bg-green-50 border border-green-100">
            <p className="text-xs font-medium text-green-700 mb-0.5">Current Status</p>
            <p className="text-xs text-green-600">{cv != null ? `Water level at ${cv.toFixed(3)} m.` : "Waiting for data..."}</p>
          </div>
        </Card>

        {/* Risk distribution */}
        <Card className="col-span-2">
          <div className="flex items-center justify-between mb-3">
            <SLabel>Risk Event Distribution</SLabel>
            <RangeSelect value={range} onChange={v => setRange(v)} />
          </div>
          {riskDist.data?.data ? (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={riskDist.data.data} barSize={36}>
                <CartesianGrid vertical={false} stroke="#f3f4f6" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} tickFormatter={v => Math.round(v).toString()} />
                <Tooltip content={<Tip />} />
                <Bar dataKey="count" name="Events" radius={[3, 3, 0, 0]}>
                  {(riskDist.data.data as any[]).map((_, i) => <Cell key={i} fill={DIST_COLORS[i] || "#2563eb"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-gray-400 py-8 text-center">No data</p>}
        </Card>
      </div>

      {/* Historical + Predicted vs Actual combined chart */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <SLabel>Historical Water Level + Predicted vs Actual</SLabel>
          <RangeSelect value={range} onChange={v => setRange(v)} />
        </div>
        {hist.data?.data ? (
          (() => {
            const histRaw = hist.data.data as any[];
            const predRaw = (vsActual.data?.data || []) as any[];
            const predByTs = new Map<string, number>();
            for (const p of predRaw) { predByTs.set(p.prediction_time, Number(p.predicted)); }
            const merged = histRaw.map((h: any) => {
              const p = predByTs.get(h.date);
              return { time: h.date, actual: Number(h.level), predicted: p ?? null, risk: h.risk };
            });
            const fmtDate = (s: string) => { const d = new Date(s); return d.toLocaleDateString(); };
            return (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={merged} margin={{ right: 80 }}>
                  <CartesianGrid stroke="#f3f4f6" />
                  <XAxis dataKey="time" tickFormatter={fmtDate} tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} interval={Math.max(1, Math.floor(merged.length / 10))} />
                  <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} domain={[0, 1.4]} tickFormatter={v => `${v.toFixed(2)}m`} width={44} />
                  <Tooltip content={({ active, payload, label }: any) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0]?.payload || {};
                    return (
                      <div className="bg-white border border-gray-200 rounded px-3 py-2 text-xs shadow-sm space-y-1">
                        <p className="text-gray-500">{new Date(label).toLocaleString()}</p>
                        {d.actual != null && <p style={{ color: "#2563eb" }}>Actual: {Number(d.actual).toFixed(3)} m</p>}
                        {d.predicted != null && <p style={{ color: "#d97706" }}>Predicted: {Number(d.predicted).toFixed(3)} m</p>}
                        <p style={{ color: "#6b7280" }}>Risk: {d.risk || "—"}</p>
                      </div>
                    );
                  }} />
                  <ReferenceLine y={0.534} stroke={RISK_COLOR.MINOR} strokeDasharray="4 2" strokeWidth={1} label={{ value: "MINOR", position: "right", fontSize: 10, fill: RISK_COLOR.MINOR }} />
                  <ReferenceLine y={0.825} stroke={RISK_COLOR.MODERATE} strokeDasharray="4 2" strokeWidth={1} label={{ value: "MODERATE", position: "right", fontSize: 10, fill: RISK_COLOR.MODERATE }} />
                  <ReferenceLine y={1.204} stroke={RISK_COLOR.MAJOR} strokeDasharray="4 2" strokeWidth={1} label={{ value: "MAJOR", position: "right", fontSize: 10, fill: RISK_COLOR.MAJOR }} />
                  <Line type="monotone" dataKey="actual" stroke="#2563eb" strokeWidth={1.5} dot={false} name="Actual" isAnimationActive={false} />
                  <Line type="monotone" dataKey="predicted" stroke="#d97706" strokeWidth={1.5} dot={true} name="Predicted" connectNulls={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            );
          })()
        ) : <p className="text-xs text-gray-400 py-8 text-center">No historical data. Run batch extraction first.</p>}
      </Card>

      {/* Monthly & Hourly averages */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SLabel>Average Water Level by Month</SLabel>
          {monthlyAvg.data?.data ? (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={monthlyAvg.data.data} margin={{ right: 20 }}>
                <CartesianGrid stroke="#f3f4f6" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} tickFormatter={v => `${v.toFixed(2)}m`} width={44} />
                <Tooltip content={<Tip />} />
                <Line type="monotone" dataKey="avg" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} name="Avg WL" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-gray-400 py-8 text-center">Loading...</p>}
        </Card>
        <Card>
          <SLabel>Average Water Level by Hour of Day</SLabel>
          {hourlyAvg.data?.data ? (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={hourlyAvg.data.data} margin={{ right: 20 }}>
                <CartesianGrid stroke="#f3f4f6" />
                <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "#9ca3af" }} axisLine={false} tickLine={false} interval={2} />
                <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} tickFormatter={v => `${v.toFixed(2)}m`} width={44} />
                <Tooltip content={<Tip />} />
                <Line type="monotone" dataKey="avg" stroke="#d97706" strokeWidth={2} dot={{ r: 3 }} name="Avg WL" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="text-xs text-gray-400 py-8 text-center">Loading...</p>}
        </Card>
      </div>

      {/* Recent predictions */}
      <Card>
        <SLabel>Recent Predictions</SLabel>
        {recentPred.data?.data?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                {["Prediction Time", "Target Time", "Current (m)", "Predicted (m)", "Risk", "Alert"].map(h => (
                  <th key={h} className="text-left pb-2 pr-4 text-xs font-medium text-gray-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(recentPred.data.data as any[]).slice(0, 10).map((r: any, i: number) => (
                <tr key={i} className="border-b border-gray-100">
                  <td className="py-2 pr-4 text-xs text-gray-500">{new Date(r.prediction_time).toLocaleString()}</td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{new Date(r.target_time).toLocaleString()}</td>
                  <td className="py-2 pr-4 text-gray-700">{Number(r.current_water_level_m).toFixed(3)}</td>
                  <td className="py-2 pr-4 text-blue-700 font-medium">{Number(r.predicted_water_level_next_1h_m).toFixed(3)}</td>
                  <td className="py-2"><Badge text={r.predicted_risk_level} color={RISK_COLOR[r.predicted_risk_level] || "#6b7280"} /></td>
                  <td className="py-2 text-xs text-gray-500">{r.alert_policy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="text-xs text-gray-400 py-4">No predictions yet. Run seed_prediction_from_notebook.py or trigger pipeline.</p>}
      </Card>
    </div>
  );
}

// ── Monitoring page ───────────────────────────────────────────────────

function MonitoringPage() {
  const services = usePoll(() => fetchJson("/api/v1/monitoring/services"), 60000);
  const dags = usePoll(() => fetchJson("/api/v1/monitoring/dags"), 60000);
  const kafka = usePoll(() => fetchJson("/api/v1/monitoring/kafka"), 30000);
  const spark = usePoll(() => fetchJson("/api/v1/monitoring/spark"), 30000);
  const quality = usePoll(() => fetchJson("/api/v1/monitoring/data-quality"), 60000);

  const svcData = (services.data?.data || []) as any[];
  const dagData = (dags.data?.data || []) as any[];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
      <Header title="Pipeline Monitoring & System Operations" sub="Kafka · PySpark · Airflow · PostgreSQL · ML Service" />

      {/* Services */}
      <div className="grid grid-cols-3 gap-3">
        {svcData.length ? svcData.map((s: any, i: number) => (
          <Card key={i} className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">{s.name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.detail}</p>
            </div>
            <StatusTag s={s.status === "healthy" ? "HEALTHY" : "WARNING"} />
          </Card>
        )) : <p className="col-span-3 text-xs text-gray-400 py-4 text-center">Loading services...</p>}
      </div>

      {/* Pipeline flow */}
      <Card>
        <SLabel>Pipeline Flow</SLabel>
        <div className="flex items-center gap-1 overflow-x-auto py-1">
          {["NOAA API", "Kafka Producer", "Kafka Topic", "PySpark", "PostgreSQL", "ML Service", "Dashboard"].map((node, i) => (
            <div key={i} className="flex items-center gap-1 flex-shrink-0">
              <div className="px-3 py-2 rounded border border-gray-200 bg-gray-50 text-xs font-medium text-gray-700">{node}</div>
              {i < 6 && <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />}
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        {/* Airflow DAGs */}
        <Card>
          <SLabel>Pipeline Tasks (Last Run)</SLabel>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                {["Task", "Status", "Records", "Last Run"].map(h => (
                  <th key={h} className="text-left pb-2 pr-3 text-xs font-medium text-gray-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dagData.length ? dagData.map((d: any, i: number) => (
                <tr key={i} className="border-b border-gray-100">
                  <td className="py-2 pr-3 text-xs text-blue-700 font-medium">{d.name}</td>
                  <td className="py-2 pr-3"><StatusTag s={d.status} /></td>
                  <td className="py-2 pr-3 text-xs text-gray-700">{d.records ?? "—"}</td>
                  <td className="py-2 text-xs text-gray-500">{d.last_run ? new Date(d.last_run).toLocaleString() : "—"}</td>
                </tr>
              )) : <tr><td colSpan={4} className="py-4 text-center text-xs text-gray-400">No pipeline runs yet</td></tr>}
            </tbody>
          </table>
        </Card>

        {/* Kafka + Spark */}
        <Card>
          <SLabel>Kafka & Spark Metrics</SLabel>
          <div className="space-y-3">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Kafka · noaa_water_level_raw</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["Messages Produced", String(kafka.data?.messages_produced ?? "—")],
                  ["Consumer Lag", String(kafka.data?.consumer_lag ?? "—")],
                  ["Topic", kafka.data?.topic || "—"],
                ].map(([k, v], i) => (
                  <div key={i} className="p-2 rounded bg-gray-50 border border-gray-100">
                    <p className="text-[10px] text-gray-400">{k}</p>
                    <p className="text-xs font-semibold text-gray-800 mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">PySpark Structured Streaming</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["Raw Rows Written", String(spark.data?.raw_rows ?? "—")],
                  ["Hourly Agg Rows", String(spark.data?.hourly_rows ?? "—")],
                  ["Anomalies", String(spark.data?.anomalies ?? "—")],
                ].map(([k, v], i) => (
                  <div key={i} className="p-2 rounded bg-gray-50 border border-gray-100">
                    <p className="text-[10px] text-gray-400">{k}</p>
                    <p className="text-xs font-semibold text-gray-800 mt-0.5">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Data quality */}
      <Card>
        <SLabel>Data Quality</SLabel>
        {quality.data?.data?.length ? (
          <div className="grid grid-cols-4 gap-3">
            {(quality.data.data as any[]).map((q: any, i: number) => (
              <div key={i} className={`p-3 rounded border ${q.ok ? "border-green-100 bg-green-50" : "border-amber-100 bg-amber-50"}`}>
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs text-gray-500">{q.label}</p>
                  {q.ok ? <CheckCircle size={12} className="text-green-600" /> : <AlertTriangle size={12} className="text-amber-500" />}
                </div>
                <p className={`text-xl font-semibold ${q.ok ? "text-green-700" : "text-amber-700"}`}>{q.value}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">{q.detail || ""}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-xs text-gray-400 py-4">No quality checks yet</p>}
      </Card>
    </div>
  );
}

// ── Model Registry page ───────────────────────────────────────────────

function ModelRegistryPage() {
  const active = usePoll(() => fetchJson("/api/v1/models/active"), 60000);
  const allModels = usePoll(() => fetchJson("/api/v1/models"), 60000);

  const a = active.data;
  const models = (allModels.data?.data || []) as any[];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
      <Header title="Model Registry" sub="Trained model versions, metrics, and deployment status" />
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Active Model", value: a?.version || "—" },
          { label: "MAE", value: a?.mae != null ? `${a.mae} m` : "—" },
          { label: "R²", value: a?.r2 != null ? String(a.r2) : "—" },
          { label: "vs Persistence", value: a?.improvement != null ? `${a.improvement.toFixed(1)}%` : "—" },
        ].map((k, i) => (
          <Card key={i}>
            <p className="text-xs text-gray-400 mb-1">{k.label}</p>
            <p className="text-xl font-semibold text-gray-900">{k.value}</p>
          </Card>
        ))}
      </div>

      <Card>
        <SLabel>All Models</SLabel>
        {models.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  {["Version", "Name", "MAE (m)", "RMSE (m)", "R²", "Persistence MAE", "Improvement", "Status", "Created"].map(h => (
                    <th key={h} className="text-left pb-2 pr-5 text-xs font-medium text-gray-400 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.map((m: any, i: number) => (
                  <tr key={i} className={`border-b border-gray-100 ${m.is_active ? "bg-blue-50/50" : ""}`}>
                    <td className="py-2.5 pr-5 font-semibold text-blue-700">{m.model_version}</td>
                    <td className="py-2.5 pr-5 text-xs text-gray-500">{m.model_name}</td>
                    <td className="py-2.5 pr-5 text-gray-800">{Number(m.mae).toFixed(5)}</td>
                    <td className="py-2.5 pr-5 text-gray-800">{Number(m.rmse).toFixed(5)}</td>
                    <td className="py-2.5 pr-5 font-semibold text-green-700">{Number(m.r2).toFixed(5)}</td>
                    <td className="py-2.5 pr-5 text-gray-500">{Number(m.persistence_mae).toFixed(5)}</td>
                    <td className="py-2.5 pr-5 font-semibold text-blue-600">{Number(m.improvement_vs_persistence).toFixed(1)}%</td>
                    <td className="py-2.5 pr-5"><StatusTag s={m.is_active ? "ACTIVE" : m.status} /></td>
                    <td className="py-2.5 text-xs text-gray-400">{new Date(m.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p className="text-xs text-gray-400 py-4">No models registered. Run register_notebook_model.py or trigger training DAG.</p>}
      </Card>
    </div>
  );
}

// ── Pipeline Logs page ────────────────────────────────────────────────

function PipelineLogsPage() {
  const [component, setComponent] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (component) params.set("component", component);
      if (severity) params.set("severity", severity);
      if (status) params.set("status", status);
      if (query) params.set("q", query);
      params.set("limit", "200");
      const d = await fetchJson(`/api/v1/pipeline/logs?${params}`);
      setLogs(d.data || []);
    } catch { } finally { setLoading(false); }
  }, [component, severity, status, query]);

  useEffect(() => { loadLogs(); const id = setInterval(loadLogs, 30000); return () => clearInterval(id); }, [loadLogs]);

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
      <Header title="Pipeline Logs" sub="Operational event log across all pipeline components" />

      <Card className="mt-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {[
            { label: "Component", val: component, set: setComponent, opts: ["", "airflow", "kafka_producer", "spark_structured_streaming", "model_training", "python_prediction"] },
            { label: "Severity", val: severity, set: setSeverity, opts: ["", "INFO", "WARNING", "ERROR", "FATAL"] },
            { label: "Status", val: status, set: setStatus, opts: ["", "SUCCESS", "RUNNING", "WARNING", "FAILED"] },
          ].map(({ label, val, set, opts }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className="text-xs text-gray-400">{label}</span>
              <select value={val} onChange={e => set(e.target.value)} className="text-xs px-2 py-1.5 rounded border border-gray-200 bg-white text-gray-700 outline-none">
                {opts.map(o => <option key={o} value={o}>{o || "All"}</option>)}
              </select>
            </div>
          ))}
          <div className="flex items-center gap-1.5 border border-gray-200 rounded px-2 py-1.5 bg-white flex-1 min-w-[200px]">
            <Search size={12} className="text-gray-400" />
            <input type="text" placeholder="Search messages..." value={query} onChange={e => setQuery(e.target.value)} className="flex-1 text-xs text-gray-700 outline-none bg-transparent" />
          </div>
          <span className="text-xs text-gray-400">{logs.length} entries</span>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              {["Time", "Pipeline", "Component", "Task", "Severity", "Status", "Message", "Records"].map(h => (
                <th key={h} className="text-left pb-2 pr-4 text-xs font-medium text-gray-400 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.map((l: any, i: number) => (
              <tr key={i} className="border-b border-gray-100">
                <td className="py-2 pr-4 text-xs text-gray-400 whitespace-nowrap">{l.time ? (() => { const d = new Date(l.time + "Z"); const utc = d.toLocaleString("en-US", { timeZone: "UTC", hour12: false, month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); const wib = d.toLocaleString("id-ID", { timeZone: "Asia/Jakarta", hour: "2-digit", minute: "2-digit" }); return utc + " UTC / " + wib + " WIB"; })() : "—"}</td>
                <td className="py-2 pr-4 text-xs text-gray-600">{l.pipeline}</td>
                <td className="py-2 pr-4 text-xs text-blue-700 font-medium">{l.component}</td>
                <td className="py-2 pr-4 text-xs text-gray-600 whitespace-nowrap">{l.task}</td>
                <td className="py-2 pr-4"><StatusTag s={l.severity} /></td>
                <td className="py-2 pr-4"><StatusTag s={l.status} /></td>
                <td className="py-2 pr-4 text-xs text-gray-500 max-w-xs">{l.message}</td>
                <td className="py-2 text-xs text-gray-600">{l.records ?? "—"}</td>
              </tr>
            ))}
            {logs.length === 0 && !loading && (
              <tr><td colSpan={8} className="py-10 text-center text-xs text-gray-400">No log entries found.</td></tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────

const PAGES: Record<PageId, { title: string; sub: string }> = {
  overview: { title: "Overview", sub: "Station 8638610 · Sewells Point, Virginia" },
  monitoring: { title: "Monitoring", sub: "Kafka · PySpark · Airflow · PostgreSQL · ML Service" },
  "model-registry": { title: "Model Registry", sub: "Trained model versions, metrics, and deployment status" },
  "pipeline-logs": { title: "Pipeline Logs", sub: "Operational event log across all pipeline components" },
};

export default function App() {
  const [active, setActive] = useState<PageId>("overview");
  const [lastUpdated, setLastUpdated] = useState("");

  const handleRefresh = useCallback(() => {
    setLastUpdated(new Date().toLocaleTimeString());
    window.location.reload();
  }, []);

  useEffect(() => {
    setLastUpdated(new Date().toLocaleTimeString());
    const id = setInterval(() => setLastUpdated(new Date().toLocaleTimeString()), 10000);
    return () => clearInterval(id);
  }, []);

  const cur = PAGES[active];

  return (
    <div className="flex h-screen w-full overflow-hidden" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      <Sidebar active={active} onNav={setActive} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {active === "overview" && <OverviewPage lastUpdated={lastUpdated} onRefresh={handleRefresh} />}
        {active === "monitoring" && <MonitoringPage />}
        {active === "model-registry" && <ModelRegistryPage />}
        {active === "pipeline-logs" && <PipelineLogsPage />}
      </div>
    </div>
  );
}
