import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, RequireAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import SimulationsPage from './pages/SimulationsPage'
import RunPage from './pages/RunPage'
import RunReportPage from './pages/RunReportPage'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-background text-foreground font-sans antialiased">
            <Navbar />
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/simulations" element={<RequireAuth><SimulationsPage /></RequireAuth>} />
              <Route path="/runs/:id" element={<RequireAuth><RunPage /></RequireAuth>} />
              <Route path="/runs/:id/report" element={<RequireAuth><RunReportPage /></RequireAuth>} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
