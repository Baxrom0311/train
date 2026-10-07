import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, RequireAuth, RequirePermission, homeFor, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import Backdrop from './components/layout/Backdrop'
import OfflineBanner from './components/layout/OfflineBanner'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import LandingPage from './pages/LandingPage'
import SimulationsPage from './pages/SimulationsPage'
import RunPage from './pages/RunPage'
import RunReportPage from './pages/RunReportPage'
import TalentsPage from './pages/TalentsPage'
import SentOffersPage from './pages/SentOffersPage'
import CompanyReportPage from './pages/CompanyReportPage'
import OffersPage from './pages/OffersPage'
import AdminPage from './pages/AdminPage'
import BillingPage from './pages/BillingPage'
import UniversityPage from './pages/UniversityPage'
import CertificatePage from './pages/CertificatePage'
import PortfolioPublicPage from './pages/PortfolioPublicPage'
import PortfolioPage from './pages/PortfolioPage'
import ScenarioListPage from './pages/ScenarioListPage'
import NotificationsPage from './pages/NotificationsPage'
import ScenarioEditorPage from './pages/ScenarioEditorPage'
import CompanyVacanciesPage from './pages/CompanyVacanciesPage'
import CompanyVacancyPage from './pages/CompanyVacancyPage'
import VacancyEditorPage from './pages/VacancyEditorPage'
import VacanciesPage from './pages/VacanciesPage'
import VacancyPage from './pages/VacancyPage'

/** `/`: mehmon — landing (CONTRACT.md §14), kirgan — o'z bosh sahifasi (talaba — dashboard). */
function Home() {
  const { user, loading, can } = useAuth()
  if (loading) return null
  if (!user) return <LandingPage />
  return <Navigate to={can('receive_offers') ? '/dashboard' : homeFor(user)} replace />
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <div className="relative min-h-screen text-foreground">
            <Backdrop />
            <Navbar />
            <OfflineBanner />
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
              <Route path="/simulations" element={<RequireAuth><SimulationsPage /></RequireAuth>} />
              <Route path="/runs/:id" element={<RequireAuth><RunPage /></RequireAuth>} />
              <Route path="/runs/:id/report" element={<RequireAuth><RunReportPage /></RequireAuth>} />
              <Route path="/notifications" element={<RequireAuth><NotificationsPage /></RequireAuth>} />
              <Route path="/offers" element={<RequirePermission permission="receive_offers"><OffersPage /></RequirePermission>} />
              <Route path="/vacancies" element={<RequirePermission permission="receive_offers"><VacanciesPage /></RequirePermission>} />
              <Route path="/vacancies/:id" element={<RequirePermission permission="receive_offers"><VacancyPage /></RequirePermission>} />
              <Route path="/company/vacancies" element={<RequirePermission permission="manage_vacancies"><CompanyVacanciesPage /></RequirePermission>} />
              <Route path="/company/vacancies/new" element={<RequirePermission permission="manage_vacancies"><VacancyEditorPage key="new" /></RequirePermission>} />
              <Route path="/company/vacancies/:id" element={<RequirePermission permission="manage_vacancies"><CompanyVacancyPage /></RequirePermission>} />
              <Route path="/company/vacancies/:id/edit" element={<RequirePermission permission="manage_vacancies"><VacancyEditorPage /></RequirePermission>} />
              <Route path="/talents" element={<RequirePermission permission="view_candidates"><TalentsPage /></RequirePermission>} />
              <Route path="/talents/offers" element={<RequirePermission permission="view_candidates"><SentOffersPage /></RequirePermission>} />
              <Route path="/talents/report" element={<RequirePermission permission="view_candidates"><CompanyReportPage /></RequirePermission>} />
              <Route path="/admin" element={<RequirePermission permission={['approve_companies', 'manage_billing', 'view_platform_stats']}><AdminPage /></RequirePermission>} />
              <Route path="/admin/scenarios" element={<RequirePermission permission="manage_simulations"><ScenarioListPage /></RequirePermission>} />
              <Route path="/admin/scenarios/new" element={<RequirePermission permission="manage_simulations"><ScenarioEditorPage key="new" /></RequirePermission>} />
              <Route path="/admin/scenarios/:id/edit" element={<RequirePermission permission="manage_simulations"><ScenarioEditorPage /></RequirePermission>} />
              <Route path="/university" element={<RequirePermission permission="manage_universities"><UniversityPage /></RequirePermission>} />
              <Route path="/portfolio" element={<RequirePermission permission="manage_portfolio"><PortfolioPage /></RequirePermission>} />
              <Route path="/c/:code" element={<CertificatePage />} />
              <Route path="/p/:slug" element={<PortfolioPublicPage />} />
              <Route path="/billing" element={<RequirePermission permission="view_org_invoices"><BillingPage /></RequirePermission>} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
