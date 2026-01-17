# LLM Brand Influence Monitor - Frontend

Modern React frontend application for the LLM Brand Influence Monitor platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **React Query** - Server state management
- **Zustand** - Client state management
- **React Router** - Routing
- **Framer Motion** - Animations
- **Recharts** - Data visualization
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `VITE_API_BASE_URL` - Backend API URL (default: `http://localhost:8000`)
- `VITE_APP_NAME` - Application name
- `VITE_ENABLE_DARK_MODE` - Enable dark mode toggle

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Layout/      # Layout components (Sidebar, Header)
│   │   ├── ui/          # Base UI components (Button, Card, etc.)
│   │   └── charts/      # Chart components (Recharts)
│   ├── pages/           # Page components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Websites.tsx
│   │   ├── WebsiteDetail.tsx
│   │   ├── SimulationDetail.tsx
│   │   └── BrandAnalysis.tsx
│   ├── services/        # API clients
│   │   ├── api.ts       # Axios instance
│   │   ├── auth.ts      # Authentication
│   │   ├── websites.ts  # Website management
│   │   ├── icps.ts      # ICP management
│   │   ├── simulations.ts
│   │   └── analytics.ts
│   ├── store/           # Zustand stores
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   ├── types/           # TypeScript definitions
│   │   └── index.ts
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utilities
│   ├── App.tsx          # Root component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── .env.example
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Features

### Authentication
- Login/Register with JWT tokens
- Token refresh
- Protected routes

### Dashboard
- Overview statistics
- Recent activity feed
- Quick actions

### Website Management
- Add/remove websites
- Trigger scraping (incremental/hard)
- View scraped pages
- Manage ICPs and conversations

### Simulations
- Create simulations with multiple LLM providers
- View simulation results
- Analyze LLM responses
- Brand mention tracking

### Brand Analysis
- Brand presence breakdown
- Share of voice charts
- Competitive analysis
- Belief distribution

### UI/UX
- Dark mode support
- Responsive design
- Smooth animations
- Loading states
- Error handling

## API Integration

The frontend communicates with the backend API via Axios. The Vite dev server proxies `/api` requests to `http://localhost:8000`.

### API Services

All API calls are organized in the `src/services/` directory:

- **auth.ts** - Authentication (login, register, logout, refresh)
- **websites.ts** - Website CRUD, scraping
- **icps.ts** - ICP management, conversations, classifications
- **simulations.ts** - Simulation management, responses
- **analytics.ts** - Brand analysis, share of voice

### React Query

Data fetching is handled by React Query with:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

## State Management

### Zustand Stores

- **authStore** - User authentication state, tokens
- **uiStore** - UI state (sidebar, theme, modals, filters)

### React Query

Server state is managed by React Query for:
- Websites
- ICPs
- Simulations
- Analytics

## Styling

### TailwindCSS

Custom design system with:
- Color palette (primary, secondary, accent, neutral)
- Extended spacing scale
- Custom animations
- Dark mode support

### Component Classes

Reusable component classes in `index.css`:
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`, `.btn-ghost`
- `.card`
- `.input`, `.label`
- `.badge`, `.badge-primary`, `.badge-success`, etc.

## Development

### Adding a New Page

1. Create component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/Layout/Sidebar.tsx`

### Adding a New API Service

1. Define types in `src/types/index.ts`
2. Create service in `src/services/`
3. Create React Query hooks in `src/hooks/`

### Customizing Theme

Edit `tailwind.config.js` to customize:
- Colors
- Spacing
- Typography
- Animations

## Deployment

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

The build output will be in the `dist/` directory.

## License

MIT
