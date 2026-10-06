import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useParams, useLocation, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { LandingPage } from './pages/LandingPage';
import { CatalogPage } from './pages/CatalogPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { VerifyCertificatePage } from './pages/VerifyCertificatePage';
import { CaseCupsPage } from './pages/CaseCupsPage';
import { TalentHuntPage } from './pages/TalentHuntPage';
import { UniversityPortalPage } from './pages/UniversityPortalPage';
import { SimulationBuilderPage } from './pages/SimulationBuilderPage';
import { MockInterviewModal } from './components/MockInterviewModal';
import { DocumentAuditModal } from './components/DocumentAuditModal';
import { fetchSimulations } from './api';
import { Simulation } from './types';

// Scroll to top on every route change
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname]);
  return null;
}

// Workspace Page Wrapper (Extracts :slug from URL)
function WorkspaceRoute({ 
  onOpenInterview, 
  onOpenDocAudit 
}: { 
  onOpenInterview: (slug: string) => void;
  onOpenDocAudit: () => void;
}) {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const activeSlug = slug || 'jpmorgan-software-engineering';

  return (
    <WorkspacePage
      simulationSlug={activeSlug}
      onBack={() => navigate('/catalog')}
      onOpenInterview={() => onOpenInterview(activeSlug)}
      onOpenDocAudit={onOpenDocAudit}
      onViewCertificate={(certUuid) => navigate(`/verify/${certUuid}`)}
    />
  );
}

// Certificate Verification Route Wrapper (Extracts :certUuid from URL)
function VerifyCertificateRoute() {
  const { certUuid } = useParams<{ certUuid: string }>();
  const navigate = useNavigate();
  const activeCertUuid = certUuid || 'TJ-2026-9842-UZB';

  return (
    <VerifyCertificatePage
      certUuid={activeCertUuid}
      onBack={() => navigate('/catalog')}
    />
  );
}

export function App() {
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const navigate = useNavigate();
  
  // Interactive Modals
  const [interviewOpen, setInterviewOpen] = useState<boolean>(false);
  const [activeInterviewSlug, setActiveInterviewSlug] = useState<string>('jpmorgan-software-engineering');
  const [docAuditOpen, setDocAuditOpen] = useState<boolean>(false);

  useEffect(() => {
    loadCatalog();
  }, []);

  const loadCatalog = async () => {
    try {
      const data = await fetchSimulations();
      setSimulations(data);
    } catch (e) {
      console.error('Simulations load error:', e);
    }
  };

  const handleNavigate = (view: string) => {
    if (view === 'landing') navigate('/');
    else if (view === 'catalog') navigate('/catalog');
    else if (view === 'casecups' || view === 'case_cups') navigate('/case-cups');
    else if (view === 'talenthunt' || view === 'talent_hunt') navigate('/talent-hunt');
    else if (view === 'university') navigate('/university');
    else if (view === 'create-simulation') navigate('/create-simulation');
    else if (view === 'verify_certificate' || view === 'verify') navigate('/verify/TJ-2026-9842-UZB');
    else if (view.startsWith('/')) navigate(view);
    else navigate(`/${view}`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950">
      <ScrollToTop />
      
      {/* Global Sticky Navigation Bar */}
      <Navbar onNavigate={handleNavigate} />

      {/* Main Routed Content */}
      <main className="flex-1">
        <Routes>
          {/* 1. Landing Page */}
          <Route 
            path="/" 
            element={
              <LandingPage
                simulations={simulations}
                onSelectSimulation={(slug) => navigate(`/workspace/${slug}`)}
                onNavigate={handleNavigate}
              />
            } 
          />

          {/* 2. Simulation Catalog */}
          <Route 
            path="/catalog" 
            element={
              <CatalogPage
                simulations={simulations}
                onSelectSimulation={(slug) => navigate(`/workspace/${slug}`)}
                onNavigate={handleNavigate}
              />
            } 
          />

          {/* 3. Interactive Workspace by Slug (e.g. /workspace/jpmorgan-software-engineering) */}
          <Route 
            path="/workspace/:slug" 
            element={
              <WorkspaceRoute
                onOpenInterview={(slug) => {
                  setActiveInterviewSlug(slug);
                  setInterviewOpen(true);
                }}
                onOpenDocAudit={() => setDocAuditOpen(true)}
              />
            } 
          />
          <Route 
            path="/workspace" 
            element={<Navigate to="/workspace/jpmorgan-software-engineering" replace />} 
          />

          {/* 4. National Case Cups */}
          <Route 
            path="/case-cups" 
            element={<CaseCupsPage onSelectSimulation={(slug) => navigate(`/workspace/${slug}`)} />} 
          />
          <Route 
            path="/casecups" 
            element={<Navigate to="/case-cups" replace />} 
          />

          {/* 5. HR Talent Hunt */}
          <Route 
            path="/talent-hunt" 
            element={<TalentHuntPage />} 
          />
          <Route 
            path="/talenthunt" 
            element={<Navigate to="/talent-hunt" replace />} 
          />

          {/* 6. University Portal */}
          <Route 
            path="/university" 
            element={<UniversityPortalPage />} 
          />

          {/* 7. HR / Author Simulation Builder */}
          <Route 
            path="/create-simulation" 
            element={
              <SimulationBuilderPage
                onSimulationCreated={(slug) => {
                  loadCatalog();
                  navigate(`/workspace/${slug}`);
                }}
                onNavigate={handleNavigate}
              />
            } 
          />
          <Route 
            path="/builder" 
            element={<Navigate to="/create-simulation" replace />} 
          />

          {/* 8. Certificate Public Verification */}
          <Route 
            path="/verify/:certUuid" 
            element={<VerifyCertificateRoute />} 
          />
          <Route 
            path="/verify" 
            element={<Navigate to="/verify/TJ-2026-9842-UZB" replace />} 
          />

          {/* 9. Catch-All Fallback */}
          <Route 
            path="*" 
            element={<Navigate to="/" replace />} 
          />
        </Routes>
      </main>

      {/* Global Footer */}
      <Footer />

      {/* Interactive Modals */}
      <MockInterviewModal
        isOpen={interviewOpen}
        onClose={() => setInterviewOpen(false)}
        simulationSlug={activeInterviewSlug}
      />

      <DocumentAuditModal
        isOpen={docAuditOpen}
        onClose={() => setDocAuditOpen(false)}
      />
    </div>
  );
}

export default App;

