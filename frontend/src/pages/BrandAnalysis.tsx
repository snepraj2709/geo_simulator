import { useParams } from 'react-router-dom';

export default function BrandAnalysis() {
  const { websiteId } = useParams();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Brand Analysis</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mt-2">
          Website: {websiteId}
        </p>
      </div>

      <div className="card p-6">
        <p className="text-neutral-600 dark:text-neutral-400">
          Brand analysis page with presence breakdown, share of voice charts, and competitive analysis
        </p>
      </div>
    </div>
  );
}
