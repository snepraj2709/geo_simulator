import { motion } from 'framer-motion';
import { Globe, TrendingUp, Users, Zap } from 'lucide-react';

export default function Dashboard() {
  const stats = [
    { name: 'Total Websites', value: '12', icon: Globe, change: '+2 this month' },
    { name: 'Active Simulations', value: '3', icon: Zap, change: 'Running now' },
    { name: 'Brands Tracked', value: '45', icon: TrendingUp, change: '+8 this week' },
    { name: 'ICPs Generated', value: '60', icon: Users, change: '5 per website' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-neutral-600 dark:text-neutral-400 mt-2">
          Monitor your brand presence across LLM responses
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  {stat.name}
                </p>
                <p className="text-3xl font-bold mt-2">{stat.value}</p>
                <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
                  {stat.change}
                </p>
              </div>
              <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900 rounded-lg flex items-center justify-center">
                <stat.icon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-neutral-200 dark:border-neutral-800">
            <div>
              <p className="font-medium">Simulation completed for example.com</p>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                2 hours ago
              </p>
            </div>
            <span className="badge badge-success">Completed</span>
          </div>
          <div className="flex items-center justify-between py-3 border-b border-neutral-200 dark:border-neutral-800">
            <div>
              <p className="font-medium">New website added: acme.com</p>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                5 hours ago
              </p>
            </div>
            <span className="badge badge-primary">New</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-medium">ICPs regenerated for startup.io</p>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                1 day ago
              </p>
            </div>
            <span className="badge badge-secondary">Updated</span>
          </div>
        </div>
      </div>
    </div>
  );
}
