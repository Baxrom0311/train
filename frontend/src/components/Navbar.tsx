import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  Menu, 
  X,
  Plus,
  User,
  LogOut,
  Building2,
  GraduationCap,
  School,
  LogIn
} from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import { useAuth } from '../context/AuthContext';
import { AuthModal } from './AuthModal';
import { Logo } from './Logo';

interface NavbarProps {
  currentView?: string;
  onNavigate?: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const { lang, setLang, t } = useLanguage();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const navLinks = [
    { id: 'catalog', path: '/catalog', label: t('nav_simulations') },
    { id: 'casecups', path: '/case-cups', label: t('nav_case_cup') },
    { id: 'talenthunt', path: '/talent-hunt', label: t('nav_talent_hunt') },
    { id: 'university', path: '/university', label: t('nav_university') },
  ];

  const handleNavClick = (path: string, id: string) => {
    if (onNavigate) {
      onNavigate(id);
    }
    navigate(path);
    setMobileMenuOpen(false);
  };

  const handleCreateSimulationClick = () => {
    if (!isAuthenticated || user?.role !== 'company_hr') {
      setAuthModalOpen(true);
      return;
    }
    if (onNavigate) {
      onNavigate('create-simulation');
    }
    navigate('/create-simulation');
    setMobileMenuOpen(false);
  };

  const languages: { code: Language; label: string }[] = [
    { code: 'uz', label: 'UZ' },
    { code: 'ru', label: 'RU' },
    { code: 'en', label: 'EN' },
  ];


  return (
    <>
      <header className="sticky top-0 z-50 border-b border-white/5 bg-[#07090E]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          
          {/* 1. Logo: TryJob */}
          <button 
            onClick={() => handleNavClick('/', 'landing')} 
            className="flex items-center gap-2.5 group cursor-pointer"
          >
            <Logo size={34} />
            <span className="text-xl font-bold tracking-tight text-white">
              Try<span className="text-indigo-400">Job</span>
            </span>
          </button>

          {/* 2. Desktop Navigatsiya */}
          <nav className="hidden md:flex items-center gap-1 bg-white/[0.03] border border-white/5 p-1 rounded-full">
            {navLinks.map((item) => {
              const isActive = location.pathname === item.path || (item.path === '/catalog' && location.pathname.startsWith('/catalog')) || (item.path === '/case-cups' && (location.pathname.startsWith('/case-cups') || location.pathname.startsWith('/casecups'))) || currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.path, item.id)}
                  className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* 3. O'ng Tomon: Til Tanlash + Profil / Kirish */}
          <div className="hidden sm:flex items-center gap-3">
            
            {/* Til Tanlagich */}
            <div className="flex items-center bg-white/[0.03] border border-white/10 rounded-lg p-0.5 text-xs font-bold">
              {languages.map((l) => (
                <button
                  key={l.code}
                  onClick={() => setLang(l.code)}
                  className={`px-2 py-1 rounded-md transition-colors ${
                    lang === l.code
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>

            {/* Simulyatsiya Yaratish Tugmasi */}
            <button
              onClick={handleCreateSimulationClick}
              className="px-3.5 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-300 hover:text-white transition-all flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5 text-indigo-400" />
              <span>{t('nav_create_simulation')}</span>
            </button>

            {/* Profil / Kirish */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2 pl-2 border-l border-white/10">
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/10">
                  <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-xs text-indigo-300">
                    {user.role === 'company_hr' ? (
                      <Building2 className="w-3.5 h-3.5 text-purple-400" />
                    ) : user.role === 'university_dean' ? (
                      <School className="w-3.5 h-3.5 text-cyan-400" />
                    ) : (
                      <GraduationCap className="w-3.5 h-3.5 text-indigo-400" />
                    )}
                  </div>
                  <div className="text-left leading-tight">
                    <div className="text-[11px] font-bold text-white max-w-[100px] truncate">
                      {user.company_name || user.full_name}
                    </div>
                    <div className="text-[9px] text-slate-400 capitalize">
                      {user.role === 'company_hr' ? 'HR Vakili' : user.role === 'university_dean' ? 'Dekanat' : 'Talaba'}
                    </div>
                  </div>
                </div>

                <button
                  onClick={logout}
                  title="Chiqish"
                  className="p-1.5 rounded-lg bg-white/[0.03] hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition shadow-sm flex items-center gap-1.5"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Kirish</span>
              </button>
            )}

          </div>

          {/* 4. Mobil Menyu Tugmasi */}
          <div className="flex items-center gap-2 md:hidden">
            <button
              onClick={() => setAuthModalOpen(true)}
              className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-bold"
            >
              {isAuthenticated ? 'Profil' : 'Kirish'}
            </button>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-white/[0.03] border border-white/10 text-slate-400 hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>

        {/* Mobil Menyu Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/5 bg-[#07090E]/95 backdrop-blur-2xl px-4 py-4 space-y-2">
            {navLinks.map((item) => {
              const isActive = location.pathname === item.path || (item.path === '/catalog' && location.pathname.startsWith('/catalog')) || (item.path === '/case-cups' && (location.pathname.startsWith('/case-cups') || location.pathname.startsWith('/casecups'))) || currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.path, item.id)}
                  className={`w-full px-4 py-2.5 rounded-xl text-sm font-medium flex items-center justify-between transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-300 hover:bg-white/[0.04]'
                  }`}
                >
                  <span>{item.label}</span>
                </button>
              );
            })}
            <div className="pt-2 border-t border-white/5 space-y-2">
              <button
                onClick={handleCreateSimulationClick}
                className="w-full px-4 py-2.5 rounded-xl bg-indigo-600/10 border border-indigo-500/30 text-indigo-300 font-semibold text-sm flex items-center justify-center gap-2"
              >
                <Plus className="w-4 h-4" />
                <span>{t('nav_create_simulation')}</span>
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Auth & Company Registration Modal */}
      <AuthModal 
        isOpen={authModalOpen} 
        onClose={() => setAuthModalOpen(false)} 
      />
    </>
  );
};
