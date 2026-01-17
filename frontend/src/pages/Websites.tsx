import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, Globe, Clock } from 'lucide-react';

export default function Websites() {
  // This would be fetched from the API using React Query
  const websites = [
    {
      id: '1',
      name: 'Example Company',
      domain: 'example.com',
      status: 'completed',
      last_scraped_at: '2024-01-15T10:30:00Z',
      stats: {
        pages_scraped: 150,
        icps_generated: 5,
        simulations_run: 3,
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Websites</h1>
          <p className="text-neutral-600 dark:text-neutral-400 mt-2">
            Manage your tracked websites
          </p>
        </div>
        <button className="btn btn-primary h-10 px-4">
          <Plus className="w-4 h-4 mr-2" />
          Add Website
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {websites.map((website, index) => (
          <motion.div
            key={website.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Link to={`/websites/${website.id}`} className="block">
              <div className="card p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900 rounded-lg flex items-center justify-center">
                    <Globe className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <span className="badge badge-success">
                    {website.status}
                  </span>
                </div>

                <h3 className="text-lg font-semibold mb-1">{website.name}</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                  {website.domain}
                </p>

                <div className="flex items-center text-xs text-neutral-500 dark:text-neutral-500 mb-4">
                  <Clock className="w-3 h-3 mr-1" />
                  Last scraped 2 hours ago
                </div>

                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-800">
                  <div>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      Pages
                    </p>
                    <p className="text-lg font-semibold">
                      {website.stats.pages_scraped}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      ICPs
                    </p>
                    <p className="text-lg font-semibold">
                      {website.stats.icps_generated}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      Sims
                    </p>
                    <p className="text-lg font-semibold">
                      {website.stats.simulations_run}
                    </p>
                  </div>
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
