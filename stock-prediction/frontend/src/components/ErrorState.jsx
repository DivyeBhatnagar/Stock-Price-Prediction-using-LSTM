export default function ErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div className="card p-6 text-center">
      <p className="text-sm font-semibold text-ink">{title}</p>
      {message && <p className="mt-2 text-sm text-muted">{message}</p>}
      {onRetry && (
        <button
          className="mt-4 rounded-full border border-border px-4 py-2 text-sm text-ink transition hover:opacity-70"
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  );
}
