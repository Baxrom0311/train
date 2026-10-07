import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, RequireAuth, RequirePermission } from './context/AuthContext'
import Navbar from './components/Navbar'
import Backdrop from './components/layout/Backdrop'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import SimulationsPage from './pages/SimulationsPage'
import RunPage from './pages/RunPage'
import RunReportPage from './pages/RunReportPage'
import TalentsPage from './pages/TalentsPage'
import SentOffersPage from './pages/SentOffersPage'
import OffersPage from './pages/OffersPage'
import AdminPage from './pages/AdminPage'
import BillingPage from './pages/BillingPage'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <div className="relative min-h-screen text-foreground">
            <Backdrop />
            <Navbar />
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/simulations" element={<RequireAuth><SimulationsPage /></RequireAuth>} />
              <Route path="/runs/:id" element={<RequireAuth><RunPage /></RequireAuth>} />
              <Route path="/runs/:id/report" element={<RequireAuth><RunReportPage /></RequireAuth>} />
              <Route path="/offers" element={<RequirePermission permission="receive_offers"><OffersPage /></RequirePermission>} />
              <Route path="/talents" element={<RequirePermission permission="view_candidates"><TalentsPage /></RequirePermission>} />
              <Route path="/talents/offers" element={<RequirePermission permission="view_candidates"><SentOffersPage /></RequirePermission>} />
              <Route path="/admin" element={<RequirePermission permission={['approve_companies', 'manage_billing']}><AdminPage /></RequirePermission>} />
              <Route path="/billing" element={<RequirePermission permission="view_org_invoices"><BillingPage /></RequirePermission>} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
