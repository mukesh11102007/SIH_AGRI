import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import LiveMonitor from './pages/LiveMonitor';
import Irrigation from './pages/Irrigation';
import CropHealth from './pages/CropHealth';
import EnvironmentalRisk from './pages/EnvironmentalRisk';
import History from './pages/History';
import Alerts from './pages/Alerts';
import Devices from './pages/Devices';
import FarmSetup from './pages/FarmSetup';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 10000,
      refetchOnWindowFocus: true,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout farmName="Demo Farm" dataSource="simulator" />}>
            <Route index element={<Dashboard />} />
            <Route path="monitor" element={<LiveMonitor />} />
            <Route path="irrigation" element={<Irrigation />} />
            <Route path="health" element={<CropHealth />} />
            <Route path="risk" element={<EnvironmentalRisk />} />
            <Route path="history" element={<History />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="devices" element={<Devices />} />
            <Route path="setup" element={<FarmSetup />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
