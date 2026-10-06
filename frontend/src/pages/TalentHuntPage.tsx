import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Briefcase, 
  Building2, 
  Star, 
  CheckCircle2, 
  Send, 
  Sparkles, 
  Award, 
  GraduationCap, 
  Clock, 
  Mail, 
  Phone, 
  MapPin, 
  ShieldCheck, 
  Filter, 
  Crown,
  TrendingUp,
  FileCheck,
  Zap,
  DollarSign,
  Gift,
  ExternalLink,
  ChevronRight,
  SlidersHorizontal,
  X,
  FileText,
  BadgeCheck,
  Laptop
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { CandidateProfile, TalentOffer } from '../types';
import { getTalentCandidates, sendTalentOffer, getSentOffers, upgradeVip } from '../api';

export const TalentHuntPage: React.FC = () => {
  const [candidates, setCandidates] = useState<CandidateProfile[]>([]);
  const [sentOffers, setSentOffers] = useState<TalentOffer[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'talents' | 'sent_offers'>('talents');

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSkill, setSelectedSkill] = useState<string>('all');
  const [selectedUni, setSelectedUni] = useState<string>('all');
  const [minScore, setMinScore] = useState<number>(85);
  const [vipOnly, setVipOnly] = useState<boolean>(false);
  const [openToWorkOnly, setOpenToWorkOnly] = useState<boolean>(false);

  // Direct Offer Modal
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateProfile | null>(null);
  const [offerModalOpen, setOfferModalOpen] = useState<boolean>(false);
  const [offerSentSuccess, setOfferSentSuccess] = useState<boolean>(false);
  const [companyName, setCompanyName] = useState<string>('Uzum Tech & Fintech Group');
  const [position, setPosition] = useState<string>('Junior / Middle Software Engineer');
  const [jobType, setJobType] = useState<string>('Full-time (Gibrid)');
  const [salaryOffer, setSalaryOffer] = useState<string>('15,000,000 - 22,000,000 UZS');
  const [selectedPerks, setSelectedPerks] = useState<string[]>([
    'Tibbiy sug\'urta',
    'MacBook Pro M3',
    'Masofaviy ishlash imkoniyati'
  ]);
  const [offerMessage, setOfferMessage] = useState<string>(
    'Salom! TryJob platformasidagi bajargan muhandislik ishlaringiz va yuqori ballingiz bizga juda ma\'qul keldi. Jamoamizga fast-track asosida taklif qilmoqchimiz.'
  );

  // Candidate Portfolio Detail Modal
  const [detailCandidate, setDetailCandidate] = useState<CandidateProfile | null>(null);

  // VIP alert feedback
  const [notification, setNotification] = useState<string | null>(null);

  const perksList = [
    'Tibbiy sug\'urta',
    'MacBook Pro M3',
    'Masofaviy ishlash imkoniyati',
    'Bepul tushlik & kofe',
    'Yillik bonus (13-oylik)',
    'Fitnes & sport kompensatsiyasi',
    'Xalqaro sertifikatlar to\'lovi'
  ];

  useEffect(() => {
    loadCandidates();
    setSentOffers(getSentOffers());
  }, [selectedSkill, selectedUni, minScore, vipOnly]);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const data = await getTalentCandidates({
        skill: selectedSkill === 'all' ? undefined : selectedSkill,
        university: selectedUni === 'all' ? undefined : selectedUni,
        minScore: minScore > 0 ? minScore : undefined,
        vipOnly
      });
      setCandidates(data);
    } catch (e) {
      console.error('Error loading candidates:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenOfferModal = (candidate: CandidateProfile) => {
    setSelectedCandidate(candidate);
    setPosition(candidate.preferred_roles[0] || 'Dasturiy Ta\'minot Mutaxassisi');
    setOfferSentSuccess(false);
    setOfferModalOpen(true);
  };

  const togglePerk = (perk: string) => {
    if (selectedPerks.includes(perk)) {
      setSelectedPerks(selectedPerks.filter(p => p !== perk));
    } else {
      setSelectedPerks([...selectedPerks, perk]);
    }
  };

  const handleSendOfferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;

    try {
      const created = await sendTalentOffer({
        candidate_id: selectedCandidate.id,
        candidate_name: selectedCandidate.name,
        company_name: companyName,
        position,
        salary_offer: salaryOffer,
        message: `${offerMessage}\n\nImtiyozlar: ${selectedPerks.join(', ')}`
      });

      setSentOffers(prev => [created, ...prev]);
      setOfferSentSuccess(true);
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 }
      });
    } catch (e) {
      console.error('Error sending offer:', e);
    }
  };

  const handleUpgradeVipClick = async (cand: CandidateProfile) => {
    const res = await upgradeVip(cand.id);
    setNotification(res.message);
    setCandidates(prev =>
      prev.map(c => c.id === cand.id ? { ...c, is_vip: true } : c)
    );
    setTimeout(() => setNotification(null), 4000);
  };

  const filteredCandidates = candidates.filter(c => {
    const q = searchQuery.toLowerCase();
    const matchesQuery = (
      c.name.toLowerCase().includes(q) ||
      c.university.toLowerCase().includes(q) ||
      c.skills.some(s => s.toLowerCase().includes(q)) ||
      c.preferred_roles.some(r => r.toLowerCase().includes(q))
    );
    const matchesOpen = !openToWorkOnly || c.is_open_to_work;
    return matchesQuery && matchesOpen;
  });

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 py-10 px-4 sm:px-6 lg:px-8 selection:bg-cyan-500/30 selection:text-cyan-200">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Toast Notification */}
        {notification && (
          <div className="fixed top-24 right-6 z-50 bg-emerald-600 text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-bounce">
            <Sparkles className="w-5 h-5 text-amber-300" />
            <span className="text-sm font-bold">{notification}</span>
          </div>
        )}

        {/* ── Header Banner ── */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-950/60 via-[#0D121F] to-cyan-950/50 border border-cyan-500/30 p-8 sm:p-10 shadow-[0_0_50px_rgba(6,182,212,0.1)]">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-16 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-3 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/15 border border-cyan-400/30 text-cyan-300 text-xs font-bold uppercase tracking-wider backdrop-blur-md">
                <Building2 className="w-3.5 h-3.5 text-cyan-400" />
                HR & Rekruting Korporativ Portali
              </div>
              <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
                TryJob <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-300 bg-clip-text text-transparent">Talent Hunt</span>
              </h1>
              <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
                Rezyumedagi quruq so'zlarga emas, talabaning <strong>haqiqiy yozgan kodi, moliya modellari va AI bergan ob'ektiv ballariga</strong> qarab eng kuchli kadrlarni tanlang va to'g'ridan-to'g'ri <span className="text-emerald-400 font-bold">Direct Job Offer</span> yuboring.
              </p>
            </div>

            {/* Quick HR Stats */}
            <div className="grid grid-cols-2 gap-3.5 w-full md:w-auto shrink-0">
              <div className="bg-[#0B0F19]/90 p-4 rounded-2xl border border-slate-800 text-center shadow-lg">
                <div className="text-xs text-slate-400 font-bold uppercase">Sinovdan O'tganlar</div>
                <div className="text-2xl font-black text-cyan-400 mt-0.5">1,160+</div>
                <div className="text-[10px] text-slate-500">Verified talabalar</div>
              </div>
              <div className="bg-[#0B0F19]/90 p-4 rounded-2xl border border-slate-800 text-center shadow-lg">
                <div className="text-xs text-slate-400 font-bold uppercase">Top 5% Iqtidorlar</div>
                <div className="text-2xl font-black text-amber-400 mt-0.5">96+ Ball</div>
                <div className="text-[10px] text-slate-500">Avtonom tekshirilgan</div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Navigation Tabs ── */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('talents')}
              className={`px-4.5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 transition cursor-pointer ${
                activeTab === 'talents'
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/50'
              }`}
            >
              <Users className="w-4 h-4" /> Barcha Saralangan Iqtidorlar ({filteredCandidates.length})
            </button>
            <button
              onClick={() => setActiveTab('sent_offers')}
              className={`px-4.5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 transition cursor-pointer ${
                activeTab === 'sent_offers'
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900/50'
              }`}
            >
              <Send className="w-4 h-4" /> Yuborilgan Takliflar ({sentOffers.length})
            </button>
          </div>
        </div>

        {/* ── TAB 1: Candidates Search & Grid ── */}
        {activeTab === 'talents' && (
          <div className="space-y-6">
            
            {/* Filter Bar */}
            <div className="bg-[#0B0F19]/90 rounded-2xl border border-slate-800 p-5 space-y-4 shadow-xl backdrop-blur-md">
              <div className="flex flex-col lg:flex-row items-center gap-4">
                <div className="relative flex-1 w-full">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Nomzod ismi, ko'nikmasi (Python, React, FastAPI, Audit) yoki OTM..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#070A12] border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                  <select
                    value={selectedSkill}
                    onChange={(e) => setSelectedSkill(e.target.value)}
                    className="bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    <option value="all">Barcha Ko'nikmalar</option>
                    <option value="Python">Python / Backend</option>
                    <option value="React">React / Frontend</option>
                    <option value="FastAPI">FastAPI / HighLoad</option>
                    <option value="IFRS">IFRS / Moliya Audit</option>
                    <option value="SQL">SQL / Data Analysis</option>
                    <option value="Korporativ">Korporativ Huquq</option>
                  </select>

                  <select
                    value={selectedUni}
                    onChange={(e) => setSelectedUni(e.target.value)}
                    className="bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    <option value="all">Barcha OTMlar</option>
                    <option value="UrDU">UrDU (Urganch davlat universiteti)</option>
                    <option value="Westminster">Westminster (WIUT)</option>
                    <option value="Inha">Inha (IUT)</option>
                    <option value="TDIU">TDIU</option>
                    <option value="TDYU">TDYU</option>
                  </select>

                  <select
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    <option value={0}>Barcha Ballar</option>
                    <option value={85}>85%+ Ball (Saralangan)</option>
                    <option value={90}>90%+ Ball (A'lo)</option>
                    <option value={95}>95%+ Ball (Top Talent)</option>
                    <option value={98}>98%+ Ball (Elite %1)</option>
                  </select>

                  <label className="flex items-center gap-2 text-xs font-bold text-amber-300 cursor-pointer bg-[#070A12] border border-slate-800 px-3 py-2.5 rounded-xl hover:border-slate-700 transition">
                    <input
                      type="checkbox"
                      checked={vipOnly}
                      onChange={(e) => setVipOnly(e.target.checked)}
                      className="rounded accent-amber-500 cursor-pointer"
                    />
                    <Crown className="w-3.5 h-3.5 text-amber-400" />
                    Faqat VIP
                  </label>

                  <label className="flex items-center gap-2 text-xs font-bold text-emerald-300 cursor-pointer bg-[#070A12] border border-slate-800 px-3 py-2.5 rounded-xl hover:border-slate-700 transition">
                    <input
                      type="checkbox"
                      checked={openToWorkOnly}
                      onChange={(e) => setOpenToWorkOnly(e.target.checked)}
                      className="rounded accent-emerald-500 cursor-pointer"
                    />
                    <Zap className="w-3.5 h-3.5 text-emerald-400" />
                    Open to Work
                  </label>
                </div>
              </div>
            </div>

            {/* AI Talent Radar Visual Preview Graphic */}
            <div className="rounded-3xl overflow-hidden border border-cyan-500/25 shadow-2xl group">
              <img 
                src="/assets/talent_hunt_radar.png" 
                alt="AI Talent Radar Dashboard" 
                className="w-full h-auto object-cover group-hover:scale-[1.01] transition-transform duration-300"
              />
            </div>

            {/* Candidates Cards Grid */}
            {loading ? (
              <div className="py-20 text-center text-slate-500">Iqtidorlar bazasi yuklanmoqda...</div>
            ) : filteredCandidates.length === 0 ? (
              <div className="py-16 text-center bg-[#0B0F19]/50 rounded-3xl border border-slate-800 space-y-3">
                <Users className="w-10 h-10 text-slate-600 mx-auto" />
                <div className="text-lg font-bold text-slate-400">Filtr bo'yicha nomzod topilmadi</div>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedSkill('all');
                    setSelectedUni('all');
                    setMinScore(0);
                    setVipOnly(false);
                    setOpenToWorkOnly(false);
                  }}
                  className="text-cyan-400 text-xs font-bold underline cursor-pointer"
                >
                  Filtrlarni tozalash
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredCandidates.map((candidate) => (
                  <div
                    key={candidate.id}
                    className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-6 sm:p-7 hover:border-cyan-500/40 transition-all duration-300 flex flex-col justify-between space-y-6 shadow-xl relative group"
                  >
                    {candidate.is_vip && (
                      <div className="absolute top-4 right-4 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/40 px-3 py-1 rounded-full flex items-center gap-1.5 text-amber-300 text-[11px] font-black uppercase shadow-sm">
                        <Crown className="w-3.5 h-3.5 text-amber-400" />
                        VIP Talant
                      </div>
                    )}

                    {/* Candidate Top info */}
                    <div className="flex items-start gap-4">
                      <div className="relative">
                        <img
                          src={candidate.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop'}
                          alt={candidate.name}
                          className="w-16 h-16 rounded-2xl object-cover border-2 border-slate-700 shadow-md group-hover:border-cyan-400/50 transition"
                        />
                        {candidate.is_open_to_work && (
                          <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 border-2 border-slate-900 rounded-full" title="Ishga tayyor" />
                        )}
                      </div>

                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-black text-white group-hover:text-cyan-300 transition">{candidate.name}</h3>
                          {candidate.avg_score >= 85 && (
                            <span title="TryJob Verified Talent" className="flex items-center text-cyan-400">
                              <BadgeCheck className="w-4 h-4" />
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-1.5">
                          <GraduationCap className="w-3.5 h-3.5 text-slate-500" />
                          {candidate.university} ({candidate.graduation_year}-yil bitiruvchisi)
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-2">
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5 text-slate-500" />
                            {candidate.location}
                          </span>
                          <span>&bull;</span>
                          <span>GPA: <strong className="text-white">{candidate.gpa}</strong></span>
                        </div>
                      </div>
                    </div>

                    {/* Score and Stats ribbon */}
                    <div className="grid grid-cols-3 gap-2 bg-[#070A12] p-3 rounded-2xl border border-slate-800 text-center">
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase font-bold">TryJob Bahosi</div>
                        <div className="text-xl font-black text-cyan-400">{candidate.avg_score}</div>
                      </div>
                      <div className="border-x border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase font-bold">Yechilgan Keyslar</div>
                        <div className="text-xl font-black text-white">{candidate.completed_simulations_count} ta</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase font-bold">Holati</div>
                        <div className="text-xs font-bold text-emerald-400 mt-1 flex items-center justify-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                          Open to Work
                        </div>
                      </div>
                    </div>

                    {/* Bio */}
                    <p className="text-xs text-slate-300 leading-relaxed bg-[#070A12]/60 p-3 rounded-xl border border-slate-800/80">
                      {candidate.bio}
                    </p>

                    {/* Verified Projects Portfolio */}
                    <div className="space-y-2">
                      <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                        Tasdiqlangan Loyihalar Portfolio:
                      </div>
                      <div className="space-y-1.5">
                        {candidate.top_projects.map((proj, idx) => (
                          <div key={idx} className="bg-[#070A12] px-3.5 py-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                            <div>
                              <div className="font-semibold text-slate-200">{proj.title}</div>
                              <div className="text-[10px] text-slate-500">{proj.company}</div>
                            </div>
                            <span className="px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-300 font-bold border border-cyan-500/20 text-[11px]">
                              {proj.score} ball
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Skills */}
                    <div className="flex flex-wrap gap-1.5">
                      {candidate.skills.map((skill) => (
                        <span key={skill} className="px-2.5 py-1 rounded-lg bg-[#121826] text-slate-300 text-xs font-medium border border-slate-800">
                          {skill}
                        </span>
                      ))}
                    </div>

                    {/* Action Bar */}
                    <div className="pt-4 border-t border-slate-800 flex items-center justify-between gap-3">
                      <button
                        onClick={() => setDetailCandidate(candidate)}
                        className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs flex items-center gap-1.5 transition cursor-pointer"
                      >
                        <FileText className="w-3.5 h-3.5" /> Profil & CV
                      </button>

                      <button
                        onClick={() => handleOpenOfferModal(candidate)}
                        className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black text-xs sm:text-sm flex items-center gap-2 transition shadow-lg shadow-cyan-500/20 cursor-pointer transform active:scale-95"
                      >
                        <Send className="w-4 h-4" /> To'g'ridan-to'g'ri Offer
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 2: Sent Offers Tracking ── */}
        {activeTab === 'sent_offers' && (
          <div className="space-y-6">
            <div className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-6 sm:p-8 space-y-6 shadow-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-black text-white flex items-center gap-2">
                    <Send className="w-5 h-5 text-emerald-400" />
                    Kompaniyangiz Tomonidan Yuborilgan Rasmiy Offerlar
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">Talabalar qabul qilgan va ko'rib chiqayotgan takliflar holati</p>
                </div>
                <span className="px-3 py-1 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold">
                  {sentOffers.length} ta faol offer
                </span>
              </div>

              {sentOffers.length === 0 ? (
                <div className="py-12 text-center text-slate-500 space-y-2">
                  <Send className="w-8 h-8 mx-auto text-slate-600" />
                  <div>Hali nomzodlarga offer yuborilmagan.</div>
                </div>
              ) : (
                <div className="space-y-4">
                  {sentOffers.map((offer) => (
                    <div key={offer.id} className="bg-[#070A12] p-5 rounded-2xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-black text-white text-base">{offer.candidate_name}</span>
                          <span className="text-xs text-cyan-400 font-semibold">&bull; {offer.position}</span>
                        </div>
                        <div className="text-xs text-slate-400">
                          Kompaniya: <strong className="text-slate-200">{offer.company_name}</strong> | Taklif: <strong className="text-emerald-400">{offer.salary_offer}</strong>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-1 italic bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                          "{offer.message}"
                        </p>
                      </div>

                      <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
                        <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 animate-spin" /> Ko'rib chiqilmoqda
                        </span>
                        <span className="text-xs text-slate-500">{offer.created_at || 'Yaqinda'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Candidate Detail Modal ── */}
        {detailCandidate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
            <div className="bg-[#0B0F19] border border-slate-800 rounded-3xl max-w-2xl w-full p-6 sm:p-8 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-4">
                  <img
                    src={detailCandidate.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop'}
                    alt={detailCandidate.name}
                    className="w-16 h-16 rounded-2xl object-cover border-2 border-cyan-400/50"
                  />
                  <div>
                    <h3 className="text-xl font-black text-white flex items-center gap-2">
                      {detailCandidate.name}
                      {detailCandidate.is_vip && <Crown className="w-4 h-4 text-amber-400" />}
                    </h3>
                    <p className="text-xs text-slate-400">{detailCandidate.university} &bull; {detailCandidate.location}</p>
                    <p className="text-xs text-cyan-400 font-bold mt-0.5">TryJob Score: {detailCandidate.avg_score} / 100</p>
                  </div>
                </div>
                <button
                  onClick={() => setDetailCandidate(null)}
                  className="text-slate-400 hover:text-white text-lg font-bold p-1 cursor-pointer"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4 text-sm text-slate-300">
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Qisqacha Ma'lumot (Bio)</h4>
                  <p className="bg-[#070A12] p-3 rounded-xl border border-slate-800 text-xs leading-relaxed">
                    {detailCandidate.bio}
                  </p>
                </div>

                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Tasdiqlangan Portfolio Keyslari</h4>
                  <div className="space-y-2">
                    {detailCandidate.top_projects.map((p, idx) => (
                      <div key={idx} className="bg-[#070A12] p-3 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-bold text-white">{p.title}</div>
                          <div className="text-slate-500 text-[11px]">{p.company} topshirig'i</div>
                        </div>
                        <span className="text-cyan-400 font-black text-sm">{p.score} ball</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Texnik Ko'nikmalar</h4>
                  <div className="flex flex-wrap gap-2">
                    {detailCandidate.skills.map(s => (
                      <span key={s} className="px-3 py-1 bg-[#121826] text-xs font-semibold text-slate-200 rounded-lg border border-slate-800">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  onClick={() => setDetailCandidate(null)}
                  className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs cursor-pointer"
                >
                  Yopish
                </button>
                <button
                  onClick={() => {
                    const c = detailCandidate;
                    setDetailCandidate(null);
                    handleOpenOfferModal(c);
                  }}
                  className="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-cyan-500/20"
                >
                  <Send className="w-3.5 h-3.5" /> To'g'ridan-to'g'ri Offerga o'tish
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Direct Offer Modal ── */}
        {offerModalOpen && selectedCandidate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
            <div className="bg-[#0B0F19] border border-slate-800 rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
              
              {offerSentSuccess ? (
                <div className="text-center space-y-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mx-auto text-3xl shadow-lg shadow-emerald-500/20">
                    ✉️
                  </div>
                  <h3 className="text-2xl font-black text-white">Direct Offer Muvaffaqiyatli Yuborildi!</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    <strong className="text-cyan-400">{selectedCandidate.name}</strong> ga <strong>{companyName}</strong> nomidan rasmiy Job Offer yuborildi. Nomzod email va Telegram orqali xabardor qilindi.
                  </p>
                  <div className="p-4 bg-[#070A12] rounded-2xl border border-slate-800 text-xs text-left space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Lavozim:</span>
                      <span className="font-bold text-slate-200">{position}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Taklif etilgan maosh:</span>
                      <span className="font-bold text-emerald-400">{salaryOffer}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Formati:</span>
                      <span className="font-bold text-cyan-400">{jobType}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setOfferModalOpen(false);
                      setActiveTab('sent_offers');
                    }}
                    className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-sm transition cursor-pointer shadow-lg shadow-emerald-500/20"
                  >
                    Yuborilgan Takliflarni Ko'rish
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSendOfferSubmit} className="space-y-5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Send className="w-3.5 h-3.5" /> Direct Job Offer
                      </span>
                      <h3 className="text-xl font-black text-white">{selectedCandidate.name} ga Taklif</h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setOfferModalOpen(false)}
                      className="text-slate-400 hover:text-white text-lg font-bold p-1 cursor-pointer"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">Kompaniyangiz Nomi</label>
                      <input
                        type="text"
                        required
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">Taklif etilayotgan lavozim</label>
                        <input
                          type="text"
                          required
                          value={position}
                          onChange={(e) => setPosition(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-slate-300 mb-1">Ish turi & Formati</label>
                        <select
                          value={jobType}
                          onChange={(e) => setJobType(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 cursor-pointer"
                        >
                          <option value="Full-time (Gibrid)">Full-time (Gibrid)</option>
                          <option value="Full-time (Ofisda)">Full-time (Ofisda)</option>
                          <option value="Masofaviy (Remote)">Masofaviy (Remote)</option>
                          <option value="Part-time">Part-time</option>
                          <option value="Pullik Amaliyot (Paid Internship)">Pullik Amaliyot (Paid Internship)</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">Taklif etilayotgan Oylik Maosh</label>
                      <div className="relative">
                        <DollarSign className="w-4 h-4 text-emerald-400 absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          required
                          value={salaryOffer}
                          onChange={(e) => setSalaryOffer(e.target.value)}
                          className="w-full bg-[#070A12] border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs font-bold text-emerald-400 focus:outline-none focus:border-emerald-500"
                        />
                      </div>
                    </div>

                    {/* Perks Selection */}
                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-2">Qo'shimcha Imtiyozlar & Bonuslar</label>
                      <div className="flex flex-wrap gap-1.5">
                        {perksList.map((perk) => {
                          const isSelected = selectedPerks.includes(perk);
                          return (
                            <button
                              key={perk}
                              type="button"
                              onClick={() => togglePerk(perk)}
                              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                                isSelected
                                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                                  : 'bg-[#070A12] text-slate-400 border border-slate-800 hover:border-slate-700'
                              }`}
                            >
                              {isSelected ? '✓ ' : '+ '} {perk}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-300 mb-1">Nomzodga Xabar & Taklif Izohi</label>
                      <textarea
                        rows={3}
                        required
                        value={offerMessage}
                        onChange={(e) => setOfferMessage(e.target.value)}
                        className="w-full bg-[#070A12] border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 resize-none"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setOfferModalOpen(false)}
                      className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs cursor-pointer"
                    >
                      Bekor qilish
                    </button>
                    <button
                      type="submit"
                      className="flex-1 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black text-xs transition shadow-lg shadow-cyan-500/25 cursor-pointer"
                    >
                      Offer Yuborish
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
