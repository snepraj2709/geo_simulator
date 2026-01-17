import {
  Globe,
  Users,
  MessageCircle,
  Tag,
  Cpu,
  Search,
  Network,
  BarChart,
  LucideIcon,
} from 'lucide-react';

// Map icon identifiers to Lucide icons
const iconMap: Record<string, LucideIcon> = {
  globe: Globe,
  users: Users,
  'message-circle': MessageCircle,
  tag: Tag,
  cpu: Cpu,
  search: Search,
  network: Network,
  'bar-chart': BarChart,
};

export function getStageIcon(iconName: string): LucideIcon {
  return iconMap[iconName] || Globe;
}
