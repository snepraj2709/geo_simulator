import { useState } from 'react';
import { ChevronLeft, ChevronRight, Sparkles, Users, Zap, CheckCircle, Lightbulb, FileText, LayoutDashboard } from 'lucide-react';
import { Button } from '../ui/button';
import { useNavigate, useLocation } from 'react-router-dom';

const menuItems = [
  {
    path: '/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
  },
  {
    path: '/run-simulator',
    label: 'Run Brand Simulator',
    icon: Sparkles,
  },
  {
    path: '/all-personas',
    label: 'All Personas',
    icon: Users,
  },
  {
    path: '/persona-simulation',
    label: 'Persona Simulation',
    icon: Zap,
  },
  {
    path: '/preflight-checker',
    label: 'Pre-Flight GEO Checker',
    icon: CheckCircle,
  },
  {
    path: '/reports',
    label: 'Analytics & Reports',
    icon: FileText,
  },
  {
    path: '/insights',
    label: 'Insights & Recommendations',
    icon: Lightbulb,
  },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div
      className={`${
        isCollapsed ? 'w-20' : 'w-64'
      } bg-white/5 border-r border-white/10 flex flex-col transition-all duration-300 ease-in-out`}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-white/10">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-white">GEO Simulator</span>
          </div>
        )}
        {isCollapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center mx-auto">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        )}
      </div>

      {/* Menu Items */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                  : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && (
                <span className="text-sm truncate">{item.label}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-3 border-t border-white/10">
        <Button
          variant="outline"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className={`${
            isCollapsed ? 'w-full px-0 justify-center' : 'w-full'
          } h-10 bg-white/5 border-white/10 hover:bg-white/10 text-gray-400`}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Collapse
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
