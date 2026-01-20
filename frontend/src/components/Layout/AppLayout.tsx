import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import type { User } from '../../App';

interface AppLayoutProps {
  user: User;
  onLogout: () => void;
  children: ReactNode;
}

export function AppLayout({ user, onLogout, children }: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header user={user} onLogout={onLogout} />
        
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
