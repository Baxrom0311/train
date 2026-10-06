import React, { useState } from 'react';
import { 
  ArrowRight, 
  CheckCircle2, 
  XCircle, 
  Briefcase, 
  GraduationCap, 
  Building2, 
  ShieldCheck, 
  Sparkles,
  Trophy,
  Users,
  Award,
  TrendingUp,
  FileCheck2,
  Zap,
  QrCode,
  Send,
  Star,
  DownloadCloud,
  Code2,
  Check,
  ChevronRight,
  Clock,
  Layers,
  BarChart3,
  Terminal,
  Play,
  FileText,
  BadgeCheck,
  ExternalLink
} from 'lucide-react';
import { Simulation } from '../types';
import { useLanguage } from '../i18n/LanguageContext';

interface LandingPageProps {
  onNavigate?: (view: any) => void;
  onSelectSimulation?: (slug: string) => void;
  simulations?: Simulation[];
}

export const LandingPage: React.FC<LandingPageProps> = ({ 
  onNavigate = () => {}, 
  onSelectSimulation = () => {},
  simulations = [] 
}) => {
  const { t, lang } = useLanguage();
  const [activeHeroTab, setActiveHeroTab] = useState<'briefing' | 'code' | 'review'>('review');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const partnerLogos = [
    { name: 'Kapitalbank ATB', badge: 'Bank & FinTech', color: 'from-amber-400 to-orange-500' },
    { name: 'Uzum Technologies', badge: 'E-Commerce & Ecosystem', color: 'from-purple-400 to-indigo-500' },
    { name: 'PwC Uzbekistan', badge: 'Audit & Consulting', color: 'from-rose-400 to-red-500' },
    { name: 'JPMorgan Chase', badge: 'Investment Banking', color: 'from-blue-400 to-cyan-500' },
    { name: 'Goldman Sachs', badge: 'Cybersecurity & Tech', color: 'from-emerald-400 to-teal-500' },
    { name: 'BCG', badge: 'Strategy Consulting', color: 'from-cyan-400 to-blue-500' }
  ];

  // Default featured simulation list
  const defaultSims: Simulation[] = [
    {
      id: 'sim-1',
      slug: 'jpmorgan-software-engineering',
      title: 'JPMorgan Chase — Software Engineering & Algorithmic Trading',
      category: 'Engineering',
      difficulty: 'Middle',
      estimated_hours: 5,
      description: 'Moliyaviy ma\'lumotlar tahlili, bozor kotirovkalari vizualizatsiyasi va real-vaqt narxlar korrelyatsiyasi tizimini qurish.',
      company: {
        id: 'c1',
        name: 'JPMorgan Chase & Co.',
        logo_url: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=120&q=80',
        industry: 'Investment Banking',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['Python & Pandas', 'Data Visualisation', 'Financial Engineering']
    },
    {
      id: 'sim-2',
      slug: 'kapitalbank-credit-analyst',
      title: 'Kapitalbank — AI Credit Scoring & Risk Modeling',
      category: 'Finance',
      difficulty: 'Junior',
      estimated_hours: 4,
      description: 'Chakana kredit arizalarini tahlil qilish, defolt ehtimolini bashorat qiluvchi skoring modelini Python va SQL da sinash.',
      company: {
        id: 'c2',
        name: 'Kapitalbank ATB',
        logo_url: 'https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=120&q=80',
        industry: 'Banking',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['DTI Tahlil', 'Kredit Riski', 'Scoring Model']
    },
    {
      id: 'sim-3',
      slug: 'uzum-ecommerce-ai-cup-2026',
      title: 'Uzum Technologies — E-Commerce AI & Recommendation Engine',
      category: 'Engineering',
      difficulty: 'Senior',
      estimated_hours: 6,
      description: '100,000+ RPS yuklamali to\'lov shlyuzi, Redis tranzaksiyalar keshlanishi va firibgarlikni aniqlovchi AI filtrlar.',
      company: {
        id: 'c3',
        name: 'Uzum Technologies',
        logo_url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=120&q=80',
        industry: 'FinTech & AI',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['High-Load Backend', 'Anti-Fraud ML', 'Redis & Cache']
    },
    {
      id: 'sim-4',
      slug: 'goldman-sachs-cybersecurity',
      title: 'Goldman Sachs — Kiberxavfsizlik va Kriptografik Himoya',
      category: 'Engineering',
      difficulty: 'Advanced',
      estimated_hours: 4.5,
      description: 'Parollar bazasidagi sizib chiqishlarni tahlil qilish, Rainbow Table hujumlariga qarshi PBKDF2/Argon2id arxitekturasini joriy etish.',
      company: {
        id: 'c4',
        name: 'Goldman Sachs',
        logo_url: 'https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=120&q=80',
        industry: 'Cybersecurity',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['Kriptografiya', 'Rainbow Table Himoyasi', 'Argon2id Standarti']
    },
    {
      id: 'sim-5',
      slug: 'bcg-strategy-consulting',
      title: 'BCG (Boston Consulting Group) — Bozor Strategiyasi va Unit-Ekonomika',
      category: 'Analytics',
      difficulty: 'Advanced',
      estimated_hours: 4.5,
      description: 'Markaziy Osiyo elektron tijorat bozorini tahlil qilish, TAM/SAM/SOM modelini tuzish va bozorga kirish memorandumini yozish.',
      company: {
        id: 'c5',
        name: 'BCG Central Asia',
        logo_url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=120&q=80',
        industry: 'Strategy Consulting',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['TAM/SAM/SOM', 'Unit Economics', 'Executive Memo']
    },
    {
      id: 'sim-6',
      slug: 'kapitalbank-fintech-cup-2026',
      title: 'Kapitalbank FinTech Cup 2026 — 50,000,000 UZS Chempionati',
      category: 'Finance',
      difficulty: 'Intermediate',
      estimated_hours: 6,
      description: 'Humo va Uzcard tranzaksiyalari oqimi, firibgarlikni (Anti-Fraud) real vaqtda aniqlash va Open Banking mahsulot strategiyasi.',
      company: {
        id: 'c6',
        name: 'Kapitalbank ATB',
        logo_url: 'https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=120&q=80',
        industry: 'FinTech Championship',
        description: '',
        website: '',
        is_verified: true
      },
      learning_outcomes: ['Anti-Fraud Engine', 'Open Banking', '50M UZS Sovrin']
    }
  ];

  const allSims = simulations.length > 0 ? simulations : defaultSims;
  const filteredSims = selectedCategory === 'all' 
    ? allSims 
    : allSims.filter(s => s.category.toLowerCase().includes(selectedCategory.toLowerCase()));

  return (
    <div className="min-h-screen bg-[#06080F] text-slate-100 selection:bg-indigo-500 selection:text-white font-sans overflow-x-hidden relative">
      
      {/* Background Subtle Grid Accent */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none -z-10" />

      {/* ── 1. HERO SECTION ────────────────────────────────────────────────── */}
      <section className="relative pt-24 pb-20 md:pt-32 md:pb-28 overflow-hidden border-b border-white/5">
        {/* Soft Ambient Blur Glows */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] md:w-[1000px] h-[400px] bg-gradient-to-r from-indigo-600/20 via-purple-600/15 to-cyan-500/15 blur-[140px] -z-10 rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
            
            {/* Chap tomon: Sarlavha, Subtitle va Harakat Tugmalari */}
            <div className="lg:col-span-6 space-y-7 text-center lg:text-left">
              
              {/* Badge */}
              <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/10 backdrop-blur-md text-xs font-semibold text-slate-200 shadow-sm">
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                </span>
                <span className="bg-gradient-to-r from-indigo-300 via-purple-300 to-cyan-300 bg-clip-text text-transparent font-bold">TryJob</span>
                <span className="text-slate-600">•</span>
                <span className="text-slate-300 font-normal">Virtual Ish Simulyatsiyasi</span>
              </div>

              {/* Sarlavha */}
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.1] text-white">
                Kompaniyalar vazifalarini bajaring.{' '}
                <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
                  Tajriba orttiring va ish taklifi oling.
                </span>
              </h1>

              {/* Tavsif */}
              <p className="text-base sm:text-lg text-slate-300 font-normal leading-relaxed max-w-xl mx-auto lg:mx-0">
                Ishga kirmasdan turib Kapitalbank, Uzum, PwC va JPMorgan kabi yetakchi kompaniyalarning real keyslarini hal qiling, portfoliosini isbotlang va to'g'ridan-to'g'ri taklif oling.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 pt-1">
                <button 
                  onClick={() => onNavigate('catalog')}
                  className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-base shadow-xl shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:-translate-y-0.5 transition-all flex items-center justify-center gap-3 group cursor-pointer border border-indigo-400/30"
                >
                  <span>Simulyatsiyalarni Boshlash</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
                </button>
                
                <button 
                  onClick={() => onNavigate('case_cups')}
                  className="w-full sm:w-auto px-7 py-4 rounded-2xl bg-white/[0.05] hover:bg-white/[0.08] border border-white/10 hover:border-white/20 text-slate-200 hover:text-white font-semibold text-base transition-all flex items-center justify-center gap-2.5 backdrop-blur-sm cursor-pointer"
                >
                  <Trophy className="w-5 h-5 text-amber-400" />
                  <span>Case Cup (150M Sovrin)</span>
                </button>
              </div>

              {/* Trust Indicators */}
              <div className="pt-2 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[10px] font-bold">✓</div>
                  <span>100% Bepul amaliyot</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-[10px] font-bold">✓</div>
                  <span>QR Verifikatsiyali Sertifikat</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-[10px] font-bold">✓</div>
                  <span>HR Talent Hunt saralashi</span>
                </div>
              </div>

            </div>

            {/* O'ng tomon: Interactive Workspace UI Simulator Mockup */}
            <div className="lg:col-span-6 relative">
              <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-indigo-500/25 via-purple-500/20 to-cyan-500/20 blur-xl opacity-70 -z-10" />

              <div className="rounded-3xl p-1 bg-gradient-to-b from-white/15 via-white/5 to-transparent border border-white/10 shadow-2xl backdrop-blur-xl">
                <div className="rounded-[22px] bg-[#0A0D17] p-5 space-y-4 border border-white/5">
                  
                  {/* Top Header Controls */}
                  <div className="flex items-center justify-between border-b border-white/5 pb-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                      <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                      <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                      <span className="text-[11px] font-mono text-slate-400 ml-2">tryjob.uz / workspace / live</span>
                    </div>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono border border-emerald-500/30 flex items-center gap-1.5 font-bold">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      AI MENTOR ONLINE
                    </span>
                  </div>

                  {/* Company Header */}
                  <div className="flex items-center justify-between bg-white/[0.02] p-3 rounded-2xl border border-white/5">
                    <div className="flex items-center gap-3">
                      <img 
                        src="https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=80&q=80" 
                        alt="Kapitalbank" 
                        className="w-10 h-10 rounded-xl object-cover border border-white/10" 
                      />
                      <div>
                        <div className="text-xs font-bold text-white flex items-center gap-1.5">
                          Kapitalbank ATB
                          <BadgeCheck className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div className="text-[11px] text-slate-400">Chakana Kredit Riski & DTI Skoringi • 1-Topshiriq</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-emerald-400">96.0% Natija</div>
                      <div className="text-[10px] text-slate-400">+35 ELO Reyting</div>
                    </div>
                  </div>

                  {/* Interactive Tab Buttons on Mockup */}
                  <div className="grid grid-cols-3 gap-1.5 p-1 rounded-xl bg-slate-950/80 border border-white/5 text-[11px] font-medium text-slate-400">
                    <button 
                      onClick={() => setActiveHeroTab('briefing')}
                      className={`py-1.5 rounded-lg transition text-center cursor-pointer ${activeHeroTab === 'briefing' ? 'bg-indigo-600/30 text-white font-bold border border-indigo-500/30' : 'hover:text-slate-200'}`}
                    >
                      1. Brifing
                    </button>
                    <button 
                      onClick={() => setActiveHeroTab('code')}
                      className={`py-1.5 rounded-lg transition text-center cursor-pointer ${activeHeroTab === 'code' ? 'bg-indigo-600/30 text-white font-bold border border-indigo-500/30' : 'hover:text-slate-200'}`}
                    >
                      2. Yechim Kodi
                    </button>
                    <button 
                      onClick={() => setActiveHeroTab('review')}
                      className={`py-1.5 rounded-lg transition text-center cursor-pointer ${activeHeroTab === 'review' ? 'bg-indigo-600/30 text-white font-bold border border-indigo-500/30' : 'hover:text-slate-200'}`}
                    >
                      3. HR Xulosasi
                    </button>
                  </div>

                  {/* Mockup Tab Content */}
                  <div className="min-h-[140px] rounded-xl bg-slate-950/90 p-3.5 text-xs border border-white/5 space-y-2 font-mono">
                    {activeHeroTab === 'briefing' && (
                      <div className="text-slate-300 space-y-1.5 font-sans">
                        <div className="text-indigo-400 font-bold font-mono text-[11px]"># Vazifa Konteksti:</div>
                        <p className="text-[11px] text-slate-300 leading-relaxed">
                          "Mijozning oylik daromadi 8,000,000 UZS. Markaziy Bankning 3205-sonli nizomiga ko'ra DTI ko'rsatkichini hisoblang va 50% limitdan oshmaganligini tasdiqlang."
                        </p>
                      </div>
                    )}

                    {activeHeroTab === 'code' && (
                      <div className="space-y-1 text-[11px] text-slate-300">
                        <div className="text-slate-500">// DTI (Debt-To-Income) Hisoblash Algoritmi</div>
                        <div className="text-purple-400">def calculate_dti(monthly_income, existing_loans, new_loan):</div>
                        <div className="text-slate-400 pl-4">total_debt = existing_loans + new_loan</div>
                        <div className="text-cyan-400 pl-4">dti_ratio = (total_debt / monthly_income) * 100</div>
                        <div className="text-emerald-400 pl-4">return dti_ratio &lt;= 50.0 # Standard Pass</div>
                      </div>
                    )}

                    {activeHeroTab === 'review' && (
                      <div className="space-y-2 font-sans">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-300 font-bold flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                            AI Mentor Fikr-mulohazasi
                          </span>
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">Muvaffaqiyatli</span>
                        </div>
                        <p className="text-[11px] text-slate-300 leading-relaxed">
                          "DTI ko'rsatkichi 49.38% qilib to'g'ri hisoblandi. Markaziy Bank me'yorlariga 100% muvofiq. HR portali orqali suhbatga tavsiya etildi!"
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Direct Job Offer Toast */}
                  <div className="p-3 rounded-2xl bg-gradient-to-r from-emerald-950/70 via-slate-900 to-indigo-950/60 border border-emerald-500/30 flex items-center justify-between shadow-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                        <Send className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white flex items-center gap-1.5">
                          Kapitalbank HR Bo'limi
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-semibold">Oflayn Suhbat Taklifi</span>
                        </div>
                        <div className="text-[10px] text-slate-300">Junior Risk Analyst lavozimiga fast-track chaqiruv</div>
                      </div>
                    </div>
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping shrink-0" />
                  </div>

                  {/* Visual 3D Preview Expand Badge */}
                  <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <Code2 className="w-3.5 h-3.5 text-indigo-400" />
                      AST Xavfsiz Sandbox Muhiti
                    </span>
                    <span className="text-emerald-400 font-bold font-mono">100% REAL-TIME</span>
                  </div>

                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── 2. PARTNERS RIBBON ──────────────────────────────────────────────── */}
      <section className="py-10 border-b border-white/5 bg-white/[0.01]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-bold text-slate-500 uppercase tracking-widest mb-6">
            O'ZBEKISTON VA XALQARO BOZOR YETAKCHILARI BILAN HAMKORLIKDA
          </p>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 items-center">
            {partnerLogos.map((partner, i) => (
              <div 
                key={i}
                className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-white/15 hover:bg-white/[0.04] transition-all flex flex-col items-center justify-center text-center group cursor-default"
              >
                <span className="text-sm font-black text-slate-200 group-hover:text-white transition">
                  {partner.name}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5">
                  {partner.badge}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. METRICS / STATS BAR ─────────────────────────────────────────── */}
      <section className="py-12 border-b border-white/5 bg-gradient-to-b from-transparent via-white/[0.01] to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-indigo-500/40 transition-all space-y-1.5 group">
              <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                5,400+
              </div>
              <div className="text-sm font-bold text-white">Faol Talabalar</div>
              <div className="text-xs text-slate-400">Virtual keyslarni muvaffaqiyatli topshirgan</div>
            </div>

            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-purple-500/40 transition-all space-y-1.5 group">
              <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                24+
              </div>
              <div className="text-sm font-bold text-white">Kompaniyalar</div>
              <div className="text-xs text-slate-400">HR portalida to'g'ridan-to'g'ri kadr qidiradi</div>
            </div>

            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-cyan-500/40 transition-all space-y-1.5 group">
              <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
                94.2%
              </div>
              <div className="text-sm font-bold text-white">Suhbatga Chaqiruv</div>
              <div className="text-xs text-slate-400">85%+ ball to'plagan nomzodlar uchun</div>
            </div>

            <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-emerald-500/40 transition-all space-y-1.5 group">
              <div className="text-3xl sm:text-4xl font-black bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
                100% Bepul
              </div>
              <div className="text-sm font-bold text-white">Ochiq Amaliyot</div>
              <div className="text-xs text-slate-400">Barcha talabalar va yosh mutaxassislar uchun</div>
            </div>

          </div>
        </div>
      </section>

      {/* ── 4. THE PROBLEM VS TRYJOB SOLUTION ──────────────────────────────── */}
      <section className="py-20 md:py-28 border-b border-white/5 relative">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
              Muammo va Yechim
            </div>
            <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
              Karyerangizdagi 3 yillik to'siqni yengamiz
            </h2>
            <p className="text-sm sm:text-base text-slate-400">
              "Ishga kirish uchun tajriba kerak, tajriba to'plash uchun esa ishga olishmaydi." Biz ushbu muammoni to'liq hal qilamiz.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
            
            {/* Eski Yo'l */}
            <div className="p-8 rounded-3xl bg-rose-500/[0.03] border border-rose-500/20 space-y-6 flex flex-col justify-between hover:border-rose-500/40 transition">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-rose-500/20 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold">
                      <XCircle className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">Eski Yo'l (Zanjirli To'siq)</h3>
                      <p className="text-xs text-rose-300">An'anaviy rezyumelar orqali saralash</p>
                    </div>
                  </div>
                </div>

                {/* Problem Visual Graphic PNG */}
                <div className="rounded-2xl overflow-hidden border border-rose-500/20 shadow-lg group">
                  <img 
                    src="/assets/problem_barrier.png" 
                    alt="Eski yo'l to'sig'i" 
                    className="w-full h-auto object-cover group-hover:scale-[1.02] transition-transform duration-300"
                  />
                </div>

                <ul className="space-y-3.5 text-sm text-slate-300 pt-2">
                  <li className="flex items-start gap-3">
                    <span className="text-rose-400 font-bold mt-0.5">✕</span>
                    <span>4 yil faqat nazariy o'qish va diplom</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-rose-400 font-bold mt-0.5">✕</span>
                    <span>100+ ta kompaniyaga javobsiz bo'sh rezyume yuborish</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-rose-400 font-bold mt-0.5">✕</span>
                    <span>"Sizda amaliy tajriba yo'q" degan standart rad javoblari</span>
                  </li>
                </ul>
              </div>

              <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/20 text-xs text-rose-200">
                Natija: 6 oydan 1 yilgacha vaqt yo'qotish va sohada ish topa olmaslik.
              </div>
            </div>

            {/* TryJob Yechimi */}
            <div className="p-8 rounded-3xl bg-emerald-500/[0.04] border border-emerald-500/30 space-y-6 flex flex-col justify-between hover:border-emerald-500/60 transition shadow-xl shadow-emerald-950/20">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-emerald-500/20 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-white">TryJob Yo'li (To'g'ridan-to'g'ri Natija)</h3>
                      <p className="text-xs text-emerald-300">Amalda ko'rsatilgan mahorat va taklif</p>
                    </div>
                  </div>
                </div>

                {/* Solution Visual Graphic PNG */}
                <div className="rounded-2xl overflow-hidden border border-emerald-500/30 shadow-lg group">
                  <img 
                    src="/assets/solution_tryjob.png" 
                    alt="TryJob amaliy yechimi" 
                    className="w-full h-auto object-cover group-hover:scale-[1.02] transition-transform duration-300"
                  />
                </div>

                <ul className="space-y-3.5 text-sm text-slate-200 pt-2">
                  <li className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold mt-0.5">✓</span>
                    <span>4-5 soatlik amaliy korporativ simulyatsiya</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold mt-0.5">✓</span>
                    <span>Kompaniyaning real keyslarini hal qilish va AI taqrizi olish</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="text-emerald-400 font-bold mt-0.5">✓</span>
                    <span>QR-kod bilan tasdiqlanuvchi portfolio va HR dan to'g'ridan-to'g'ri taklif</span>
                  </li>
                </ul>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-950/50 border border-emerald-500/30 text-xs text-emerald-200 font-medium">
                Natija: 1 hafta ichida isbotlangan tajriba va to'g'ridan-to'g'ri suhbat chaqiruvi.
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* ── 5. HOW IT WORKS (3 CLEAR STEPS) ────────────────────────────────── */}
      <section className="py-20 md:py-28 border-b border-white/5 bg-gradient-to-b from-transparent via-white/[0.01] to-transparent">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
              Oddiy va Aniq Jarayon
            </div>
            <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
              TryJob qanday ishlaydi?
            </h2>
            <p className="text-sm sm:text-base text-slate-400">
              Karyerangizni boshlash uchun 3 ta aniq qadam
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* 1-Qadam */}
            <div className="p-7 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-indigo-500/40 hover:bg-white/[0.04] transition-all space-y-4 group">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-black text-xl border border-indigo-500/20 group-hover:scale-105 transition-transform">
                01
              </div>
              <h3 className="text-lg font-bold text-white">Kompaniya Keysini Tanlang</h3>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Kapitalbank, Uzum, PwC yoki JPMorgan kabi yetakchi brendlarning soha simulyatsiyasini o'zingizga mos yo'nalishda tanlang.
              </p>
            </div>

            {/* 2-Qadam */}
            <div className="p-7 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-purple-500/40 hover:bg-white/[0.04] transition-all space-y-4 group">
              <div className="w-14 h-14 rounded-2xl bg-purple-500/10 text-purple-400 flex items-center justify-center font-black text-xl border border-purple-500/20 group-hover:scale-105 transition-transform">
                02
              </div>
              <h3 className="text-lg font-bold text-white">Real Vazifani Bajaring</h3>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Nazariya emas — haqiqiy ma'lumotlar tahlili, hujjat auditi va kodlarni yozib, AI mentordan daqiqalar ichida batafsil taqriz oling.
              </p>
            </div>

            {/* 3-Qadam */}
            <div className="p-7 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-cyan-500/40 hover:bg-white/[0.04] transition-all space-y-4 group">
              <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center font-black text-xl border border-cyan-500/20 group-hover:scale-105 transition-transform">
                03
              </div>
              <h3 className="text-lg font-bold text-white">Ish Taklifini Oling</h3>
              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                Bajargan ishingiz HR portalida ko'rinadi va ish beruvchilar sizni to'g'ridan-to'g'ri suhbatga chaqiradilar.
              </p>
            </div>

          </div>

        </div>
      </section>

      {/* ── 6. POPULAR SIMULATIONS SHOWCASE ────────────────────────────────── */}
      <section className="py-20 md:py-28 border-b border-white/5 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5" /> Amaliy Dasturlar
              </div>
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
                Ommabop Simulyatsiyalar
              </h2>
              <p className="text-sm sm:text-base text-slate-400 max-w-2xl">
                Karyerangizni yetakchi brendlarning eng talabgir amaliy topshiriqlari bilan boshlang
              </p>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap items-center gap-2">
              {[
                { id: 'all', label: 'Barchasi' },
                { id: 'engineering', label: 'Dasturlash' },
                { id: 'finance', label: 'Moliya & Bank' },
                { id: 'analytics', label: 'Biznes Tahlil' }
              ].map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                    selectedCategory === cat.id 
                      ? 'bg-indigo-600 text-white shadow-md' 
                      : 'bg-white/[0.04] text-slate-400 hover:text-white border border-white/5'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredSims.map((sim) => (
              <div
                key={sim.id}
                onClick={() => onSelectSimulation(sim.slug)}
                className="group relative rounded-3xl bg-slate-900/40 border border-white/10 hover:border-indigo-500/50 hover:bg-slate-900/90 p-6 flex flex-col justify-between transition-all duration-300 cursor-pointer shadow-xl hover:shadow-indigo-500/10 hover:-translate-y-1.5 backdrop-blur-xl"
              >
                <div>
                  {/* Category & Hours */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="px-3 py-1 rounded-xl text-[11px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {sim.category}
                    </span>
                    <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-500" /> ~{sim.estimated_hours} soat
                    </span>
                  </div>

                  {/* Company Logo & Verified */}
                  <div className="flex items-center gap-3 mb-4">
                    <img
                      src={sim.company?.logo_url || 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=80&q=80'}
                      alt={sim.company?.name}
                      className="w-11 h-11 rounded-xl object-cover border border-white/10"
                    />
                    <div>
                      <div className="text-xs font-bold text-white">{sim.company?.name}</div>
                      <div className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Rasmiy Hamkor
                      </div>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors leading-snug mb-2">
                    {sim.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed line-clamp-2 mb-4">
                    {sim.description}
                  </p>

                  {/* Outcomes */}
                  {sim.learning_outcomes && (
                    <div className="flex flex-wrap gap-1.5 mb-6">
                      {sim.learning_outcomes.slice(0, 3).map((item, idx) => (
                        <span key={idx} className="text-[10px] px-2 py-0.5 rounded-md bg-white/[0.04] text-slate-300 border border-white/5">
                          {item}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="pt-2 border-t border-white/5">
                  <button className="w-full py-2.5 rounded-xl bg-white/[0.04] group-hover:bg-gradient-to-r group-hover:from-indigo-600 group-hover:to-purple-600 text-slate-300 group-hover:text-white font-bold text-xs transition flex items-center justify-center gap-2">
                    <span>Simulyatsiyani Boshlash</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* ── 7. VALUE FOR ALL STAKEHOLDERS (3 AUDIENCES) ────────────────────── */}
      <section className="py-20 md:py-28 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
              Aniq Qiymat
            </div>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tight">
              Barcha ishtirokchilar uchun aniq natija
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* 1. TALABALAR UCHUN */}
            <div className="rounded-3xl bg-slate-900/40 border border-indigo-500/25 p-7 flex flex-col justify-between space-y-6 shadow-2xl relative overflow-hidden group hover:border-indigo-400/60 hover:bg-slate-900/80 transition-all">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-indigo-500/15 text-indigo-400 border border-indigo-500/20">
                    <GraduationCap className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    100% Bepul
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-white">Talabalarga</h3>
                  <p className="text-xs text-slate-400 mt-1">Rezyumesiz, amaliy isbot bilan ishga kirish</p>
                </div>

                {/* UI Mockup */}
                <div className="rounded-2xl bg-black/60 border border-white/10 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-xs font-bold">UZ</div>
                      <div>
                        <div className="text-xs font-bold text-white">Bahrom R.</div>
                        <div className="text-[10px] text-slate-400">UrDU Bitiruvchisi</div>
                      </div>
                    </div>
                    <div className="p-1 rounded bg-white/10 text-indigo-300">
                      <QrCode className="w-4 h-4" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] p-2 rounded-lg bg-white/[0.03]">
                      <span className="text-slate-300 font-medium">JPMorgan Quant Tech</span>
                      <span className="text-emerald-400 font-bold">96% Tasdiqlangan</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] p-2 rounded-lg bg-white/[0.03]">
                      <span className="text-slate-300 font-medium">Kapitalbank Scoring</span>
                      <span className="text-emerald-400 font-bold">92% Tasdiqlangan</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-white/5 text-xs text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>Portfolioda 2 ta korporativ keys va QR sertifikat</span>
              </div>
            </div>

            {/* 2. ISH BERUVCHILAR UCHUN */}
            <div className="rounded-3xl bg-slate-900/40 border border-purple-500/25 p-7 flex flex-col justify-between space-y-6 shadow-2xl relative overflow-hidden group hover:border-purple-400/60 hover:bg-slate-900/80 transition-all">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-purple-500/15 text-purple-400 border border-purple-500/20">
                    <Briefcase className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    HR Portali
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-white">Kompaniyalarga (HR)</h3>
                  <p className="text-xs text-slate-400 mt-1">CV saralamasdan, tayyor kadrlarni topish</p>
                </div>

                {/* UI Mockup */}
                <div className="rounded-2xl bg-black/60 border border-white/10 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Top Nomzod</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-bold flex items-center gap-1">
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" /> 94% Match
                    </span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-white">Aziza Karimova</div>
                      <div className="text-[10px] text-purple-300">Westminster • Audit & IFRS</div>
                    </div>
                    <button className="px-2.5 py-1 rounded-lg bg-purple-600 hover:bg-purple-500 text-[10px] font-bold text-white transition flex items-center gap-1">
                      <Send className="w-2.5 h-2.5" /> Taklif
                    </button>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                    <span>Onboarding xarajati:</span>
                    <span className="text-purple-300 font-bold">70% Tejaladi</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-white/5 text-xs text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
                <span>100 ta bo'sh rezyume o'rniga — faqat amalda 85%+ olgan kadrlar</span>
              </div>
            </div>

            {/* 3. UNIVERSITETLAR UCHUN */}
            <div className="rounded-3xl bg-slate-900/40 border border-cyan-500/25 p-7 flex flex-col justify-between space-y-6 shadow-2xl relative overflow-hidden group hover:border-cyan-400/60 hover:bg-slate-900/80 transition-all">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
                    <Building2 className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    OTM Monitoringi
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-white">Universitetlarga</h3>
                  <p className="text-xs text-slate-400 mt-1">Talabalar amaliyotini raqamli monitoring qilish</p>
                </div>

                {/* UI Mockup */}
                <div className="rounded-2xl bg-black/60 border border-white/10 p-4 space-y-3">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-300 font-bold">UrDU Amaliyot Ko'rsatkichi</span>
                    <span className="text-cyan-400 font-bold">94.8%</span>
                  </div>

                  <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-cyan-400 to-indigo-500 w-[94.8%]" />
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <div className="text-[10px] text-slate-400">Talabalar: <strong className="text-white">1,420+</strong></div>
                    <span className="text-[10px] text-cyan-300 font-medium flex items-center gap-1">
                      <DownloadCloud className="w-3 h-3" /> PDF Hisobot
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-white/5 text-xs text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>Qog'ozdagi formal amaliyotlar o'rniga — 100% raqamli nazorat</span>
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* ── 8. VERIFIED CERTIFICATE SHOWCASE ──────────────────────────────── */}
      <section className="py-20 md:py-28 border-b border-white/5 relative overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900/50 to-slate-950">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            
            {/* Left Info */}
            <div className="lg:col-span-5 space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-bold uppercase tracking-wider">
                <Award className="w-3.5 h-3.5" /> Rasmiy Kafolat
              </div>
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
                HR va Kompaniyalar tomonidan tan olinadigan <span className="bg-gradient-to-r from-amber-400 to-yellow-300 bg-clip-text text-transparent">Oltin Sertifikat</span>
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Har bir topshirilgan simulyatsiya HMAC-SHA256 kriptografik imzosi va individual QR-kod bilan tasdiqlanadi. Ish beruvchilar LinkedIn yoki rezyumengizdagi QR-kodni skanerlab, haqiqiy kodingiz va baholaringizni bir soniyada ko'rishlari mumkin.
              </p>

              <div className="space-y-3 text-xs text-slate-300 text-left pt-2">
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.02] border border-white/5">
                  <QrCode className="w-5 h-5 text-amber-400 shrink-0" />
                  <span>Darhol skanerlanuvchi ommaviy verifikatsiya sahifasi</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.02] border border-white/5">
                  <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>Soxtalashtirishdan 100% himoyalangan raqamli imzo</span>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.02] border border-white/5">
                  <Building2 className="w-5 h-5 text-indigo-400 shrink-0" />
                  <span>Kapitalbank, Uzum va PwC tomonidan to'g'ridan-to'g'ri tan olinadi</span>
                </div>
              </div>

              <div className="pt-2">
                <button 
                  onClick={() => onNavigate('verify_certificate')}
                  className="px-6 py-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-bold text-xs transition flex items-center justify-center lg:justify-start gap-2 mx-auto lg:mx-0 cursor-pointer"
                >
                  <QrCode className="w-4 h-4" />
                  <span>Sertifikatni QR orqali tekshirib ko'rish</span>
                </button>
              </div>
            </div>

            {/* Right Certificate PNG Visual */}
            <div className="lg:col-span-7 relative group">
              <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-amber-500/20 via-yellow-500/20 to-orange-500/20 blur-2xl opacity-70 group-hover:opacity-100 transition-opacity" />
              <div className="relative rounded-3xl overflow-hidden border border-amber-500/40 shadow-2xl bg-slate-950 p-2">
                <img 
                  src="/assets/certificate_gold_preview.png" 
                  alt="TryJob Official Verified Gold Certificate" 
                  className="w-full h-auto rounded-2xl object-cover shadow-inner group-hover:scale-[1.01] transition-transform duration-300"
                />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── 9. NATIONAL CASE CUPS & TALENT RADAR ───────────────────────────── */}
      <section className="py-20 border-b border-white/5 bg-gradient-to-b from-slate-950 via-slate-900/30 to-slate-950">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-12">
          
          {/* Case Cup Banner Visual */}
          <div className="rounded-3xl p-2 bg-gradient-to-r from-amber-500/20 via-purple-500/20 to-indigo-500/20 border border-amber-500/30 shadow-2xl overflow-hidden group">
            <div className="rounded-2xl overflow-hidden bg-slate-950">
              <img 
                src="/assets/case_cup_banner.png" 
                alt="TryJob Milliy Case Cup 2026" 
                className="w-full h-auto object-cover group-hover:scale-[1.01] transition-transform duration-300"
              />
            </div>
          </div>

          {/* Talent Hunt Radar Preview */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center pt-6">
            <div className="lg:col-span-7 rounded-3xl p-2 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 shadow-2xl overflow-hidden group">
              <div className="rounded-2xl overflow-hidden bg-slate-950">
                <img 
                  src="/assets/talent_hunt_radar.png" 
                  alt="TryJob AI Talent Radar" 
                  className="w-full h-auto object-cover group-hover:scale-[1.01] transition-transform duration-300"
                />
              </div>
            </div>

            <div className="lg:col-span-5 space-y-5 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold uppercase tracking-wider">
                <Users className="w-3.5 h-3.5" /> HR Talent Hunt
              </div>
              <h3 className="text-2xl sm:text-3xl font-black text-white">
                Kompaniyalar Sizni Amalda Ko'rib Tanlaydi
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Rezyumedagi chiroyli so'zlar emas, balki real simulyatsiyalardagi kodingiz, analitika aniqligi va ELO reytingingiz HR Talent Radarida ko'rinadi.
              </p>
              <div>
                <button 
                  onClick={() => onNavigate('talenthunt')}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/25 transition flex items-center justify-center lg:justify-start gap-2 mx-auto lg:mx-0 cursor-pointer"
                >
                  <span>Talent Hunt Portalini Ko'rish</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── 9. FINAL CTA SECTION ────────────────────────────────────────────── */}
      <section className="py-24 relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-indigo-600/20 blur-[140px] -z-10 rounded-full" />

        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-8">
          
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/10 text-xs font-semibold text-indigo-300">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> Bepul Virtual Amaliyot
          </div>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            Karyerangizni bugunoq <br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
              amaliy tajriba bilan boshlang.
            </span>
          </h2>

          <p className="text-sm sm:text-base text-slate-300 max-w-xl mx-auto leading-relaxed">
            Hech qanday to'lov yo'q. Faqat siz, real korporativ vazifalar va sizni kutayotgan yetakchi ish beruvchilar.
          </p>

          <div className="pt-2">
            <button 
              onClick={() => onNavigate('catalog')}
              className="px-10 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:opacity-95 text-white font-bold text-base sm:text-lg shadow-2xl shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:-translate-y-0.5 transition-all inline-flex items-center gap-3 group cursor-pointer border border-indigo-400/30"
            >
              <span>Hoziroq Boshlash — Bepul</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400 pt-4">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> 100% Bepul Kirish
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-indigo-400" /> Rasmiy Sertifikat
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-purple-400" /> To'g'ridan-to'g'ri HR Aloqasi
            </span>
          </div>

        </div>
      </section>

    </div>
  );
};
