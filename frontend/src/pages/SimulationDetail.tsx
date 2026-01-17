import { useParams } from 'react-router-dom';

export default function SimulationDetail() {
  const { websiteId, simulationId } = useParams();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Simulation Results</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mt-2">
          Website: {websiteId} | Simulation: {simulationId}
        </p>
      </div>

      <div className="card p-6">
        <p className="text-neutral-600 dark:text-neutral-400">
          Simulation detail page with LLM responses, brand mentions, and analysis charts
        </p>
      </div>
    </div>
  );
}
