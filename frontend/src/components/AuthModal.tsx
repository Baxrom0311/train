import React, { useState } from 'react';
import { 
  X, 
  Building2, 
  GraduationCap, 
  School, 
  ArrowRight, 
  Lock, 
  Mail, 
  User, 
  Globe, 
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Logo } from './Logo';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultRole?: 'student' | 'company_hr' | 'university_dean';
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, defaultRole = 'student' }) => {
  const { login, registerCompany } = useAuth();
  const [activeTab, setActiveTab] = useState<'login' | 'register_company'>('login');
  const [selectedRole, setSelectedRole] = useState<'student' | 'company_hr' | 'university_dean'>(defaultRole);

  // Form states
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  
  // Company Registration states
  const [companyName, setCompanyName] = useState<string>('');
  const [industry, setIndustry] = useState<string>('Fintech & Banking');
  const [website, setWebsite] = useState<string>('');
  const [hrName, setHrName] = useState<string>('');
  const [hrEmail, setHrEmail] = useState<string>('');

  if (!isOpen) return null;

  const handleQuickLogin = (role: 'student' | 'company_hr' | 'university_dean') => {
    if (role === 'company_hr') {
      login('hr@kapitalbank.uz', 'company_hr');
    } else if (role === 'university_dean') {
      login('dean@urdu.uz', 'university_dean');
    } else {
      login('student@tryjob.uz', 'student');
    }
    onClose();
  };

  const handleCustomLogin = (e: React.FormEvent) => {
    e.preventDefault();
    login(email || 'student@tryjob.uz', selectedRole);
    onClose();
  };

  const handleCompanyRegister = (e: React.FormEvent) => {
    e.preventDefault();
    registerCompany({
      name: companyName || 'Mening Korxonam',
      industry: industry,
      website: website || 'https://company.uz',
      logo_url: 'https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=120&auto=format&fit=crop&q=80',
      hr_name: hrName || 'HR Boshqaruvchisi',
      email: hrEmail || 'hr@company.uz'
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg rounded-3xl bg-[#0B0F19] border border-white/10 shadow-2xl overflow-hidden p-6 sm:p-8 space-y-6">
        
        {/* Yopish tugmasi */}
        <button 
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Sarlavhasi */}
        <div className="text-center space-y-2">
          <Logo size={44} className="mx-auto" />
          <h3 className="text-2xl font-bold text-white tracking-tight">
            {activeTab === 'login' ? 'TryJob Tizimiga Kirish' : 'Kompaniyani Ro\'yxatdan O\'tkazish'}
          </h3>
          <p className="text-xs text-slate-400">
            {activeTab === 'login' 
              ? 'Rolingizni tanlang va profilingizga kiring' 
              : 'Kompaniyangiz nomidan simulyatsiya yaratish uchun profil oching'}
          </p>
        </div>

        {/* Tablar */}
        <div className="flex bg-white/5 p-1 rounded-xl border border-white/5 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('login')}
            className={`flex-1 py-2 rounded-lg transition ${
              activeTab === 'login' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Mavjud Profilga Kirish
          </button>
          <button
            onClick={() => setActiveTab('register_company')}
            className={`flex-1 py-2 rounded-lg transition ${
              activeTab === 'register_company' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            🏢 Kompaniya Ochish (HR)
          </button>
        </div>

        {activeTab === 'login' ? (
          <div className="space-y-5">
            
            {/* Tezkor Kirish (1-Click Demo Profiles) */}
            <div className="space-y-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tezkor Demo Kirish:</span>
              <div className="grid grid-cols-3 gap-2">
                
                <button
                  type="button"
                  onClick={() => handleQuickLogin('student')}
                  className="p-3 rounded-xl bg-white/[0.03] hover:bg-indigo-600/20 border border-white/10 hover:border-indigo-500/40 transition text-center space-y-1.5 group"
                >
                  <GraduationCap className="w-5 h-5 mx-auto text-indigo-400 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-white">Talaba</div>
                  <div className="text-[10px] text-slate-400">UrDU</div>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('company_hr')}
                  className="p-3 rounded-xl bg-white/[0.03] hover:bg-purple-600/20 border border-white/10 hover:border-purple-500/40 transition text-center space-y-1.5 group"
                >
                  <Building2 className="w-5 h-5 mx-auto text-purple-400 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-white">Kompaniya HR</div>
                  <div className="text-[10px] text-slate-400">Kapitalbank</div>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('university_dean')}
                  className="p-3 rounded-xl bg-white/[0.03] hover:bg-cyan-600/20 border border-white/10 hover:border-cyan-500/40 transition text-center space-y-1.5 group"
                >
                  <School className="w-5 h-5 mx-auto text-cyan-400 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-white">OTM Dekani</div>
                  <div className="text-[10px] text-slate-400">UrDU</div>
                </button>

              </div>
            </div>

            <div className="relative flex items-center justify-center">
              <span className="h-px bg-white/10 w-full" />
              <span className="px-3 text-[10px] text-slate-500 bg-[#0B0F19] uppercase">yoki email orqali</span>
            </div>

            {/* Qo'lda Kirish Formasi */}
            <form onSubmit={handleCustomLogin} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300">Email Manzil</label>
                <div className="relative mt-1">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="student@tryjob.uz yoki hr@company.uz"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Parol</label>
                <div className="relative mt-1">
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-95 text-white font-bold text-xs transition shadow-lg shadow-indigo-500/25 mt-2"
              >
                Tizimga Kirish
              </button>
            </form>

          </div>
        ) : (
          /* Kompaniya Ro'yxatdan O'tkazish */
          <form onSubmit={handleCompanyRegister} className="space-y-3">
            <div>
              <label className="text-xs font-medium text-slate-300">Kompaniya Nomi *</label>
              <input
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Masalan: Uzum Technologies, Kapitalbank..."
                className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 mt-1"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-medium text-slate-300">Soha / Industry</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#131826] border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500 mt-1"
                >
                  <option value="Fintech & Banking">Fintech & Banking</option>
                  <option value="Software Engineering">Software Engineering</option>
                  <option value="Audit & Advisory">Audit & Advisory</option>
                  <option value="E-Commerce & Retail">E-Commerce & Retail</option>
                  <option value="Telecom & IT">Telecom & IT</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Veb-sayt</label>
                <input
                  type="text"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  placeholder="https://company.uz"
                  className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 mt-1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-medium text-slate-300">HR Mas'ul Shaxs *</label>
                <input
                  type="text"
                  required
                  value={hrName}
                  onChange={(e) => setHrName(e.target.value)}
                  placeholder="Ism Familiya"
                  className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 mt-1"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Korporativ Email *</label>
                <input
                  type="email"
                  required
                  value={hrEmail}
                  onChange={(e) => setHrEmail(e.target.value)}
                  placeholder="hr@company.uz"
                  className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 mt-1"
                />
              </div>
            </div>

            <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-[11px] text-indigo-300 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0 text-indigo-400 mt-0.5" />
              <span>Kompaniyangiz ro'yxatdan o'tgach, sizga bepul <strong>Simulation Builder</strong> va <strong>Talent Hunt</strong> huquqi beriladi.</span>
            </div>

            <button
              type="submit"
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-95 text-white font-bold text-xs transition shadow-lg shadow-indigo-500/25 mt-2 flex items-center justify-center gap-2"
            >
              <span>Kompaniyani Ochish va Simulyatsiya Yaratish</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

      </div>
    </div>
  );
};
