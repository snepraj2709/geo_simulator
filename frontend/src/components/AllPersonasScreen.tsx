import { Button } from './ui/button';
import { Plus, Calendar, User } from 'lucide-react';

export function AllPersonasScreen() {
  const personas = [
    {
      id: '1',
      name: 'Sarah Chen',
      title: 'VP of Marketing',
      description: 'Senior marketing executive at mid-market B2B SaaS, focused on pipeline generation and brand awareness',
      avatar: 'https://images.unsplash.com/photo-1758518727888-ffa196002e59?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
      lastUpdated: '2 days ago',
      promptCount: 10,
    },
    {
      id: '2',
      name: 'Marcus Rodriguez',
      title: 'SEO Manager',
      description: 'Technical SEO specialist managing enterprise-level organic search strategies and content optimization',
      avatar: 'https://images.unsplash.com/photo-1581065178047-8ee15951ede6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
      lastUpdated: '2 days ago',
      promptCount: 10,
    },
    {
      id: '3',
      name: 'Emily Watson',
      title: 'Content Marketing Director',
      description: 'Leading content strategy for growth-stage startups, balancing thought leadership with demand generation',
      avatar: 'https://images.unsplash.com/photo-1758525589763-b9ad2a75bfe8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
      lastUpdated: '2 days ago',
      promptCount: 10,
    },
    {
      id: '4',
      name: 'David Park',
      title: 'Growth Marketing Lead',
      description: 'Data-driven growth marketer optimizing acquisition channels and conversion funnels in competitive markets',
      avatar: 'https://images.unsplash.com/photo-1752859951149-7d3fc700a7ec?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=200',
      lastUpdated: '2 days ago',
      promptCount: 10,
    },
  ];

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl text-white mb-2">All Personas</h1>
            <p className="text-gray-400">Manage and configure your ideal customer profiles</p>
          </div>
          <Button className="h-11 px-6 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white">
            <Plus className="w-4 h-4 mr-2" />
            Add New Persona
          </Button>
        </div>

        {/* Personas Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {personas.map((persona) => (
            <div
              key={persona.id}
              className="p-6 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all cursor-pointer group"
            >
              {/* Avatar */}
              <div className="flex items-center gap-4 mb-4">
                <img
                  src={persona.avatar}
                  alt={persona.name}
                  className="w-16 h-16 rounded-full object-cover ring-2 ring-violet-500/20 group-hover:ring-violet-500/40 transition-all"
                />
                <div className="flex-1 min-w-0">
                  <h3 className="text-white truncate">{persona.name}</h3>
                  <p className="text-sm text-violet-400 truncate">{persona.title}</p>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-400 leading-relaxed mb-4 line-clamp-3">
                {persona.description}
              </p>

              {/* Meta Info */}
              <div className="flex items-center justify-between pt-4 border-t border-white/10">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <User className="w-3 h-3" />
                  <span>{persona.promptCount} prompts</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Calendar className="w-3 h-3" />
                  <span>{persona.lastUpdated}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
