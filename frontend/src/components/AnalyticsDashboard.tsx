import { TrendingUp, Users, Zap, Eye, Sparkles } from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export function AnalyticsDashboard() {
  const trendData = [
    { date: 'Jan 15', score: 65 },
    { date: 'Jan 22', score: 68 },
    { date: 'Jan 29', score: 72 },
    { date: 'Feb 5', score: 71 },
    { date: 'Feb 12', score: 75 },
    { date: 'Feb 19', score: 78 },
  ];

  const visibilityData = [
    { date: 'Jan 15', mentions: 45, recommendations: 12 },
    { date: 'Jan 22', mentions: 52, recommendations: 15 },
    { date: 'Jan 29', mentions: 58, recommendations: 18 },
    { date: 'Feb 5', mentions: 61, recommendations: 20 },
    { date: 'Feb 12', mentions: 67, recommendations: 24 },
    { date: 'Feb 19', mentions: 72, recommendations: 28 },
  ];

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl text-white mb-2">Analytics & Reporting</h1>
          <p className="text-gray-400">Track your GEO performance over time</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">GEO Score</span>
              <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-violet-400" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-3xl text-white tabular-nums">78</div>
              <div className="flex items-center gap-2 text-sm text-green-400">
                <TrendingUp className="w-3 h-3" />
                <span>+6 from last week</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Total Mentions</span>
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Eye className="w-5 h-5 text-blue-400" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-3xl text-white tabular-nums">72</div>
              <div className="flex items-center gap-2 text-sm text-green-400">
                <TrendingUp className="w-3 h-3" />
                <span>+10 from last week</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Recommendations</span>
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-green-400" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-3xl text-white tabular-nums">28</div>
              <div className="flex items-center gap-2 text-sm text-green-400">
                <TrendingUp className="w-3 h-3" />
                <span>+4 from last week</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Active Personas</span>
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-3xl text-white tabular-nums">4</div>
              <div className="text-sm text-gray-500">Across all simulations</div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* GEO Score Trend */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
            <h3 className="text-white mb-6">GEO Score Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="date"
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                  domain={[60, 80]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(10, 10, 15, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={{ fill: '#8b5cf6', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Visibility Metrics */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
            <h3 className="text-white mb-6">Visibility Metrics</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={visibilityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="date"
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(10, 10, 15, 0.95)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="mentions"
                  stackId="1"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.6}
                />
                <Area
                  type="monotone"
                  dataKey="recommendations"
                  stackId="2"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.6}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
          <h3 className="text-white mb-6">Recent Simulations</h3>
          <div className="space-y-4">
            {[
              { date: 'Feb 19, 2026', personas: 4, prompts: 40, score: 78 },
              { date: 'Feb 12, 2026', personas: 4, prompts: 40, score: 75 },
              { date: 'Feb 5, 2026', personas: 3, prompts: 30, score: 71 },
            ].map((sim, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-violet-500/20 flex items-center justify-center">
                    <Sparkles className="w-6 h-6 text-violet-400" />
                  </div>
                  <div>
                    <div className="text-white">Brand Simulation</div>
                    <div className="text-sm text-gray-400">
                      {sim.personas} personas • {sim.prompts} prompts tested
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <div className="text-sm text-gray-400">Score</div>
                    <div className="text-xl text-white tabular-nums">{sim.score}</div>
                  </div>
                  <div className="text-sm text-gray-500">{sim.date}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
