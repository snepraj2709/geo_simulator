import { useState, useRef, useEffect } from 'react';
import { User as UserIcon, Settings, LogOut } from 'lucide-react';
import type { User } from '../../App';

interface HeaderProps {
  user: User;
  onLogout: () => void;
}

export function Header({ user, onLogout }: HeaderProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const initials = user.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="h-16 bg-white/5 border-b border-white/10 flex items-center justify-end px-6">
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsDropdownOpen(!isDropdownOpen)}
          className="flex items-center gap-3 hover:bg-white/5 px-3 py-2 rounded-lg transition-colors"
        >
          <div className="text-right">
            <div className="text-sm text-white">{user.name}</div>
            <div className="text-xs text-gray-400">{user.email}</div>
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-white">
            {initials}
          </div>
        </button>

        {isDropdownOpen && (
          <div className="absolute right-0 mt-2 w-56 rounded-xl bg-[#0a0a0f] border border-white/10 shadow-xl overflow-hidden z-50">
            <div className="p-3 border-b border-white/10">
              <div className="text-sm text-white">{user.name}</div>
              <div className="text-xs text-gray-400">{user.email}</div>
            </div>

            <div className="py-2">
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                <UserIcon className="w-4 h-4" />
                Profile
              </button>
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors">
                <Settings className="w-4 h-4" />
                Settings
              </button>
            </div>

            <div className="border-t border-white/10 py-2">
              <button
                onClick={onLogout}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-400 hover:bg-white/5 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
