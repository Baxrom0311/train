import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Clock, 
  ArrowRight, 
  Play, 
  Filter, 
  Sparkles, 
  Building2, 
  CheckCircle2, 
  BookOpen, 
  Code2, 
  BarChart3, 
  Scale, 
  Shield, 
  Layers, 
  X,
  Plus
} from 'lucide-react';
import { Simulation } from '../types';
import { useLanguage } from '../i18n/LanguageContext';

interface CatalogPageProps {
  simulations: Simulation[];
  onSelectSimulation: (slug: string) => void;
  onNavigate?: (view: string) => void;
}

export const CatalogPage: React.FC<CatalogPageProps> = ({ 
  simulations, 
  onSelectSimulation, 
  onNavigate 
}) => {
  const { t } = useLanguage();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Filtering logic
  const filteredSimulations = useMemo(() => {
    return simulations.filter((sim) => {
      const matchesCat =
        selectedCategory === 'all' ||
        sim.category.toLowerCase().includes(selectedCategory.toLowerCase());
      
      const matchesDiff =
        selectedDifficulty === 'all' ||
        (sim.difficulty && sim.difficulty.toLowerCase() === selectedDifficulty.toLowerCase());

      const query = searchQuery.trim().toLowerCase();
      const matchesSearch =
        !query ||
        sim.title.toLowerCase().includes(query) ||
        sim.description.toLowerCase().includes(query) ||
        sim.company?.name.toLowerCase().includes(query) ||
        (sim.learning_outcomes && sim.learning_outcomes.some(lo => lo.toLowerCase().includes(query)));

      return matchesCat && matchesDiff && matchesSearch;
    });
  }, [simulations, selectedCategory, selectedDifficulty, searchQuery]);

  // Counts for Category Pills
  const engCount = simulations.filter(s => s.category.toLowerCase().includes('engineering')).length;
  const finCount = simulations.filter(s => s.category.toLowerCase().includes('finance')).length;
  const dataCount = simulations.filter(s => s.category.toLowerCase().includes('analytics') || s.category.toLowerCase().includes('consulting')).length;
  const legalCount = simulations.filter(s => s.category.toLowerCase().includes('legal') || s.category.toLowerCase().includes('audit')).length;
  const cyberCount = simulations.filter(s => s.category.toLowerCase().includes('cyber') || s.category.toLowerCase().includes('security')).length;

  const categories = [
    { id: 'all', label: t('cat_filter_all'), count: simulations.length, icon: Sparkles },
    { id: 'Engineering', label: t('cat_filter_eng'), count: engCount, icon: Code2 },
    { id: 'Finance', label: t('cat_filter_fin'), count: finCount, icon: BarChart3 },
    { id: 'Analytics', label: t('cat_filter_data'), count: dataCount, icon: Layers },
    { id: 'Legal', label: t('cat_filter_legal'), count: legalCount, icon: Scale },
  ];

  const difficulties = [
    { id: 'all', label: t('cat_diff_all') },
    { id: 'Junior', label: t('cat_diff_junior'), color: 'emerald' },
    { id: 'Middle', label: t('cat_diff_middle'), color: 'indigo' },
    { id: 'Senior', label: t('cat_diff_senior'), color: 'purple' },
  ];

  const getDifficultyBadge = (diff?: string) => {
    const d = (diff || 'Junior').toLowerCase();
    if (d.includes('senior') || d.includes('advanced')) {
      return {
        bg: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
        dot: 'bg-purple-400',
        label: 'Senior'
      };
    }
    if (d.includes('middle') || d.includes('intermediate')) {
      return {
        bg: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
        dot: 'bg-indigo-400',
        label: 'Middle'
      };
    }
    return {
      bg: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
      dot: 'bg-emerald-400',
      label: 'Junior'
    };
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 font-sans pb-24 relative overflow-x-hidden">
      
      {/* Background Neon Aura Lights */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[350px] bg-gradient-to-b from-indigo-900/20 via-purple-900/10 to-transparent blur-[140px] pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 space-y-10">
        
        {/* ── HEADER & HR BUILDER CTA ────────────────────────────────────────── */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pt-4">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-bold uppercase tracking-wider backdrop-blur-md">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>{t('cat_all_programs')}</span>
            </div>
            
            <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight">
              {t('cat_title')}
            </h1>

            <p className="text-slate-400 text-sm sm:text-base max-w-2xl leading-relaxed">
              {t('cat_desc')}
            </p>
          </div>

          {/* HR / Creator Callout Box */}
          {onNavigate && (
            <div className="rounded-3xl p-6 bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-slate-900/80 border border-indigo-500/20 shadow-2xl backdrop-blur-xl shrink-0 max-w-sm space-y-3 relative overflow-hidden group hover:border-indigo-500/40 transition-all">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-indigo-400 uppercase tracking-wider">
                  {t('cat_creator_tag')}
                </span>
                <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  <Building2 className="w-4 h-4" />
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {t('cat_creator_desc')}
              </p>
              <button
                onClick={() => onNavigate('create-simulation')}
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-lg shadow-indigo-500/20 border border-indigo-400/30"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{t('cat_creator_btn')}</span>
                <ArrowRight className="w-3.5 h-3.5 ml-auto" />
              </button>
            </div>
          )}
        </div>

        {/* ── FILTER & SEARCH CONTROL BAR (LINEAR / VERCEL STYLE) ───────────── */}
        <div className="space-y-4">
          
          {/* Main Controls Wrapper */}
          <div className="p-3 sm:p-4 rounded-3xl bg-slate-900/60 border border-white/10 backdrop-blur-2xl shadow-xl flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
            
            {/* Category Pills */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
              {categories.map((cat) => {
                const Icon = cat.icon;
                const isSelected = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3.5 py-2 rounded-2xl text-xs font-bold transition-all duration-200 cursor-pointer flex items-center gap-2 whitespace-nowrap shrink-0 border ${
                      isSelected
                        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white border-indigo-400/30 shadow-lg shadow-indigo-500/25'
                        : 'bg-white/[0.03] text-slate-300 hover:text-white hover:bg-white/[0.06] border-white/5'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                    <span>{cat.label}</span>
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                      isSelected ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'
                    }`}>
                      {cat.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Search Input Box */}
            <div className="relative w-full lg:w-80 shrink-0">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                placeholder={t('cat_search_placeholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950/80 border border-white/10 rounded-2xl pl-10 pr-9 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-full text-slate-400 hover:text-white hover:bg-white/10"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

          </div>

          {/* Secondary Sub-filters: Difficulty Filters & Active Status */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-2">
            
            {/* Difficulty Pills */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-slate-400 mr-1 flex items-center gap-1">
                <Filter className="w-3 h-3" /> Daraja:
              </span>
              {difficulties.map((diff) => {
                const isSelected = selectedDifficulty === diff.id;
                return (
                  <button
                    key={diff.id}
                    onClick={() => setSelectedDifficulty(diff.id)}
                    className={`px-3 py-1 rounded-xl text-[11px] font-semibold transition-all cursor-pointer border ${
                      isSelected
                        ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 shadow-xs'
                        : 'bg-white/[0.02] text-slate-400 hover:text-slate-200 border-white/5'
                    }`}
                  >
                    {diff.label}
                  </button>
                );
              })}
            </div>

            {/* Results Count */}
            <div className="text-xs text-slate-400 font-mono">
              <span className="text-indigo-400 font-bold">{filteredSimulations.length}</span> {t('cat_showing_results')}
            </div>

          </div>

        </div>

        {/* ── SIMULATIONS GRID (STRIPE / LINEAR CARDS) ──────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSimulations.map((sim) => {
            const diffBadge = getDifficultyBadge(sim.difficulty);

            return (
              <div
                key={sim.id}
                onClick={() => onSelectSimulation(sim.slug)}
                className="group relative rounded-3xl bg-slate-900/40 border border-white/10 hover:border-indigo-500/50 hover:bg-slate-900/80 p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 cursor-pointer shadow-xl hover:shadow-2xl hover:shadow-indigo-500/10 hover:-translate-y-1.5 backdrop-blur-xl overflow-hidden"
              >
                {/* Top Subtle Sheen Overlay */}
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:via-indigo-400/50 transition-all" />

                <div>
                  
                  {/* Category Pill & Difficulty Badge & Duration */}
                  <div className="flex items-center justify-between gap-2 mb-5">
                    <span className="px-3 py-1 rounded-xl text-[11px] font-bold bg-white/[0.04] text-slate-200 border border-white/10 group-hover:border-indigo-500/30 transition-colors">
                      {sim.category}
                    </span>

                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold border flex items-center gap-1.5 ${diffBadge.bg}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${diffBadge.dot}`} />
                        {diffBadge.label}
                      </span>
                      
                      <span className="text-xs font-semibold text-slate-400 flex items-center gap-1 shrink-0">
                        <Clock className="w-3.5 h-3.5 text-slate-500" /> ~{sim.estimated_hours} {t('cat_hours_suffix')}
                      </span>
                    </div>
                  </div>

                  {/* Company Info */}
                  <div className="flex items-center gap-3.5 mb-4">
                    <img
                      src={sim.company?.logo_url || 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=80&q=80'}
                      alt={sim.company?.name}
                      className="w-11 h-11 rounded-2xl object-cover border border-white/10 group-hover:border-indigo-500/40 transition-colors shadow-md"
                    />
                    <div>
                      <div className="text-xs font-bold text-white group-hover:text-indigo-300 transition-colors">
                        {sim.company?.name}
                      </div>
                      <div className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> {t('cat_verified_partner')}
                      </div>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-black text-white mb-2.5 group-hover:text-indigo-300 transition-colors leading-snug">
                    {sim.title}
                  </h3>

                  {/* Description */}
                  <p className="text-slate-400 text-xs leading-relaxed line-clamp-3 mb-5">
                    {sim.description}
                  </p>

                  {/* Learning Outcomes / Skills */}
                  {sim.learning_outcomes && sim.learning_outcomes.length > 0 && (
                    <div className="space-y-2 mb-6 border-t border-white/5 pt-4">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                        {t('cat_learning_outcomes')}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {sim.learning_outcomes.slice(0, 3).map((out, i) => (
                          <span 
                            key={i} 
                            className="text-[10px] bg-white/[0.03] text-slate-300 px-2.5 py-1 rounded-lg border border-white/5 truncate max-w-full font-medium group-hover:border-white/10 transition-colors"
                          >
                            {out}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                </div>

                {/* Bottom CTA Button */}
                <div className="pt-2">
                  <button className="w-full bg-white/[0.04] group-hover:bg-gradient-to-r group-hover:from-indigo-600 group-hover:to-purple-600 text-slate-200 group-hover:text-white font-bold py-3 px-4 rounded-2xl transition-all duration-300 text-center flex items-center justify-center gap-2 text-xs border border-white/5 group-hover:border-indigo-400/30 shadow-lg group-hover:shadow-indigo-500/20 cursor-pointer">
                    <span>{t('cat_start_btn')}</span>
                    <Play className="w-3.5 h-3.5 fill-current group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </div>

              </div>
            );
          })}
        </div>

        {/* ── EMPTY STATE ────────────────────────────────────────────────────── */}
        {filteredSimulations.length === 0 && (
          <div className="text-center py-20 bg-slate-900/30 rounded-3xl border border-white/5 space-y-4 backdrop-blur-md">
            <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/10 text-slate-400 flex items-center justify-center mx-auto">
              <Search className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-slate-300 font-bold text-base">{t('cat_no_results')}</p>
              <p className="text-slate-500 text-xs">Qidiruv so'zini o'zgartiring yoki filtrlarni tozalang.</p>
            </div>
            <button 
              onClick={() => { 
                setSelectedCategory('all'); 
                setSelectedDifficulty('all');
                setSearchQuery(''); 
              }} 
              className="px-5 py-2.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-bold text-indigo-300 hover:text-white transition cursor-pointer"
            >
              {t('cat_reset_filters')}
            </button>
          </div>
        )}

      </div>
    </div>
  );
};
