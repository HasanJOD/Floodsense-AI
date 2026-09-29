export default function MethodologyNote({ data }: { data: { method: string; model_limitations: string } }) {
  return (
    <details className="rounded-lg border border-flood-border bg-flood-panel p-4">
      <summary className="cursor-pointer text-sm font-medium text-flood-text">
        Methodology & Limitations
      </summary>
      <div className="mt-2 space-y-2 text-xs text-flood-muted">
        <p>
          <span className="font-medium text-flood-text">Detection method:</span>{' '}
          {data.method === 'random_forest' ? 'Random Forest (ML)' : 'Heuristic rules'}
        </p>
        <p>
          <span className="font-medium text-flood-text">Risk bands:</span>{' '}
          {['LOW', 'MODERATE', 'HIGH', 'SEVERE'].join(', ')}
        </p>
        <p>{data.model_limitations}</p>
      </div>
    </details>
  );
}
