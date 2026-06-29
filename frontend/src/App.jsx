import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import VoiceLive from './pages/VoiceLive'

function DashboardPage() {
  return (
    <>
      <header className="dashboard-header" style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem 2rem 0' }}>
        <div />
        <nav className="top-nav">
          <Link to="/" className="active">Analytics</Link>
          <Link to="/voice-live">Live Voice</Link>
        </nav>
      </header>
      <Dashboard />
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/voice-live" element={<VoiceLive />} />
      </Routes>
    </BrowserRouter>
  )
}
