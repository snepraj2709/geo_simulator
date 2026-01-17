import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  activeFilters: Record<string, any>;
  modals: {
    createWebsite: boolean;
    createSimulation: boolean;
    [key: string]: boolean;
  };
  
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
  setActiveFilters: (filters: Record<string, any>) => void;
  openModal: (modalName: string) => void;
  closeModal: (modalName: string) => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  sidebarOpen: true,
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  activeFilters: {},
  modals: {
    createWebsite: false,
    createSimulation: false,
  },
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    set({ theme });
  },
  
  toggleTheme: () => {
    const newTheme = get().theme === 'light' ? 'dark' : 'light';
    get().setTheme(newTheme);
  },
  
  setActiveFilters: (filters) => set({ activeFilters: filters }),
  
  openModal: (modalName) =>
    set((state) => ({
      modals: { ...state.modals, [modalName]: true },
    })),
  
  closeModal: (modalName) =>
    set((state) => ({
      modals: { ...state.modals, [modalName]: false },
    })),
}));

// Initialize theme on load
if (typeof window !== 'undefined') {
  const theme = localStorage.getItem('theme') as 'light' | 'dark' | null;
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  }
}
