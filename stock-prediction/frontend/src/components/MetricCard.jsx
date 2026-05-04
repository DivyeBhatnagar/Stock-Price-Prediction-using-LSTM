export default function MetricCard({ label, value, trend }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-muted">{label}</p>
      <div className="mt-2 flex items-center justify-between">
        <p className="text-lg font-semibold text-ink">{value}</p>
        {trend && (
          <span className="rounded-full bg-accent/10 px-2 py-1 text-xs text-accent">
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
