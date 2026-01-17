import { Outlet } from 'react-router-dom';

export default function Layout() {

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-950">
      <div className={`flex-1 flex flex-col transition-all duration-300`}>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
