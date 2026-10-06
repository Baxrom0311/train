import React, { useState, useEffect } from 'react';
import { 
  Building, 
  GraduationCap, 
  Users, 
  Award, 
  TrendingUp, 
  FileSpreadsheet, 
  Download, 
  CheckCircle2, 
  Briefcase, 
  BarChart3, 
  ChevronRight, 
  ShieldCheck, 
  ExternalLink,
  BookOpen,
  Sparkles,
  School,
  Printer,
  FileText,
  Calendar,
  X,
  Layers,
  ArrowUpRight,
  SlidersHorizontal
} from 'lucide-react';
import { UniversityStats } from '../types';
import { getUniversityStats } from '../api';

export const UniversityPortalPage: React.FC = () => {
  const [stats, setStats] = useState<UniversityStats | null>(null);
  const [selectedUniversity, setSelectedUniversity] = useState<string>('urdu');
  const [loading, setLoading] = useState<boolean>(true);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  
  // Interactive chart state
  const [activeChartMetric, setActiveChartMetric] = useState<'completions' | 'avgScore' | 'hired'>('completions');
  const [hoveredMonth, setHoveredMonth] = useState<number | null>(null);

  // PDF Official Report Preview Modal
  const [pdfModalOpen, setPdfModalOpen] = useState<boolean>(false);

  const universitiesList = [
    { id: 'urdu', name: 'UrDU (Urganch davlat universiteti)' },
    { id: 'wiut', name: 'Westminster Xalqaro Universiteti (WIUT)' },
    { id: 'inha', name: 'Inha Universiteti Toshkent (IUT)' },
    { id: 'tdiu', name: 'TDIU (Toshkent Davlat Iqtisodiyot Universiteti)' },
    { id: 'tdyu', name: 'TDYU (Toshkent Davlat Yuridik Universiteti)' }
  ];

  useEffect(() => {
    loadStats();
  }, [selectedUniversity]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await getUniversityStats(selectedUniversity);
      setStats(data);
    } catch (e) {
      console.error('Error loading university stats:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportExcel = () => {
    if (!stats) return;
    
    // Generate CSV content
    const rows = [
      ['TryJob OTM Amaliyot Monitoring Hisoboti - 2026'],
      ['OTM Nomi', stats.university_name],
      ['Qisqa Nomi', stats.short_name],
      ['Jami Talabalar', stats.total_students.toString()],
      ['Amaliyot O\'tganlar', stats.active_interns.toString()],
      ['O\'rtacha Ball', stats.average_score.toString()],
      ['Bandlik Ko\'rsatkichi', `${stats.hiring_rate_percent}%`],
      [],
      ['Fakultetlar Kesimida:'],
      ['Fakultet', 'O\'rtacha Ball', 'Bajarilish Foizi (%)'],
      ...stats.departments.map(d => [d.name, d.avg_score.toString(), `${d.completion_rate}%`]),
      [],
      ['Oylik Dinamika:'],
      ['Oy', 'Topshirilgan Keyslar', 'O\'rtacha Ball'],
      ...stats.monthly_trend.map(m => [m.month, m.completions.toString(), m.avg_score.toString()])
    ];

    const csvContent = '\uFEFF' + rows.map(e => e.map(cell => `"${(cell || '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `TryJob_${stats.short_name}_Amaliyot_Hisoboti_2026.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setExportNotice(`${stats?.short_name || 'OTM'} bo'yicha 2026-yilgi amaliyot hisoboti (CSV/Excel) muvaffaqiyatli yuklab olindi.`);
    setTimeout(() => setExportNotice(null), 4000);
  };

  const handleOpenPdfReport = () => {
    setPdfModalOpen(true);
  };

  const handlePrintPdf = () => {
    window.print();
  };

  if (!stats && loading) {
    return (
      <div className="min-h-screen bg-[#07090E] flex items-center justify-center text-slate-400">
        Universitet statistikasi yuklanmoqda...
      </div>
    );
  }

  const maxCompletions = stats ? Math.max(...stats.monthly_trend.map(m => m.completions)) : 1;

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 py-10 px-4 sm:px-6 lg:px-8 selection:bg-indigo-500/30 selection:text-indigo-200">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Export Toast Notification */}
        {exportNotice && (
          <div className="fixed top-24 right-6 z-50 bg-emerald-600 text-white px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 animate-fade-in">
            <CheckCircle2 className="w-5 h-5 text-amber-300" />
            <span className="text-sm font-bold">{exportNotice}</span>
          </div>
        )}

        {/* ── Top Header & University Selector ── */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 bg-[#0B0F19]/90 backdrop-blur-md rounded-3xl border border-slate-800 p-6 sm:p-8 shadow-[0_0_50px_rgba(99,102,241,0.08)]">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 font-black text-2xl shadow-lg shadow-indigo-500/15">
              <School className="w-7 h-7" />
            </div>
            <div>
              <div className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" /> Oliy Ta'lim Amaliyot & Karyera Markazi Portali
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-white mt-0.5">
                {stats?.university_name}
              </h1>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full md:w-auto">
            <select
              value={selectedUniversity}
              onChange={(e) => setSelectedUniversity(e.target.value)}
              className="bg-[#070A12] border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-200 focus:outline-none focus:border-indigo-500 shadow cursor-pointer"
            >
              {universitiesList.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>

            <button
              onClick={handleExportExcel}
              className="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-emerald-600/20 cursor-pointer"
            >
              <FileSpreadsheet className="w-4 h-4" /> Excel Hisobot
            </button>

            <button
              onClick={handleOpenPdfReport}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-600/25 cursor-pointer"
            >
              <FileText className="w-4 h-4" /> Rasmiy PDF Reestr
            </button>
          </div>
        </div>

        {/* ── KPI Metric Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-[#0B0F19]/90 rounded-2xl border border-slate-800 p-6 space-y-2 shadow-xl hover:border-cyan-500/40 transition">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-bold uppercase tracking-wider">Jami Talabalar</span>
              <Users className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-3xl font-black text-white">{stats?.total_students}</div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              <span className="text-emerald-400 font-bold">+{stats?.active_interns}</span> faol virtual amaliyotda
            </div>
          </div>

          <div className="bg-[#0B0F19]/90 rounded-2xl border border-slate-800 p-6 space-y-2 shadow-xl hover:border-amber-500/40 transition">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-bold uppercase tracking-wider">Tugallangan Keyslar</span>
              <Award className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-3xl font-black text-amber-400">{stats?.completed_simulations}</div>
            <div className="text-xs text-slate-400">
              HMAC sertifikati berilgan
            </div>
          </div>

          <div className="bg-[#0B0F19]/90 rounded-2xl border border-slate-800 p-6 space-y-2 shadow-xl hover:border-emerald-500/40 transition">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-bold uppercase tracking-wider">O'rtacha O'zlashtirish</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-3xl font-black text-emerald-400">{stats?.average_score} <span className="text-base text-slate-400">/ 100</span></div>
            <div className="text-xs text-slate-400">
              AI ob'ektiv bahosi
            </div>
          </div>

          <div className="bg-[#0B0F19]/90 rounded-2xl border border-slate-800 p-6 space-y-2 shadow-xl hover:border-purple-500/40 transition">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-bold uppercase tracking-wider">Hiring & Offer Rate</span>
              <Briefcase className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-3xl font-black text-purple-400">{stats?.hiring_rate_percent}%</div>
            <div className="text-xs text-slate-400">
              {stats?.partner_companies_count}+ korxona taklif bergan
            </div>
          </div>
        </div>

        {/* ── Monthly Progress & Department Rankings ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Monthly Completion Interactive SVG Chart */}
          <div className="lg:col-span-2 bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-6 sm:p-8 space-y-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-black text-white flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-cyan-400" />
                  Oylik Amaliyot Dinamikasi & Monitoring (2026)
                </h3>
                <p className="text-xs text-slate-400 mt-1">Talabalar tomonidan muvaffaqiyatli topshirilgan korporativ keyslar soni</p>
              </div>
              
              <div className="flex items-center gap-1.5 bg-[#070A12] p-1 rounded-xl border border-slate-800">
                <button
                  onClick={() => setActiveChartMetric('completions')}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition cursor-pointer ${
                    activeChartMetric === 'completions'
                      ? 'bg-cyan-500 text-slate-950'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Keyslar soni
                </button>
                <button
                  onClick={() => setActiveChartMetric('avgScore')}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition cursor-pointer ${
                    activeChartMetric === 'avgScore'
                      ? 'bg-emerald-500 text-slate-950'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  O'rtacha Ball
                </button>
              </div>
            </div>

            {/* Custom Interactive SVG/CSS Bar & Spline Chart */}
            <div className="pt-6 pb-2">
              <div className="relative flex items-end justify-between gap-3 sm:gap-6 h-56 border-b border-slate-800/80 px-4">
                {stats?.monthly_trend.map((m, idx) => {
                  const value = activeChartMetric === 'completions' ? m.completions : m.avg_score;
                  const maxVal = activeChartMetric === 'completions' ? maxCompletions : 100;
                  const heightPercent = Math.round((value / maxVal) * 100);
                  const isHovered = hoveredMonth === idx;

                  return (
                    <div 
                      key={m.month} 
                      onMouseEnter={() => setHoveredMonth(idx)}
                      onMouseLeave={() => setHoveredMonth(null)}
                      className="flex-1 flex flex-col items-center gap-2 group cursor-pointer relative"
                    >
                      {/* Tooltip */}
                      <div className={`absolute -top-10 bg-[#121826] border border-cyan-500/50 text-cyan-300 font-black text-xs px-2.5 py-1 rounded-lg shadow-xl pointer-events-none transition-all duration-200 z-20 ${
                        isHovered ? 'opacity-100 scale-100' : 'opacity-0 scale-90'
                      }`}>
                        {value} {activeChartMetric === 'completions' ? 'ta keys' : 'ball'}
                      </div>

                      <div className="w-full max-w-[52px] bg-slate-900 rounded-t-xl overflow-hidden flex flex-col justify-end group-hover:bg-slate-800 transition h-full">
                        <div 
                          className={`w-full rounded-t-xl transition-all duration-500 shadow-lg ${
                            activeChartMetric === 'completions'
                              ? 'bg-gradient-to-t from-cyan-600 via-blue-500 to-cyan-400 group-hover:from-cyan-400 group-hover:to-cyan-300 shadow-cyan-500/20'
                              : 'bg-gradient-to-t from-emerald-600 via-teal-500 to-emerald-400 group-hover:from-emerald-400 group-hover:to-emerald-300 shadow-emerald-500/20'
                          }`}
                          style={{ height: `${heightPercent}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-slate-400 mt-1">{m.month}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 bg-[#070A12] p-3.5 rounded-2xl border border-slate-800">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                Eng faol oylik cho'qqi: <strong className="text-white">Sentyabr (560 ta topshirilgan keys)</strong>
              </span>
              <span className="text-emerald-400 font-bold">+38% o'tgan yilga nisbatan o'sish</span>
            </div>
          </div>

          {/* Department Rankings */}
          <div className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-6 sm:p-8 space-y-6 shadow-xl">
            <div>
              <h3 className="text-lg font-black text-white flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-indigo-400" />
                Fakultetlar Reytingi
              </h3>
              <p className="text-xs text-slate-400 mt-1">O'zlashtirish va amaliyot o'tash foizi</p>
            </div>

            <div className="space-y-4">
              {stats?.departments.map((dept, idx) => (
                <div key={idx} className="bg-[#070A12] p-3.5 rounded-2xl border border-slate-800 space-y-2 hover:border-slate-700 transition">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white">{dept.name}</span>
                    <span className="text-cyan-400 font-black">{dept.avg_score} ball</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-500 h-2 rounded-full transition-all duration-700" 
                      style={{ width: `${dept.completion_rate}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{dept.student_count} talaba</span>
                    <span>{dept.completion_rate}% yakunlangan</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* ── Top Performers & Job Offers Table ── */}
        <div className="bg-[#0B0F19]/90 rounded-3xl border border-slate-800 p-6 sm:p-8 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-black text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                {stats?.short_name}ning Yetakchi Iqtidorli Talabalari
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Kompaniyalar tomonidan e'tirof etilgan va ish taklifi olgan bitiruvchilar</p>
            </div>
            <button
              onClick={handleOpenPdfReport}
              className="px-4 py-2 rounded-xl bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 text-xs font-bold flex items-center gap-2 hover:bg-indigo-500/25 transition cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5" /> Reestrni Chop Etish (PDF)
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#070A12] text-slate-400 font-bold uppercase text-xs tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-5">Talaba Ismi</th>
                  <th className="py-3.5 px-5">Bosqich & Fakultet</th>
                  <th className="py-3.5 px-5 text-center">Sertifikatlar</th>
                  <th className="py-3.5 px-5 text-center">TryJob Bali</th>
                  <th className="py-3.5 px-5">Amaliyot / Ish Holati</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {stats?.top_performers.map((performer, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="py-4 px-5 font-bold text-white flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-full bg-slate-800 text-cyan-400 text-xs flex items-center justify-center font-bold">
                        {idx + 1}
                      </span>
                      {performer.name}
                    </td>
                    <td className="py-4 px-5 text-xs text-slate-300">
                      {performer.course}-kurs, {performer.faculty}
                    </td>
                    <td className="py-4 px-5 text-center font-bold text-white text-xs">
                      <span className="bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700">
                        {performer.cert_count} ta
                      </span>
                    </td>
                    <td className="py-4 px-5 text-center font-black text-cyan-400 text-base">
                      {performer.score}
                    </td>
                    <td className="py-4 px-5">
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        ✓ {performer.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Official PDF Academic Report Modal ── */}
        {pdfModalOpen && stats && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
            <div className="bg-white text-slate-900 border border-slate-200 rounded-3xl max-w-3xl w-full p-8 space-y-6 shadow-2xl relative max-h-[90vh] overflow-y-auto print:p-0 print:border-none print:shadow-none">
              
              {/* Header for print / modal */}
              <div className="flex items-start justify-between border-b-2 border-slate-800 pb-4">
                <div className="space-y-1">
                  <div className="text-[11px] font-black uppercase tracking-widest text-indigo-900">
                    O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI
                  </div>
                  <h2 className="text-xl font-black text-slate-950">
                    {stats.university_name}
                  </h2>
                  <p className="text-xs text-slate-600">
                    Talabalarning Virtual Amaliyot va Korporativ Simulyatsiyalar Natijalari Bo'yicha Rasmiy Reestri
                  </p>
                </div>
                <button
                  onClick={() => setPdfModalOpen(false)}
                  className="text-slate-500 hover:text-black font-bold p-1 print:hidden cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Report Metadata */}
              <div className="grid grid-cols-3 gap-4 text-xs bg-slate-100 p-4 rounded-xl">
                <div>
                  <span className="text-slate-500 block">Hisobot Sanasi:</span>
                  <strong className="text-slate-900">2026-yil Oktyabr</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">Jami Amaliyotchilar:</span>
                  <strong className="text-slate-900">{stats.total_students} nafar</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">O'rtacha Ball:</span>
                  <strong className="text-indigo-900 font-bold">{stats.average_score} / 100</strong>
                </div>
              </div>

              {/* Performers Table for Official Seal */}
              <div>
                <h4 className="text-xs font-black uppercase text-slate-800 mb-2">Eng Yuqori Natija Ko'rsatgan Talabalar Ro'yxati</h4>
                <table className="w-full text-xs text-left border border-slate-300">
                  <thead className="bg-slate-200 text-slate-700 font-bold">
                    <tr>
                      <th className="p-2 border border-slate-300">№</th>
                      <th className="p-2 border border-slate-300">F.I.SH</th>
                      <th className="p-2 border border-slate-300">Fakultet / Kurs</th>
                      <th className="p-2 border border-slate-300 text-center">HMAC Ball</th>
                      <th className="p-2 border border-slate-300">Amaliyot / Ish Natijasi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.top_performers.map((p, i) => (
                      <tr key={i} className="border-b border-slate-300">
                        <td className="p-2 border border-slate-300 font-bold">{i + 1}</td>
                        <td className="p-2 border border-slate-300 font-semibold">{p.name}</td>
                        <td className="p-2 border border-slate-300">{p.faculty} ({p.course}-kurs)</td>
                        <td className="p-2 border border-slate-300 text-center font-bold text-indigo-700">{p.score}</td>
                        <td className="p-2 border border-slate-300">{p.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Official Seal / Signatures Section */}
              <div className="pt-6 border-t border-slate-300 flex justify-between items-end text-xs">
                <div>
                  <p className="font-bold text-slate-800">O'quv ishlari bo'yicha prorektor:</p>
                  <p className="text-slate-500 mt-6">_____________________ (Imzo / Muhr)</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-slate-800">Karyera va amaliyot markazi boshlig'i:</p>
                  <p className="text-slate-500 mt-6">_____________________ (Imzo)</p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 flex items-center justify-end gap-3 print:hidden">
                <button
                  onClick={() => setPdfModalOpen(false)}
                  className="px-5 py-2.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs cursor-pointer"
                >
                  Yopish
                </button>
                <button
                  onClick={handlePrintPdf}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-black text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-indigo-600/30"
                >
                  <Printer className="w-4 h-4" /> Chop etish / PDF qilib saqlash
                </button>
              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
};
