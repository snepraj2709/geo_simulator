import { TrendingUp, TrendingDown, Award, AlertTriangle, Target, Download, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Cell,
} from 'recharts';
import { brandStates, competitorData, geoScore, modelPerformance, radarData } from '@/data/constants';

interface ReportDashboardProps {
  brandUrl: string;
}

export function ReportDashboard({ brandUrl }: ReportDashboardProps) {

  return (
    <div className="min-h-screen px-4 py-8 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/5 rounded-full blur-[100px]"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/5 rounded-full blur-[100px]"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 mb-3">
              <Award className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-300">Analysis Complete</span>
            </div>
            <h1 className="text-4xl text-white mb-2">GEO Performance Report</h1>
            <p className="text-gray-400">{brandUrl}</p>
          </div>

          <div className="flex gap-3">
            <Button variant="outline" className="border-white/10 hover:bg-white/5">
              <RefreshCw className="w-4 h-4 mr-2" />
              Re-run
            </Button>
            <Button className="bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700">
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>

        {/* GEO Score Hero */}
        <div className="p-8 rounded-2xl bg-gradient-to-br from-violet-500/20 via-blue-500/20 to-cyan-500/20 border border-violet-500/30 backdrop-blur-sm">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="flex-1 text-center md:text-left">
              <h2 className="text-gray-300 mb-2">Your GEO Score</h2>
              <div className="flex items-baseline gap-3 justify-center md:justify-start">
                <span className="text-6xl text-white tabular-nums">{geoScore}</span>
                <span className="text-2xl text-gray-400">/ 100</span>
              </div>
              <p className="text-sm text-gray-400 mt-3 max-w-md">
                Your brand has strong AI visibility with room for optimization in trust signals and competitive positioning
              </p>
            </div>

            <div className="flex gap-6">
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-green-500/20 flex items-center justify-center mb-2">
                  <TrendingUp className="w-8 h-8 text-green-400" />
                </div>
                <div className="text-sm text-gray-400">Strong</div>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 rounded-xl bg-blue-500/20 flex items-center justify-center mb-2">
                  <Target className="w-8 h-8 text-blue-400" />
                </div>
                <div className="text-sm text-gray-400">Visible</div>
              </div>
            </div>
          </div>
        </div>

        {/* Brand Presence States */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {brandStates.map((state) => (
            <div
              key={state.state}
              className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">{state.state}</span>
                {state.trend === 'up' && <TrendingUp className="w-4 h-4 text-green-400" />}
                {state.trend === 'down' && <TrendingDown className="w-4 h-4 text-red-400" />}
              </div>
              
              <div className="space-y-1">
                <div className="text-3xl text-white tabular-nums">{state.count}</div>
                <div className="text-sm text-gray-500">{state.percentage}% of responses</div>
              </div>

              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full transition-all duration-1000"
                  style={{
                    width: `${state.percentage * 2}%`,
                    backgroundColor: state.color,
                  }}
                ></div>
              </div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Competitive Comparison */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
            <h3 className="text-white mb-6">Competitive GEO Benchmark</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={competitorData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis 
                  dataKey="name" 
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
                <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                  {competitorData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Radar Chart */}
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
            <h3 className="text-white mb-6">Brand Attributes Analysis</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.1)" />
                <PolarAngleAxis 
                  dataKey="attribute" 
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                />
                <PolarRadiusAxis 
                  angle={90} 
                  domain={[0, 100]}
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
                />
                <Radar
                  name="Your Brand"
                  dataKey="yourBrand"
                  stroke="#8b5cf6"
                  fill="#8b5cf6"
                  fillOpacity={0.3}
                />
                <Radar
                  name="Industry Avg"
                  dataKey="industry"
                  stroke="#64748b"
                  fill="#64748b"
                  fillOpacity={0.2}
                />
                <Legend 
                  wrapperStyle={{ color: '#fff' }}
                  iconType="circle"
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Performance Table */}
        <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
          <h3 className="text-white mb-6">Performance by AI Model</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 text-sm text-gray-400">Model</th>
                  <th className="text-right py-3 px-4 text-sm text-gray-400">Mentions</th>
                  <th className="text-right py-3 px-4 text-sm text-gray-400">Recommendations</th>
                  <th className="text-right py-3 px-4 text-sm text-gray-400">Ignored</th>
                  <th className="text-right py-3 px-4 text-sm text-gray-400">Success Rate</th>
                </tr>
              </thead>
              <tbody>
                {modelPerformance.map((model) => {
                  const total = model.mentions + model.recommendations + model.ignored;
                  const successRate = Math.round(((model.mentions + model.recommendations) / total) * 100);
                  
                  return (
                    <tr key={model.model} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-4 px-4 text-white">{model.model}</td>
                      <td className="py-4 px-4 text-right text-gray-300 tabular-nums">{model.mentions}</td>
                      <td className="py-4 px-4 text-right text-green-400 tabular-nums">{model.recommendations}</td>
                      <td className="py-4 px-4 text-right text-red-400 tabular-nums">{model.ignored}</td>
                      <td className="py-4 px-4 text-right">
                        <span className={`inline-flex items-center gap-1 tabular-nums ${
                          successRate >= 90 ? 'text-green-400' :
                          successRate >= 70 ? 'text-blue-400' :
                          'text-yellow-400'
                        }`}>
                          {successRate}%
                          {successRate >= 90 ? <TrendingUp className="w-3 h-3" /> : null}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Key Recommendations */}
        <div className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm">
          <h3 className="text-white mb-6">Key Recommendations</h3>
          
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <div className="flex-1">
                <h4 className="text-white mb-1">Strong Foundation</h4>
                <p className="text-sm text-gray-400">
                  Your brand is mentioned in 78% of relevant queries. Continue building content authority in your category.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Target className="w-5 h-5 text-blue-400" />
              </div>
              <div className="flex-1">
                <h4 className="text-white mb-1">Optimize for Direct Recommendations</h4>
                <p className="text-sm text-gray-400">
                  Only 30% of mentions are direct recommendations. Focus on trust signals, case studies, and comparison content.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
              <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-yellow-400" />
              </div>
              <div className="flex-1">
                <h4 className="text-white mb-1">Address Competitor Gap</h4>
                <p className="text-sm text-gray-400">
                  Competitor D scores 3 points higher. Analyze their content strategy and identify differentiation opportunities.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
