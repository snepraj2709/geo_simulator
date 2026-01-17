import { useParams } from 'react-router-dom';

export default function WebsiteDetail() {
  const { websiteId } = useParams();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Website Details</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mt-2">
          ID: {websiteId}
        </p>
      </div>

      <div className="card p-6">
        <p className="text-neutral-600 dark:text-neutral-400">
          Website detail page with tabs for Overview, ICPs, Conversations, and Simulations
        </p>
      </div>
    </div>
  );
}
