import React, { useState, useEffect } from 'react';
import { 
  Trophy, 
  Flame, 
  Calendar, 
  Users, 
  Award, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  Search, 
  Clock, 
  ShieldCheck, 
  Gift, 
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Zap,
  Target,
  Medal,
  Crown,
  Layers,
  CheckCircle,
  Briefcase,
  SlidersHorizontal,
  Star
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { CaseCup, LeaderboardEntry } from '../types';
import { getCaseCups, getLeaderboard } from '../api';

interface CaseCupsPageProps {
  onSelectSimulation?: (slug: string) => void;
}

export const CaseCupsPage: React.FC<CaseCupsPageProps> = ({ onSelectSimulation }) => {
  const [activeTab, setActiveTab] = useState<'cups' | 'leaderboard' | 'prizes'>('cups');
  const [caseCups, setCaseCups] = useState<CaseCup[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [timeFilter, setTimeFilter] = useState<'all' | 'season' | 'month'>('season');
  
  // Registration Modal state
  const [selectedCup, setSelectedCup] = useState<CaseCup | null>(null);
  const [registeredCups, setRegisteredCups] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('tryjob_registered_cups') || '[]');
    } catch {
      return [];
    }
  });
  const [regModalOpen, setRegModalOpen] = useState<boolean>(false);
  const [regSuccess, setRegSuccess] = useState<boolean>(false);
  const [teamName, setTeamName] = useState<string>('');
  const [studentRole, setStudentRole] = useState<string>('Solo / Individual');
  const [contactPhone, setContactPhone] = useState<string>('+998 90 ');
  const [telegramHandle, setTelegramHandle] = useState<string>('@');

  useEffect(() => {
    loadData();
  }, [categoryFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cups, lb] = await Promise.all([
        getCaseCups(),
        getLeaderboard(categoryFilter)
      ]);
      setCaseCups(cups);
      setLeaderboard(lb);
    } catch (e) {
      console.error('Error loading Case Cup data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterClick = (cup: CaseCup) => {
    setSelectedCup(cup);
    setRegSuccess(false);
    setRegModalOpen(true);
  };

  const handleConfirmRegistration = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCup) return;
    
    if (registeredCups.includes(selectedCup.id)) {
      setRegSuccess(true);
      return;
    }
    
    const updated = [...registeredCups, selectedCup.id];
    setRegisteredCups(updated);
    localStorage.setItem('tryjob_registered_cups', JSON.stringify(updated));

    // Save full registration info for certificate and team leaderboard
    try {
      const regDetails = JSON.parse(localStorage.getItem('tryjob_registered_details') || '{}');
      regDetails[selectedCup.id] = {
        cup_id: selectedCup.id,
        cup_title: selectedCup.title,
        team_name: teamName || 'Solo',
        student_role: studentRole,
        contact_phone: contactPhone,
        telegram_handle: telegramHandle,
        registered_at: new Date().toISOString()
      };
      localStorage.setItem('tryjob_registered_details', JSON.stringify(regDetails));
    } catch (e) {
      console.error('Error saving reg details:', e);
    }

    setRegSuccess(true);

    confetti({
      particleCount: 140,
      spread: 90,
      origin: { y: 0.6 }
    });
  };

  const filteredLeaderboard = leaderboard.filter(entry => {
    const q = searchQuery.toLowerCase();
    const matchesSearch = (
      entry.user_name.toLowerCase().includes(q) ||
      entry.university.toLowerCase().includes(q) ||
      (entry.category && entry.category.toLowerCase().includes(q))
    );
    return matchesSearch;
  });

  // Check if podium should be displayed (only when no narrow search is active and at least 3 items exist)
  const isSearchActive = searchQuery.trim().length > 0;
  const showPodium = !isSearchActive && filteredLeaderboard.length >= 3;
  const firstPlace = filteredLeaderboard[0];
  const secondPlace = filteredLeaderboard[1];
  const thirdPlace = filteredLeaderboard[2];
  const displayTableList = showPodium ? filteredLeaderboard.slice(3) : filteredLeaderboard;


  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 py-10 px-4 sm:px-6 lg:px-8 selection:bg-amber-500/30 selection:text-amber-200">
      <div className="max-w-7xl mx-auto space-y-12">
        
        {/* ── Hero Banner ── */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-amber-500/15 via-[#0E131F] to-cyan-500/15 border border-amber-500/30 p-8 sm:p-12 shadow-[0_0_50px_rgba(245,158,11,0.12)]">
          <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/4 -mb-20 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
            <div className="max-w-2xl space-y-5">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/10 border border-amber-400/30 text-amber-300 text-xs font-bold tracking-wider uppercase shadow-sm backdrop-blur-md">
                <Trophy className="w-4 h-4 text-amber-400 animate-pulse" />
                TryJob Milliy Chempionatlari 2026
              </div>
              <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-white leading-tight">
                TryJob <span className="bg-gradient-to-r from-amber-400 via-orange-400 to-yellow-300 bg-clip-text text-transparent">Case Cup</span>
              </h1>
              <p className="text-slate-300 text-base sm:text-lg leading-relaxed">
                O'zbekistonning yetakchi IT, Bank va Audit kompaniyalarining real keyslarini yeching, 
                <span className="text-amber-300 font-black"> 150,000,000 UZS</span> sovrin jamg'armasidan ulushingizni oling hamda to'g'ridan-to'g'ri <span className="text-cyan-300 font-black">Fast-Track Job Offer</span> ga ega bo'ling!
              </p>
              
              <div className="flex flex-wrap items-center gap-6 pt-2">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-300 bg-[#0B0F19]/80 px-3.5 py-1.5 rounded-xl border border-slate-800">
                  <Flame className="w-4 h-4 text-orange-400" />
                  <span>Jami sovrin: <strong className="text-amber-400 font-bold">150M+ UZS</strong></span>
                </div>
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-300 bg-[#0B0F19]/80 px-3.5 py-1.5 rounded-xl border border-slate-800">
                  <Users className="w-4 h-4 text-cyan-400" />
                  <span>Ishtirokchilar: <strong className="text-cyan-300 font-bold">1,160+ talaba</strong></span>
                </div>
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-300 bg-[#0B0F19]/80 px-3.5 py-1.5 rounded-xl border border-slate-800">
                  <Award className="w-4 h-4 text-emerald-400" />
                  <span>Fast-Track Offers: <strong className="text-emerald-300 font-bold">25+ vakansiya</strong></span>
                </div>
              </div>
            </div>

            {/* Featured Active Cup Highlight */}
            <div className="bg-[#0B0F19]/90 backdrop-blur-xl p-6 sm:p-7 rounded-3xl border border-amber-500/30 w-full lg:w-84 text-center space-y-4 shadow-2xl relative group">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-black text-[10px] tracking-wider uppercase px-3 py-1 rounded-full shadow-lg">
                🔥 Bosh Sovrinli Chempionat
              </div>
              <div className="pt-2">
                <div className="text-2xl font-black text-amber-400">Uzum Fintech Cup 2026</div>
                <div className="text-3xl font-black text-white mt-1">50,000,000 UZS</div>
              </div>
              <div className="text-xs text-slate-300 bg-[#121826] py-2 px-3.5 rounded-xl border border-slate-800 flex items-center justify-center gap-2">
                <Clock className="w-4 h-4 text-amber-400 animate-pulse" />
                <span>Ro'yxatdan o'tish: <strong>22 kun qoldi</strong></span>
              </div>
              <button
                onClick={() => {
                  const uzumCup = caseCups.find(c => (c?.slug || '').includes('uzum')) || caseCups[0];
                  if (uzumCup) handleRegisterClick(uzumCup);
                }}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-black text-sm transition-all shadow-lg shadow-amber-500/25 flex items-center justify-center gap-2 cursor-pointer transform active:scale-95"
              >
                <Zap className="w-4 h-4 fill-current" />
                Hozir Qatnashish
              </button>
            </div>
          </div>
        </div>

        {/* ── Navigation Tabs ── */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            <button
              onClick={() => setActiveTab('cups')}
              className={`px-5 py-2.5 rounded-xl font-bold text-sm sm:text-base flex items-center gap-2.5 transition duration-200 cursor-pointer ${
                activeTab === 'cups'
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <Trophy className="w-4 h-4" /> Chempionatlar ({caseCups.length})
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`px-5 py-2.5 rounded-xl font-bold text-sm sm:text-base flex items-center gap-2.5 transition duration-200 cursor-pointer ${
                activeTab === 'leaderboard'
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <TrendingUp className="w-4 h-4" /> Jonli Leaderboard (Podium)
            </button>
            <button
              onClick={() => setActiveTab('prizes')}
              className={`px-5 py-2.5 rounded-xl font-bold text-sm sm:text-base flex items-center gap-2.5 transition duration-200 cursor-pointer ${
                activeTab === 'prizes'
                  ? 'bg-purple-500/15 text-purple-400 border border-purple-500/40 shadow-[0_0_15px_rgba(168,85,247,0.2)]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
              }`}
            >
              <Gift className="w-4 h-4" /> Sovrinlar & Qoidalar
            </button>
          </div>
        </div>

        {/* ── TAB 1: Case Cups List ── */}
        {activeTab === 'cups' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {caseCups.map((cup) => {
                const isRegistered = registeredCups.includes(cup.id);
                return (
                  <div 
                    key={cup.id}
                    className="group relative bg-[#0B0F19]/90 backdrop-blur-md rounded-3xl border border-slate-800 p-6 sm:p-8 hover:border-amber-500/50 transition-all duration-300 flex flex-col justify-between shadow-xl hover:shadow-[0_0_30px_rgba(245,158,11,0.08)]"
                  >
                    <div className="space-y-6">
                      {/* Card Header */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3.5">
                          <img
                            src={cup.company_logo || 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=120&h=120&fit=crop'}
                            alt={cup.host_company}
                            className="w-13 h-13 rounded-2xl object-cover border border-slate-700/80 shadow-md group-hover:border-amber-400/60 transition"
                          />
                          <div>
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                              {cup.host_company}
                            </span>
                            <h3 className="text-xl font-black text-white group-hover:text-amber-400 transition">
                              {cup.title}
                            </h3>
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                          cup.status === 'active'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {cup.status === 'active' ? '● Jonli Faol' : 'Tez Kunda'}
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-slate-300 text-sm leading-relaxed">
                        {cup.description}
                      </p>

                      {/* Prize Pool Highlight */}
                      <div className="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent p-4 rounded-2xl border border-amber-500/20 flex items-center justify-between">
                        <div>
                          <div className="text-xs text-amber-300/80 font-bold uppercase tracking-wider">Sovrin Fondi</div>
                          <div className="text-2xl font-black text-amber-400">{cup.prize_pool}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-slate-400 font-semibold">Topshiriqlar</div>
                          <div className="text-lg font-bold text-white">{cup.tasks_count} ta bosqich</div>
                        </div>
                      </div>

                      {/* Stages Roadmap */}
                      <div className="space-y-2.5">
                        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-cyan-400">
                            <Target className="w-3.5 h-3.5" /> Bosqichlar rejasi:
                          </span>
                          <span className="text-[11px] text-slate-500 font-normal">Muddat: {cup.deadline}</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {cup.stages.map((st, sIdx) => (
                            <div key={st.stage} className="bg-[#070A12]/80 p-3 rounded-xl border border-slate-800/80 flex items-start gap-2.5 hover:border-slate-700 transition">
                              <span className={`w-5 h-5 rounded-full font-bold flex items-center justify-center shrink-0 text-[10px] ${
                                sIdx === 0 
                                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' 
                                  : 'bg-slate-800 text-slate-400'
                              }`}>
                                {st.stage}
                              </span>
                              <div className="flex-1">
                                <div className="font-semibold text-slate-200 line-clamp-1">{st.title}</div>
                                <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                                  <Calendar className="w-3 h-3 text-slate-500" />
                                  {st.date}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2 pt-1">
                        {cup.tags.map(tag => (
                          <span key={tag} className="px-2.5 py-1 rounded-lg bg-[#121826] text-slate-300 text-xs font-medium border border-slate-800">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Card Footer */}
                    <div className="pt-6 mt-6 border-t border-slate-800/80 flex items-center justify-between gap-4">
                      <div className="text-xs text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Users className="w-3.5 h-3.5 text-cyan-400" />
                          <span className="font-bold text-slate-200">{cup.participants_count}</span> ishtirokchi
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">Boshlanish: {cup.start_date}</div>
                      </div>

                      {isRegistered ? (
                        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                          <CheckCircle2 className="w-4 h-4" /> Ro'yxatdan o'tgansiz
                        </div>
                      ) : (
                        <button
                          onClick={() => handleRegisterClick(cup)}
                          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-black text-xs sm:text-sm transition-all shadow-lg shadow-amber-500/20 flex items-center gap-2 cursor-pointer transform active:scale-95"
                        >
                          <Trophy className="w-4 h-4" /> Chempionatga Yozilish
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── TAB 2: Live Leaderboard with Olympic Podium ── */}
        {activeTab === 'leaderboard' && (
          <div className="space-y-10">
            {/* Filter & Search Bar */}
            <div className="flex flex-col lg:flex-row items-center justify-between gap-4 bg-[#0B0F19]/90 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
              <div className="relative w-full lg:w-96">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Talaba ismi yoki OTM bo'yicha qidirish..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#070A12] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              <div className="flex items-center gap-2 w-full lg:w-auto overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
                {['all', 'Backend', 'Frontend', 'Moliya', 'Security', 'Huquq'].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap cursor-pointer ${
                      categoryFilter === cat
                        ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                        : 'bg-slate-900 text-slate-300 hover:bg-slate-800 border border-slate-800'
                    }`}
                  >
                    {cat === 'all' ? 'Barcha Yo\'nalishlar' : cat}
                  </button>
                ))}
              </div>
            </div>

            {/* ── 1-2-3 Oltin, Kumush, Bronza Podium ── */}
            {showPodium && (
              <div className="space-y-4">
                <div className="text-center space-y-1">
                  <div className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-400 uppercase tracking-widest">
                    <Crown className="w-4 h-4" /> Chempionat PesHQadamlari
                  </div>
                  <h3 className="text-2xl font-black text-white">Rasmiy G'oliblar Podiumi</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 items-end max-w-5xl mx-auto">
                  
                  {/* 🥈 2-O'RIN: Kumush (Silver) */}
                  {secondPlace && (
                    <div className="order-2 md:order-1 relative rounded-3xl bg-gradient-to-b from-slate-800/80 to-[#0B0F19] border border-slate-400/40 p-6 flex flex-col items-center text-center space-y-4 shadow-[0_0_30px_rgba(148,163,184,0.15)] hover:border-slate-300 transition duration-300">
                      <div className="absolute -top-4 px-3.5 py-1 rounded-full bg-slate-800 border border-slate-500 text-slate-200 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 shadow-lg">
                        <Medal className="w-4 h-4 text-slate-300" /> 2-O'RIN &bull; KUMUSH
                      </div>

                      <div className="relative pt-2">
                        <img
                          src={secondPlace.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop'}
                          alt={secondPlace.user_name}
                          className="w-20 h-20 rounded-2xl object-cover border-2 border-slate-300 shadow-xl"
                        />
                        <span className="absolute -bottom-2 -right-2 w-7 h-7 rounded-full bg-slate-300 text-slate-950 font-black text-xs flex items-center justify-center shadow">
                          #2
                        </span>
                      </div>

                      <div>
                        <h4 className="text-lg font-black text-white flex items-center justify-center gap-1.5">
                          {secondPlace.user_name}
                          {secondPlace.is_verified_talent && (
                            <ShieldCheck className="w-4 h-4 text-cyan-400" />
                          )}
                        </h4>
                        <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{secondPlace.university}</p>
                      </div>

                      <div className="w-full bg-[#070A12] p-3 rounded-2xl border border-slate-800 flex items-center justify-around">
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase font-bold">O'rtacha Ball</div>
                          <div className="text-xl font-black text-slate-200">{secondPlace.score}</div>
                        </div>
                        <div className="w-px h-8 bg-slate-800" />
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase font-bold">Keyslar</div>
                          <div className="text-xl font-black text-white">{secondPlace.completed_simulations} ta</div>
                        </div>
                      </div>

                      <div className="flex flex-wrap justify-center gap-1.5">
                        {(secondPlace.badges || []).map(b => (
                          <span key={b} className="px-2.5 py-0.5 rounded-md bg-slate-800/80 text-[11px] font-semibold text-slate-300 border border-slate-700/50">
                            {b}
                          </span>
                        ))}
                      </div>

                      <div className="w-full pt-2">
                        <div className="w-full py-2 bg-slate-800/60 rounded-xl border border-slate-700 text-xs font-bold text-slate-300">
                          🥈 15,000,000 UZS Mukofot
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 🥇 1-O'RIN: Oltin (Gold) - Elevated Center */}
                  {firstPlace && (
                    <div className="order-1 md:order-2 relative rounded-3xl bg-gradient-to-b from-amber-500/20 via-[#0D121F] to-[#0B0F19] border-2 border-amber-400/80 p-7 flex flex-col items-center text-center space-y-4 shadow-[0_0_45px_rgba(245,158,11,0.25)] hover:border-amber-300 transition duration-300 transform md:-translate-y-4">
                      <div className="absolute -top-5 px-4 py-1.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 shadow-xl animate-bounce">
                        <Crown className="w-4 h-4 text-slate-950 fill-current" /> 1-O'RIN &bull; OLTIN CHEMPION
                      </div>

                      <div className="relative pt-2">
                        <div className="absolute -inset-1 bg-amber-400 rounded-2xl blur-md opacity-40 animate-pulse" />
                        <img
                          src={firstPlace.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop'}
                          alt={firstPlace.user_name}
                          className="relative w-24 h-24 rounded-2xl object-cover border-2 border-amber-400 shadow-2xl"
                        />
                        <span className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-500 text-slate-950 font-black text-sm flex items-center justify-center shadow-lg border border-amber-200">
                          #1
                        </span>
                      </div>

                      <div>
                        <h4 className="text-xl font-black text-white flex items-center justify-center gap-1.5">
                          {firstPlace.user_name}
                          <ShieldCheck className="w-5 h-5 text-cyan-400" />
                        </h4>
                        <p className="text-xs text-amber-300/90 font-semibold line-clamp-1 mt-0.5">{firstPlace.university}</p>
                      </div>

                      <div className="w-full bg-[#070A12] p-3.5 rounded-2xl border border-amber-500/30 flex items-center justify-around shadow-inner">
                        <div>
                          <div className="text-[10px] text-amber-300/80 uppercase font-bold">O'rtacha Ball</div>
                          <div className="text-2xl font-black text-amber-400">{firstPlace.score}</div>
                        </div>
                        <div className="w-px h-8 bg-slate-800" />
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase font-bold">Keyslar</div>
                          <div className="text-2xl font-black text-white">{firstPlace.completed_simulations} ta</div>
                        </div>
                      </div>

                      <div className="flex flex-wrap justify-center gap-1.5">
                        {(firstPlace.badges || []).map(b => (
                          <span key={b} className="px-2.5 py-0.5 rounded-md bg-amber-500/15 text-[11px] font-bold text-amber-300 border border-amber-500/30">
                            {b}
                          </span>
                        ))}
                      </div>

                      <div className="w-full pt-2">
                        <div className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl text-xs font-black text-slate-950 shadow-md">
                          🥇 30,000,000 UZS + Direct Job Offer
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 🥉 3-O'RIN: Bronza (Bronze) */}
                  {thirdPlace && (
                    <div className="order-3 relative rounded-3xl bg-gradient-to-b from-amber-900/30 to-[#0B0F19] border border-amber-700/50 p-6 flex flex-col items-center text-center space-y-4 shadow-[0_0_30px_rgba(180,83,9,0.15)] hover:border-amber-600 transition duration-300">
                      <div className="absolute -top-4 px-3.5 py-1 rounded-full bg-slate-800 border border-amber-700 text-amber-300 text-xs font-black uppercase tracking-wider flex items-center gap-1.5 shadow-lg">
                        <Medal className="w-4 h-4 text-amber-600" /> 3-O'RIN &bull; BRONZA
                      </div>

                      <div className="relative pt-2">
                        <img
                          src={thirdPlace.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop'}
                          alt={thirdPlace.user_name}
                          className="w-20 h-20 rounded-2xl object-cover border-2 border-amber-700 shadow-xl"
                        />
                        <span className="absolute -bottom-2 -right-2 w-7 h-7 rounded-full bg-amber-700 text-slate-100 font-black text-xs flex items-center justify-center shadow">
                          #3
                        </span>
                      </div>

                      <div>
                        <h4 className="text-lg font-black text-white flex items-center justify-center gap-1.5">
                          {thirdPlace.user_name}
                          {thirdPlace.is_verified_talent && (
                            <ShieldCheck className="w-4 h-4 text-cyan-400" />
                          )}
                        </h4>
                        <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{thirdPlace.university}</p>
                      </div>

                      <div className="w-full bg-[#070A12] p-3 rounded-2xl border border-slate-800 flex items-center justify-around">
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase font-bold">O'rtacha Ball</div>
                          <div className="text-xl font-black text-amber-600">{thirdPlace.score}</div>
                        </div>
                        <div className="w-px h-8 bg-slate-800" />
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase font-bold">Keyslar</div>
                          <div className="text-xl font-black text-white">{thirdPlace.completed_simulations} ta</div>
                        </div>
                      </div>

                      <div className="flex flex-wrap justify-center gap-1.5">
                        {(thirdPlace.badges || []).map(b => (
                          <span key={b} className="px-2.5 py-0.5 rounded-md bg-slate-800/80 text-[11px] font-semibold text-slate-300 border border-slate-700/50">
                            {b}
                          </span>
                        ))}
                      </div>

                      <div className="w-full pt-2">
                        <div className="w-full py-2 bg-slate-800/60 rounded-xl border border-slate-700 text-xs font-bold text-amber-200">
                          🥉 10,000,000 UZS Mukofot
                        </div>
                      </div>
                    </div>
                  )}

                </div>
              </div>
            )}

            {/* Rest of Leaderboard Table */}
            <div className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 overflow-hidden shadow-xl">
              <div className="p-5 border-b border-slate-800 flex items-center justify-between">
                <div className="font-black text-white flex items-center gap-2 text-sm sm:text-base">
                  <SlidersHorizontal className="w-4 h-4 text-cyan-400" />
                  {showPodium ? "Ishtirokchilarning To'liq Reyting Jadvali (4-O'rindan boshlab)" : "Reyting Natijalari"}
                </div>
                <span className="text-xs text-slate-400 bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
                  {displayTableList.length} ta nomzod
                </span>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[#070A12] text-slate-400 font-bold uppercase text-xs tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-4 px-6">O'rin</th>
                      <th className="py-4 px-6">Talaba & OTM</th>
                      <th className="py-4 px-6">Yo'nalish</th>
                      <th className="py-4 px-6 text-center">Bajarilgan</th>
                      <th className="py-4 px-6 text-center">O'rtacha Ball</th>
                      <th className="py-4 px-6">Yutuqlar & Badjlar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 text-slate-300">
                    {displayTableList.map((entry) => (
                      <tr key={entry.rank} className="hover:bg-slate-800/30 transition">
                        <td className="py-4 px-6 font-black text-base text-slate-200">
                          #{entry.rank}
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <img
                              src={entry.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=60&h=60&fit=crop'}
                              alt={entry.user_name}
                              className="w-10 h-10 rounded-xl object-cover border border-slate-700"
                            />
                            <div>
                              <div className="font-bold text-white flex items-center gap-1.5">
                                {entry.user_name}
                                {entry.is_verified_talent && (
                                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                                )}
                              </div>
                              <div className="text-xs text-slate-400">{entry.university}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-xs text-slate-300">
                          {entry.category || 'Dasturiy Injiniring'}
                        </td>
                        <td className="py-4 px-6 text-center font-bold text-white">
                          {entry.completed_simulations} ta keys
                        </td>
                        <td className="py-4 px-6 text-center font-black text-cyan-400 text-base">
                          {entry.score}
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex flex-wrap gap-1.5">
                            {(entry.badges || []).map(b => (
                              <span key={b} className="px-2 py-0.5 rounded-md bg-[#121826] text-[10px] font-semibold text-slate-300 border border-slate-800">
                                {b}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 3: Prizes & Rules ── */}
        {activeTab === 'prizes' && (
          <div className="space-y-8">
            {/* Visual Banner PNG */}
            <div className="rounded-3xl overflow-hidden border border-amber-500/30 shadow-2xl group">
              <img 
                src="/assets/case_cup_banner.png" 
                alt="Case Cup Chempionat Sovrinlari" 
                className="w-full h-auto object-cover group-hover:scale-[1.01] transition-transform duration-300"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-gradient-to-br from-amber-500/10 via-[#0B0F19] to-slate-900 p-8 rounded-3xl border border-amber-500/30 space-y-4 shadow-xl">
                <div className="w-12 h-12 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-black text-2xl">
                  1
                </div>
                <h3 className="text-xl font-black text-white">Pul Mukofotlari Jamg'armasi</h3>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Har bir chempionat g'oliblari 1-3 o'rinlar bo'yicha to'g'ridan-to'g'ri bank kartalariga naqd pul mukofotlarini qabul qilishadi.
                </p>
                <div className="text-amber-400 font-black text-2xl">150,000,000 UZS</div>
              </div>

              <div className="bg-gradient-to-br from-cyan-500/10 via-[#0B0F19] to-slate-900 p-8 rounded-3xl border border-cyan-500/30 space-y-4 shadow-xl">
                <div className="w-12 h-12 rounded-2xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-black text-2xl">
                  2
                </div>
                <h3 className="text-xl font-black text-white">Fast-Track Job Offer</h3>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Eng yuqori natija ko'rsatgan top 10 ishtirokchi homiy kompaniyalar (Uzum, Payme, PwC, Click) boshqaruv jamoasi bilan suhbatdan o'tib, to'g'ridan-to'g'ri ishga olinadi.
                </p>
                <div className="text-cyan-400 font-black text-2xl">25+ Ish O'rni</div>
              </div>

              <div className="bg-gradient-to-br from-purple-500/10 via-[#0B0F19] to-slate-900 p-8 rounded-3xl border border-purple-500/30 space-y-4 shadow-xl">
                <div className="w-12 h-12 rounded-2xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400 font-black text-2xl">
                  3
                </div>
                <h3 className="text-xl font-black text-white">HMAC Imzoli Verifikatsiya</h3>
                <p className="text-slate-300 text-sm leading-relaxed">
                  Barcha ishtirokchilar jahon standartlaridagi kriptografik himoyalangan Case Cup sertifikatiga ega bo'ladilar va LinkedIn profiliga qo'shishlari mumkin.
                </p>
                <div className="text-purple-400 font-black text-2xl">100% Rasmiy</div>
              </div>
            </div>

            {/* Rules Container */}
            <div className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-8 space-y-6 shadow-xl">
              <h3 className="text-2xl font-black text-white flex items-center gap-2">
                <ShieldCheck className="w-6 h-6 text-emerald-400" /> Chempionatning Rasmiy Qoidalari va Baholash Tartibi
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-slate-300">
                <div className="space-y-4">
                  <div className="flex items-start gap-3 bg-[#070A12] p-4 rounded-2xl border border-slate-800">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Avtonom AI Baholash:</strong> Kod sintaksisi, xavfsizligi, algoritm samaradorligi va arxitekturasi AI tekshiruv moduli tomonidan qat'iy rubrika bo'yicha baholanadi.</span>
                  </div>
                  <div className="flex items-start gap-3 bg-[#070A12] p-4 rounded-2xl border border-slate-800">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Haqiqiy Mentorlar Audit:</strong> Yakuniy bosqichda kompaniyalarning yetakchi Tech Lead va Moliya direktorlari eng yaxshi 5 ta yechimni jonli ko'rib chiqadi.</span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start gap-3 bg-[#070A12] p-4 rounded-2xl border border-slate-800">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Antiplagiat Tizimi:</strong> Boshqa talabalarning yechimlarini nusxalash yoki tayyor online kodlardan ruxsatsiz foydalanish holatlari aniqlanganda profil chetlatiladi.</span>
                  </div>
                  <div className="flex items-start gap-3 bg-[#070A12] p-4 rounded-2xl border border-slate-800">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <span><strong>Talabalar & Bitiruvchilar:</strong> O'zbekiston va xorijiy OTMlarning barcha bakalavr va magistr talabalari ishtirok etishi mumkin (yosh chegarasi 18-28).</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Registration Modal ── */}
        {regModalOpen && selectedCup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
            <div className="bg-[#0B0F19] border border-slate-800 rounded-3xl max-w-lg w-full p-6 sm:p-8 space-y-6 shadow-2xl relative">
              
              {regSuccess ? (
                <div className="text-center space-y-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mx-auto text-3xl shadow-lg shadow-emerald-500/20">
                    🎉
                  </div>
                  <h3 className="text-2xl font-black text-white">Tabriklaymiz, Ro'yxatdan O'tdingiz!</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Siz <strong className="text-amber-400">{selectedCup.title}</strong> chempionatiga muvaffaqiyatli qatnashuvchi sifatida qabul qilindingiz.
                  </p>
                  <div className="p-4 bg-[#070A12] rounded-2xl border border-slate-800 text-xs text-left space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Boshlanish sanasi:</span>
                      <span className="font-bold text-slate-200">{selectedCup.start_date}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Ishtirok turi:</span>
                      <span className="font-bold text-cyan-400">{studentRole}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Sovrin fondi:</span>
                      <span className="font-bold text-amber-400">{selectedCup.prize_pool}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setRegModalOpen(false)}
                    className="w-full py-3.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-sm transition cursor-pointer shadow-lg shadow-cyan-500/25"
                  >
                    Tushunarli, Rahmat!
                  </button>
                </div>
              ) : (
                <form onSubmit={handleConfirmRegistration} className="space-y-5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Chempionatga qabul</span>
                      <h3 className="text-xl font-black text-white">{selectedCup.title}</h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setRegModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold p-1 cursor-pointer"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="p-3.5 bg-[#070A12] rounded-2xl border border-slate-800/80 text-xs text-slate-300 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Tashkilotchi:</span>
                      <strong className="text-white">{selectedCup.host_company}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Sovrin:</span>
                      <strong className="text-amber-400">{selectedCup.prize_pool}</strong>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">Ishtirok formati</label>
                      <select
                        value={studentRole}
                        onChange={(e) => setStudentRole(e.target.value)}
                        className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 cursor-pointer"
                      >
                        <option value="Solo / Individual">Yakkaxon (Solo Developer / Analyst)</option>
                        <option value="Jamoaviy (2-3 kishi)">Jamoaviy qatnashish (Team)</option>
                      </select>
                    </div>

                    {studentRole.includes('Jamoaviy') && (
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">Jamoa nomi</label>
                        <input
                          type="text"
                          required
                          placeholder="Masalan: Tashkent Innovators"
                          value={teamName}
                          onChange={(e) => setTeamName(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">Aloqa telefoni</label>
                        <input
                          type="text"
                          value={contactPhone}
                          onChange={(e) => setContactPhone(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">Telegram username</label>
                        <input
                          type="text"
                          value={telegramHandle}
                          onChange={(e) => setTelegramHandle(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    </div>

                    <div className="text-xs text-slate-400 bg-[#070A12] p-3 rounded-xl border border-slate-800">
                      Chempionatda qatnashish <strong>100% bepul</strong>. Topshiriqlar belgilangan muddatda ochiladi va profilingizga email xabarnoma yuboriladi.
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setRegModalOpen(false)}
                      className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs cursor-pointer transition"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      className="flex-1 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-black text-xs transition shadow-lg shadow-amber-500/25 cursor-pointer"
                    >
                      Ishtirokni Tasdiqlash
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
