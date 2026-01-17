import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Layout from './components/Layout/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Websites from './pages/Websites';
import WebsiteDetail from './pages/WebsiteDetail';
import SimulationDetail from './pages/SimulationDetail';
import BrandAnalysis from './pages/BrandAnalysis';

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route
        path="/"
        element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="websites" element={<Websites />} />
        <Route path="websites/:websiteId" element={<WebsiteDetail />} />
        <Route path="websites/:websiteId/simulations/:simulationId" element={<SimulationDetail />} />
        <Route path="websites/:websiteId/brands" element={<BrandAnalysis />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
