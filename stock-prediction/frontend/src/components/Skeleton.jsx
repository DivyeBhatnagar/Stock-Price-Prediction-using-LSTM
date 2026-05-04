export function SkeletonCard() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-3 w-24 rounded bg-gray-200" />
      <div className="mt-3 h-5 w-32 rounded bg-gray-200" />
      <div className="mt-6 flex justify-between">
        <div className="h-8 w-24 rounded bg-gray-200" />
        <div className="h-6 w-16 rounded bg-gray-200" />
      </div>
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-4 w-40 rounded bg-gray-200" />
      <div className="mt-3 h-64 rounded-xl bg-gray-200" />
    </div>
  );
}
