import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HostPage from './pages/HostPage';
import GuestPage from './pages/GuestPage';
import NotFoundPage from './pages/NotFoundPage';
import GestureOnboarding from './components/GestureOnboarding';

function OnboardingPreview() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-8 gap-8">
      <div className="flex flex-col items-center gap-2">
        <span className="text-[11px] font-semibold tracking-[0.3em] uppercase text-white/20">DualSign</span>
        <h1 className="text-2xl font-bold text-white/80 tracking-tight">Component Preview</h1>
      </div>
      <GestureOnboarding />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<OnboardingPreview />} />
        <Route path="/host" element={<HostPage />} />
        <Route path="/guest" element={<GuestPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
