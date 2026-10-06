import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  ArrowLeft, Clock, Mic, Award, CheckCircle2, Play, Pause, Headphones, 
  Database, Download, Table, Edit3, CheckCheck, PlayCircle, Paperclip, 
  Sparkles, Terminal, FileSpreadsheet, Bot, AlertTriangle, Lightbulb, 
  ArrowRight, FileCheck, Check, Loader2, Zap, Flame, ShieldAlert, TrendingUp,
  Copy, RotateCcw, Code2, FileText, Volume2, VolumeX, Eye, Columns, 
  FileCode, Info, ChevronRight, Filter, Search, ArrowUpDown, 
  CheckSquare, Square, Star, SlidersHorizontal, BookOpen, AlertCircle
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { Simulation, SimulationTask, SubmissionResponse } from '../types';
import { fetchSimulationDetail, runPythonSandbox, submitTaskSolution, issueCertificate } from '../api';

interface WorkspacePageProps {
  simulationSlug: string;
  onBack: () => void;
  onOpenInterview: () => void;
  onOpenDocAudit: () => void;
  onViewCertificate: (certUuid: string) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Audio Waveform Equalizer Component
// ─────────────────────────────────────────────────────────────────────────────
const AudioWaveformPlayer: React.FC<{
  supervisorName?: string;
  duration?: string;
  transcript?: string;
}> = ({ supervisorName, duration = '01:45', transcript }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showTranscript, setShowTranscript] = useState(false);
  const intervalRef = useRef<any>(null);

  const durationSec = useMemo(() => {
    const parts = duration.split(':').map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    return 105;
  }, [duration]);

  useEffect(() => {
    if (isPlaying) {
      intervalRef.current = setInterval(() => {
        setProgress((prev) => {
          const next = prev + (0.5 * playbackSpeed);
          if (next >= durationSec) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
      }, 500);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, playbackSpeed, durationSec]);

  const toggleSpeed = () => {
    const speeds = [1.0, 1.25, 1.5, 2.0];
    const nextIdx = (speeds.indexOf(playbackSpeed) + 1) % speeds.length;
    setPlaybackSpeed(speeds[nextIdx]);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const waveformHeights = [
    25, 45, 70, 30, 85, 95, 60, 40, 75, 100, 80, 50, 
    90, 65, 35, 80, 95, 55, 70, 40, 85, 60, 45, 30
  ];

  return (
    <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800/90 rounded-2xl p-5 space-y-4 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Rahbar Ovozli Yo'riqnomasi ({supervisorName || 'Supervisor'})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="text-[11px] font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5" />
            {showTranscript ? 'Transkriptni yashirish' : 'Transkriptni o\'qish'}
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-4 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
        {/* Play/Pause Button */}
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 flex items-center justify-center transition shadow-lg shadow-cyan-500/25 shrink-0 cursor-pointer"
          title={isPlaying ? 'Pauza' : 'Ijro etish'}
        >
          {isPlaying ? <Pause className="w-5 h-5 fill-slate-950" /> : <Play className="w-5 h-5 fill-slate-950 ml-0.5" />}
        </button>

        {/* Waveform Equalizer Display */}
        <div className="flex-1 w-full space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span className="text-cyan-400 font-bold">{formatTime(progress)}</span>
            <span>{duration}</span>
          </div>

          <div 
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - rect.left;
              const ratio = Math.max(0, Math.min(1, clickX / rect.width));
              setProgress(ratio * durationSec);
            }}
            className="h-10 bg-slate-900/90 rounded-xl flex items-center justify-between gap-1 px-3 border border-slate-800 cursor-pointer overflow-hidden group"
          >
            {waveformHeights.map((h, i) => {
              const currentRatio = progress / durationSec;
              const barRatio = i / waveformHeights.length;
              const isPassed = barRatio <= currentRatio;
              const dynamicHeight = isPlaying 
                ? Math.max(20, Math.min(100, h + (Math.sin(Date.now() / 200 + i) * 30)))
                : h;

              return (
                <div
                  key={i}
                  className="flex-1 flex items-center justify-center h-full"
                >
                  <span
                    className={`w-full rounded-full transition-all duration-150 ${
                      isPassed 
                        ? 'bg-gradient-to-t from-cyan-500 to-emerald-400' 
                        : 'bg-slate-700/80 group-hover:bg-slate-600'
                    }`}
                    style={{
                      height: `${dynamicHeight}%`,
                      maxWidth: '4px'
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Audio Controls */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <button
            onClick={toggleSpeed}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-300 text-xs font-mono font-bold transition cursor-pointer"
            title="Ijro tezligi"
          >
            {playbackSpeed}x
          </button>
          <button
            onClick={() => setIsMuted(!isMuted)}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 transition cursor-pointer"
            title={isMuted ? 'Ovozni yoqish' : 'Ovozni o\'chirish'}
          >
            {isMuted ? <VolumeX className="w-4 h-4 text-rose-400" /> : <Volume2 className="w-4 h-4 text-cyan-400" />}
          </button>
        </div>
      </div>

      {/* Expandable Transcript */}
      {showTranscript && (
        <div className="p-4 rounded-xl bg-slate-950/90 border border-cyan-500/20 text-xs text-slate-300 leading-relaxed animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold mb-1.5">
            <Headphones className="w-3.5 h-3.5" />
            <span>To'liq Ovozli Transkript:</span>
          </div>
          <p className="whitespace-pre-line text-slate-300/90">
            {transcript || "Assalomu alaykum va xush kelibsiz! Ushbu amaliy vazifada siz korxona darajasidagi real biznes holatini tahlil qilasiz. Barcha talablarni sinchiklab o'rganib chiqing va yechimingizni taqdim eting."}
          </p>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Interactive Data Assets Table Component
// ─────────────────────────────────────────────────────────────────────────────
const InteractiveDataTable: React.FC<{
  dataset?: {
    title: string;
    headers: string[];
    rows: string[][];
  };
  onExportCSV: () => void;
}> = ({ dataset, onExportCSV }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [viewMode, setViewMode] = useState<'table' | 'dictionary'>('table');
  const [copiedJSON, setCopiedJSON] = useState(false);

  if (!dataset || !dataset.headers || dataset.headers.length === 0) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-8 text-center space-y-3 shadow-xl">
        <Database className="w-10 h-10 text-slate-600 mx-auto" />
        <h4 className="text-sm font-bold text-slate-200">Ushbu vazifa uchun to'g'ridan-to'g'ri jadval talab etilmaydi</h4>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Chap tomondagi "Ishchi Resurslar To'plami" fayllari (.pdf, .xlsx) orqali vazifani tahlil qilishingiz mumkin.
        </p>
      </div>
    );
  }

  const handleSort = (colIdx: number) => {
    if (sortCol === colIdx) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(colIdx);
      setSortAsc(true);
    }
  };

  const filteredRows = useMemo(() => {
    let list = [...dataset.rows];
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      list = list.filter(row => row.some(cell => cell.toLowerCase().includes(term)));
    }
    if (sortCol !== null) {
      list.sort((a, b) => {
        const valA = a[sortCol] || '';
        const valB = b[sortCol] || '';
        const numA = parseFloat(valA.replace(/[^0-9.-]+/g, ''));
        const numB = parseFloat(valB.replace(/[^0-9.-]+/g, ''));
        if (!isNaN(numA) && !isNaN(numB)) {
          return sortAsc ? numA - numB : numB - numA;
        }
        return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });
    }
    return list;
  }, [dataset.rows, searchTerm, sortCol, sortAsc]);

  const handleCopyJSON = () => {
    const jsonObj = dataset.rows.map(row => {
      const obj: Record<string, string> = {};
      dataset.headers.forEach((h, i) => {
        obj[h] = row[i] || '';
      });
      return obj;
    });
    navigator.clipboard.writeText(JSON.stringify(jsonObj, null, 2));
    setCopiedJSON(true);
    setTimeout(() => setCopiedJSON(false), 2000);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-extrabold text-white">{dataset.title || 'Korporativ Jonli Dataset'}</h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              {dataset.rows.length} yozuvlar
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real vaqtda tahlil qilish, qidirish, saralash va eksport qilish imkoniyati
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1 rounded-lg font-bold transition cursor-pointer ${
                viewMode === 'table' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
              }`}
            >
              Jadval
            </button>
            <button
              onClick={() => setViewMode('dictionary')}
              className={`px-3 py-1 rounded-lg font-bold transition cursor-pointer ${
                viewMode === 'dictionary' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
              }`}
            >
              Sxema / Lug'at
            </button>
          </div>

          <button
            onClick={handleCopyJSON}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-700 flex items-center gap-1.5 transition cursor-pointer"
            title="JSON nusxalash"
          >
            {copiedJSON ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copiedJSON ? 'Nusxalandi' : 'JSON'}
          </button>

          <button
            onClick={onExportCSV}
            className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 text-xs font-black px-3.5 py-1.5 rounded-xl flex items-center gap-1.5 shadow-md shadow-emerald-500/20 transition cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> CSV Yuklab Olish
          </button>
        </div>
      </div>

      {viewMode === 'table' ? (
        <>
          {/* Search Bar & Stats */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Ustunlar va qiymatlar bo'yicha qidirish..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono transition"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white text-xs"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="text-[11px] text-slate-400 flex items-center gap-2 self-end sm:self-auto">
              <span>Ko'rsatilmoqda: <strong className="text-white">{filteredRows.length}</strong> / {dataset.rows.length}</span>
              {sortCol !== null && (
                <span className="bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 px-2 py-0.5 rounded">
                  Saralangan: {dataset.headers[sortCol]} ({sortAsc ? 'O\'sish' : 'Kamayish'})
                </span>
              )}
            </div>
          </div>

          {/* Interactive Table */}
          <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-inner">
            <div className="overflow-x-auto max-h-[460px]">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/95 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800 sticky top-0 backdrop-blur z-10">
                  <tr>
                    <th className="p-3.5 w-12 text-center text-slate-600">#</th>
                    {dataset.headers.map((h, i) => (
                      <th
                        key={i}
                        onClick={() => handleSort(i)}
                        className="p-3.5 font-bold hover:text-cyan-400 cursor-pointer select-none transition"
                      >
                        <div className="flex items-center gap-1.5">
                          <span>{h}</span>
                          <ArrowUpDown className={`w-3 h-3 ${sortCol === i ? 'text-cyan-400' : 'text-slate-600'}`} />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {filteredRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-900/60 transition group">
                      <td className="p-3 text-center text-slate-600 text-[10px]">{rIdx + 1}</td>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="p-3 text-slate-200 whitespace-nowrap">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {filteredRows.length === 0 && (
                    <tr>
                      <td colSpan={dataset.headers.length + 1} className="p-8 text-center text-slate-500">
                        "{searchTerm}" bo'yicha hech qanday ma'lumot topilmadi.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Data Dictionary / Schema Mode */
        <div className="space-y-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {dataset.headers.map((colName, idx) => {
              const sampleVals = dataset.rows.slice(0, 3).map(r => r[idx]).filter(Boolean);
              return (
                <div key={idx} className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-cyan-400 text-xs truncate">{colName}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 uppercase font-mono">
                      Col #{idx + 1}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    <span className="text-slate-500">Namunalar:</span>
                    <ul className="mt-1 space-y-0.5 font-mono text-slate-300">
                      {sampleVals.map((v, sIdx) => (
                        <li key={sIdx} className="truncate">• {v}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Markdown Formatter & Live Preview Helper
// ─────────────────────────────────────────────────────────────────────────────
const MarkdownPreview: React.FC<{ content: string }> = ({ content }) => {
  if (!content.trim()) {
    return (
      <div className="text-slate-600 italic text-xs py-8 text-center">
        Hisobot ko'rinishi bo'sh. Yozishni boshlang...
      </div>
    );
  }

  // Safe and clean custom Markdown renderer
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let inCodeBlock = false;
  let codeBuffer: string[] = [];

  lines.forEach((line, idx) => {
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${idx}`} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 font-mono text-xs text-emerald-400 overflow-x-auto my-2">
            {codeBuffer.join('\n')}
          </pre>
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    // Headers
    if (line.startsWith('# ')) {
      elements.push(<h1 key={idx} className="text-lg font-black text-white mt-4 mb-2 pb-1 border-b border-slate-800">{line.replace('# ', '')}</h1>);
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={idx} className="text-base font-bold text-cyan-300 mt-3 mb-1.5">{line.replace('## ', '')}</h2>);
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={idx} className="text-sm font-bold text-slate-200 mt-2.5 mb-1">{line.replace('### ', '')}</h3>);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <div key={idx} className="flex items-start gap-2 text-xs text-slate-300 my-0.5 pl-2">
          <span className="text-cyan-400 font-bold">•</span>
          <span>{line.substring(2)}</span>
        </div>
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={idx} className="border-l-2 border-cyan-500 pl-3 py-1 my-2 bg-cyan-950/20 rounded-r text-xs text-slate-300 italic">
          {line.replace('> ', '')}
        </blockquote>
      );
    } else if (line.trim() === '---') {
      elements.push(<hr key={idx} className="border-slate-800 my-3" />);
    } else if (line.trim() !== '') {
      elements.push(<p key={idx} className="text-xs text-slate-300 my-1 leading-relaxed">{line}</p>);
    }
  });

  return (
    <div className="prose prose-invert max-w-none space-y-1">
      {elements}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Workspace Page
// ─────────────────────────────────────────────────────────────────────────────
export const WorkspacePage: React.FC<WorkspacePageProps> = ({
  simulationSlug,
  onBack,
  onOpenInterview,
  onOpenDocAudit,
  onViewCertificate
}) => {
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentTaskIndex, setCurrentTaskIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<'briefing' | 'data' | 'workspace' | 'model'>('briefing');
  
  // Editor & Submission state
  const [codeContent, setCodeContent] = useState<string>('');
  const [reportContent, setReportContent] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<SubmissionResponse | null>(null);
  const [completedTaskIds, setCompletedTaskIds] = useState<Set<string>>(new Set());

  // Report editor view mode
  const [reportViewMode, setReportViewMode] = useState<'edit' | 'split' | 'preview'>('edit');

  // Infinite Adaptive Mastery Mode state
  const [masteryLevel, setMasteryLevel] = useState<number>(1);
  const [isGeneratingDynamicTask, setIsGeneratingDynamicTask] = useState<boolean>(false);
  const [dynamicTaskAlert, setDynamicTaskAlert] = useState<string | null>(null);

  // Sandbox state
  const [runningSandbox, setRunningSandbox] = useState<boolean>(false);
  const [sandboxResult, setSandboxResult] = useState<{ success: boolean; output: string; error?: string; execution_time_ms: number } | null>(null);
  const [sandboxTab, setSandboxTab] = useState<'output' | 'diagnostics'>('output');

  // Compare diff mode in Model Answer tab
  const [compareMode, setCompareMode] = useState<boolean>(false);
  const [copiedModelAnswer, setCopiedModelAnswer] = useState<boolean>(false);

  // Load completed tasks on mount
  useEffect(() => {
    try {
      const savedCompleted = localStorage.getItem(`tryjob_completed_${simulationSlug}`);
      if (savedCompleted) {
        setCompletedTaskIds(new Set(JSON.parse(savedCompleted)));
      }
    } catch (e) {
      console.error("Error loading completed tasks:", e);
    }
  }, [simulationSlug]);

  // Persist completed tasks when updated
  useEffect(() => {
    if (completedTaskIds.size > 0) {
      localStorage.setItem(`tryjob_completed_${simulationSlug}`, JSON.stringify(Array.from(completedTaskIds)));
    }
  }, [completedTaskIds, simulationSlug]);

  useEffect(() => {
    loadSimulation();
  }, [simulationSlug]);

  const loadSimulation = async () => {
    setLoading(true);
    try {
      const data = await fetchSimulationDetail(simulationSlug);
      setSimulation(data);
      if (data.tasks && data.tasks.length > 0) {
        initTask(data.tasks[0]);
      }
    } catch (err) {
      console.error("Simulation load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const initTask = (task: SimulationTask) => {
    const isCode = task.resource_files?.task_type === 'code' || task.mentor_persona === 'lead_engineer';
    const draftKey = `tryjob_draft_${simulationSlug}_${task.id}`;
    const savedDraft = localStorage.getItem(draftKey);

    if (isCode) {
      setCodeContent(savedDraft !== null ? savedDraft : (task.template_data || '# Kodingizni shu yerga yozing\n'));
    } else {
      setReportContent(savedDraft !== null ? savedDraft : (task.template_data || ''));
    }
    setSandboxResult(null);
    setFeedback(null);
    setSelectedFile(null);
    setCompareMode(false);
  };

  const currentTask: SimulationTask | undefined = simulation?.tasks?.[currentTaskIndex];
  const isCodeTask = currentTask?.resource_files?.task_type === 'code' || currentTask?.mentor_persona === 'lead_engineer';

  // Auto-save draft whenever codeContent or reportContent changes
  useEffect(() => {
    if (!currentTask) return;
    const draftKey = `tryjob_draft_${simulationSlug}_${currentTask.id}`;
    const textToSave = isCodeTask ? codeContent : reportContent;
    if (textToSave !== undefined && textToSave !== '') {
      localStorage.setItem(draftKey, textToSave);
    }
  }, [codeContent, reportContent, currentTask, isCodeTask, simulationSlug]);

  const handleSelectTask = (index: number) => {
    if (!simulation || !simulation.tasks) return;
    setCurrentTaskIndex(index);
    initTask(simulation.tasks[index]);
    setActiveTab('briefing');
  };

  // Run Code in Sandbox
  const handleRunSandbox = async () => {
    if (!codeContent.trim()) return;
    setRunningSandbox(true);
    try {
      const res = await runPythonSandbox(codeContent);
      setSandboxResult(res);
      setSandboxTab('output');
    } catch (err: any) {
      setSandboxResult({
        success: false,
        output: '',
        error: err.response?.data?.detail || err.message,
        execution_time_ms: 0
      });
      setSandboxTab('output');
    } finally {
      setRunningSandbox(false);
    }
  };

  // Submit Task Solution
  const handleSubmitTask = async () => {
    if (!simulation || !currentTask) return;
    setSubmitting(true);
    try {
      const textToSubmit = isCodeTask ? codeContent : reportContent;
      const res = await submitTaskSolution(simulation.id, currentTask.id, textToSubmit, selectedFile || undefined);
      setFeedback(res);
      
      // Add to completed tasks
      setCompletedTaskIds((prev) => new Set(prev).add(currentTask.id));

      // Trigger celebratory confetti if passed!
      if (res.score >= 70) {
        confetti({
          particleCount: 100,
          spread: 80,
          origin: { y: 0.6 }
        });
      }
    } catch (err: any) {
      alert("Topshirishda xatolik: " + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  // Issue Certificate
  const handleIssueCertificate = async () => {
    if (!simulation) return;
    try {
      const cert = await issueCertificate(simulation.id);
      confetti({
        particleCount: 150,
        spread: 90,
        origin: { y: 0.5 }
      });
      onViewCertificate(cert.cert_uuid);
    } catch (err: any) {
      alert("Sertifikat tayyorlashda xatolik: " + (err.response?.data?.detail || err.message));
    }
  };

  // Infinite Adaptive Mastery: Trigger Level Up Dynamic Anomaly Task
  const handleTriggerDynamicMastery = () => {
    if (!simulation) return;
    setIsGeneratingDynamicTask(true);
    setTimeout(() => {
      const nextLevel = masteryLevel + 1;
      setMasteryLevel(nextLevel);

      const nextOrder = (simulation.tasks?.length || 0) + 1;
      const isCode = isCodeTask || simulation.category?.toLowerCase().includes('fintech') || simulation.category?.toLowerCase().includes('dastur');

      const anomalyTask: SimulationTask = isCode ? {
        id: `task-dynamic-level-${nextLevel}-${Date.now()}`,
        order: nextOrder,
        title: `⚡ Level ${nextLevel} Mastery: High-Load Race Condition & Memory Leak (Anomal Vazifa)`,
        mentor_persona: 'lead_engineer',
        briefing_text: `DIQQAT! Favqulodda vaziyat (P1 Incident)! Oldingi vazifani 100% muvaffaqiyatli yakunladingiz. Hozirda tizimga 100k+ parallel RPS tushmoqda va ma'lumotlar bazasida deadlock hamda xotira to'lishi (Memory Leak) yuzaga keldi. AI Mentor sizga ushbu anomaliyani tezkor bartaraf etish topshirig'ini yuklaydi.`,
        instructions: `1. Quyidagi anomal holatni bartaraf etuvchi, oqimni xavfsiz boshqaruvchi (Thread-safe Rate Limiter va Deadlock himoyasi) kodni yozing.\n2. Sandboxda sinab ko'ring va xotira tozalanishini tekshiring.\n3. AI Mentorga baholash uchun yuboring.`,
        template_data: `# ⚡ LEVEL ${nextLevel} MASTER ANOMAL TOPSHIRIQ\n# Vazifa: Thread-safe Rate Limiter va Deadlock himoyasi\n\nimport time\nimport threading\nfrom collections import deque\n\nclass AdaptiveMasteryEngine:\n    def __init__(self, max_rps: int = 1000):\n        self.max_rps = max_rps\n        self.queue = deque()\n        self.lock = threading.Lock()\n        \n    def process_request(self, user_id: str, payload: dict) -> bool:\n        # TODO: Rate limiter va xotira tozalash logikasini yozing\n        with self.lock:\n            self.queue.append((time.time(), user_id))\n            return True\n\n# Test qilish:\nengine = AdaptiveMasteryEngine()\nprint("✅ Adaptive Engine ishga tushdi: Level ${nextLevel}")\n`,
        model_answer: `import time\nimport threading\nfrom collections import deque\n\nclass AdaptiveMasteryEngine:\n    def __init__(self, max_rps: int = 1000):\n        self.max_rps = max_rps\n        self.queue = deque()\n        self.lock = threading.Lock()\n        \n    def process_request(self, user_id: str, payload: dict) -> bool:\n        now = time.time()\n        with self.lock:\n            while self.queue and self.queue[0][0] < now - 1.0:\n                self.queue.popleft()\n            if len(self.queue) >= self.max_rps:\n                return False\n            self.queue.append((now, user_id))\n            return True\n\nengine = AdaptiveMasteryEngine()\nprint("✅ Level ${nextLevel} Senior Anomaly Fixed!")\n`,
        rubric_criteria: [
          { criterion: `Level ${nextLevel} Anomaliya va Race condition bartaraf etilganligi`, max_score: 30 },
          { criterion: 'Xotira boshqaruvi va Resurslarni tozalash (Memory cleanup)', max_score: 25 },
          { criterion: 'High-load stress testga chidamlilik', max_score: 25 },
          { criterion: 'Korporativ Clean Code va Thread Safety', max_score: 20 }
        ],
        resource_files: {
          task_type: 'code',
          supervisor: {
            name: 'Sherzod Qodirov',
            role: 'Chief Technology Officer (CTO)',
            department: 'Incident Response & Infrastructure',
            avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&h=120&fit=crop',
            audio_duration: '01:10'
          },
          audio_transcript: `Bu Sherzod. Avvalgi topshiriqni juda a'lo bajarganingiz uchun rahbariyat nomidan ushbu Level ${nextLevel} favqulodda anomaliya vazifasini sizga yuklaymiz. Omad!`,
          corporate_context: `Level ${nextLevel} bosqichida xatolar xarajati yuqori. Tizim to'xtovsiz ishlashi shart.`,
          deliverables: ['AdaptiveMasteryEngine klassi', 'Stress test loglari'],
          dataset: {
            title: `Level ${nextLevel} Crash Telemetriya Loglari`,
            headers: ['Timestamp', 'Error_Code', 'Active_Threads', 'CPU_Usage_%', 'Status'],
            rows: [
              ['14:30:01.002', 'ERR_DEADLOCK_0x4F', '1240', '99.4%', 'CRITICAL'],
              ['14:30:01.045', 'ERR_OOM_BUFFER', '1420', '98.8%', 'CRITICAL'],
              ['14:30:01.090', 'ERR_TIMEOUT_GATEWAY', '1500', '100%', 'DOWN']
            ]
          },
          downloads: [
            { name: `telemetry_dump_level_${nextLevel}.log`, size: '840 KB', type: 'LOG' }
          ],
          model_explanation: `Level ${nextLevel} yechimi oqimlararo qulflash (Lock) va o'tgan so'rovlarni xotiradan tozalash (sliding-window) orqali kesh to'lishining oldini oladi.`
        }
      } : {
        id: `task-dynamic-level-${nextLevel}-${Date.now()}`,
        order: nextOrder,
        title: `⚡ Level ${nextLevel} Mastery: Favqulodda Korporativ Audit va Soliq Riski (Anomal Vazifa)`,
        mentor_persona: 'audit_manager',
        briefing_text: `DIQQAT! Kutilmagan favqulodda audit tekshiruvi! Avvalgi hisobotni a'lo topshirdingiz, biroq xalqaro inspektsiya kompaniyaga 12 milliard so'mlik da'vo kiritdi. Sizdan favqulodda Audit himoyasi va Risk hisobotini tuzish talab etiladi.`,
        instructions: `1. Quyidagi kutilmagan sanksiyaviy va transfer bahosi (Transfer Pricing) da'volarini tahlil qiling.\n2. Kompaniya manfaatlarini himoya qiluvchi Favqulodda Audit Memorandumini yozing.\n3. Moliyaviy zaxira miqdorini hisoblang.`,
        template_data: `FAVQULODDA AUDIT MEMORANDUMI (LEVEL ${nextLevel})\n\nKIMGA: Boshqaruv Kengashi va Bosh Direktor\nKIMDAN: Lead Audit & Risk Expert\nMAVZU: 12 Mlrd so'mlik Da'vo bo'yicha Favqulodda Audit Xulosasi\n\n1. ANOMAL RISK VA DA'VOLAR TAHLILI:\n...\n\n2. HUQUQIY VA MOLIYAVIY HIMOYA STRATEGIYASI:\n...\n\n3. KOMPANIYA UCHUN XATARNI KAMAYTIRISH CHORALARI:\n...`,
        model_answer: `FAVQULODDA AUDIT MEMORANDUMI (LEVEL ${nextLevel})\n\nKIMGA: Boshqaruv Kengashiga\nKIMDAN: Senior Audit Associate\nMAVZU: Xalqaro Da'vo yuzasidan audit xulosasi\n\n1. ASOSIY XULOSA:\nDa'vodagi 12 mlrd so'mlik xatarning 8.4 mlrd so'mi ikki tomonlama soliqqa tortish to'g'risidagi xalqaro konvensiya (DTA) asosida asossiz deb topildi.\n\n2. TAVSIYA:\nZudlik bilan xalqaro arbitraj memorandumini taqdim etish va hisoblangan zaxirani balansda aks ettirish tavsiya etiladi.`,
        rubric_criteria: [
          { criterion: `Level ${nextLevel} Soliq va Audit qonunchiligining chuqur tahlili`, max_score: 30 },
          { criterion: 'Kompaniya xatarlarini kamaytirish dalillari', max_score: 25 },
          { criterion: 'Xulosa va tavsiyalar asoslanganligi', max_score: 25 },
          { criterion: 'Korporativ hisobot strukturasi va tili', max_score: 20 }
        ],
        resource_files: {
          task_type: 'report',
          supervisor: {
            name: 'Nodira Qosimova',
            role: 'Audit Partner & Risk Lead',
            department: 'Emergency Assurance Team',
            avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=120&h=120&fit=crop',
            audio_duration: '01:20'
          },
          audio_transcript: `Assalomu alaykum. Bizda kutilmagan vaziyat yuzaga keldi. Oldingi hisobotingiz juda a'lo bo'lgani uchun ushbu Level ${nextLevel} keysni sizga ishonib topshiryapmiz!`,
          corporate_context: 'Favqulodda vaziyatlarda tezkor va huquqiy asoslangan qaror qabul qilish talab etiladi.',
          deliverables: ['Favqulodda Audit Memorandumi', 'Risk tahlili jadvali'],
          dataset: {
            title: `Level ${nextLevel} Da'vo va Sanksiya Moddalari`,
            headers: ['Modda_ID', 'Da\'vo_Predmeti', 'Summa_UZS', 'Xatar_Ehtimoli_%'],
            rows: [
              ['ART_901', 'Transfer narxlarini shakllantirish', '7,500,000,000', '85%'],
              ['ART_902', 'Bojxona imtiyozlari qayta ko\'rib chiqilishi', '4,500,000,000', '60%']
            ]
          },
          downloads: [
            { name: `legal_audit_claim_level_${nextLevel}.pdf`, size: '1.4 MB', type: 'PDF' }
          ],
          model_explanation: `Level ${nextLevel} xulosasi xalqaro arbitraj amaliyotiga to'liq mos keladi.`
        }
      };

      const updatedTasks = [...(simulation.tasks || []), anomalyTask];
      setSimulation({
        ...simulation,
        tasks: updatedTasks
      });

      const newIdx = updatedTasks.length - 1;
      setCurrentTaskIndex(newIdx);
      initTask(anomalyTask);
      setActiveTab('briefing');
      setIsGeneratingDynamicTask(false);
      setDynamicTaskAlert(`⚡ LEVEL ${nextLevel} MAHORAT BOSQICHI ISHGA TUSHDI! Siz uchun qiyinlashtirilgan anomal vazifa tayyorlandi.`);

      confetti({
        particleCount: 140,
        spread: 100,
        origin: { y: 0.4 }
      });

      setTimeout(() => {
        setDynamicTaskAlert(null);
      }, 5000);
    }, 1200);
  };

  // Download Sample File
  const handleDownloadFile = (filename: string) => {
    const blob = new Blob([
      `TryJob Korporativ Resurs: ${filename}\nSana: 2026-10-05\nKompaniya: ${simulation?.company.name || 'TryJob Partner'}\nSimulyatsiya: ${simulation?.title}\nHolat: Rasmiy o'quv modeli.`
    ], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  // Export CSV
  const handleExportCSV = () => {
    const dataset = currentTask?.resource_files?.dataset;
    if (!dataset) return;
    const csvContent = [
      dataset.headers.join(','),
      ...dataset.rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dataset.title || 'dataset'}.csv`;
    a.click();
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Simulyatsiya ish stoli yuklanmoqda...</p>
      </div>
    );
  }

  if (!simulation || !currentTask) {
    return (
      <div className="max-w-md mx-auto py-20 text-center space-y-4">
        <p className="text-slate-400 text-sm">Simulyatsiya topilmadi.</p>
        <button onClick={onBack} className="bg-cyan-500 text-slate-950 font-bold px-6 py-2.5 rounded-xl text-xs">
          Katalogga qaytish
        </button>
      </div>
    );
  }

  const resMeta = currentTask.resource_files || {};
  const supervisor = resMeta.supervisor;
  const dataset = resMeta.dataset;
  const downloads = resMeta.downloads || [];
  const deliverables = resMeta.deliverables || [];

  const wordCount = reportContent.trim().length > 0 ? reportContent.trim().split(/\s+/).length : 0;
  const charCount = reportContent.length;
  const estimatedReadTime = Math.max(1, Math.ceil(wordCount / 180));
  const allTasksDone = simulation.tasks && completedTaskIds.size === simulation.tasks.length;

  return (
    <div className="pb-16 space-y-6">
      
      {/* Workspace Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur sticky top-0 z-30 py-3.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition cursor-pointer"
              title="Katalogga qaytish"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <img
                src={simulation.company?.logo_url || 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=80&q=80'}
                alt="Logo"
                className="w-10 h-10 rounded-xl object-cover border border-slate-700 shrink-0 shadow"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-extrabold text-cyan-400 uppercase tracking-wider">
                    {simulation.company?.name}
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    VERIFIED PARTNER
                  </span>
                </div>
                <h1 className="text-sm sm:text-base font-extrabold text-white leading-tight truncate max-w-md md:max-w-xl">
                  {simulation.title}
                </h1>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700">
              <Clock className="w-3.5 h-3.5 text-cyan-400" /> ~{simulation.estimated_hours} soat
            </div>
            
            <button
              onClick={onOpenInterview}
              className="bg-gradient-to-r from-indigo-600/20 to-purple-600/20 hover:from-indigo-600/30 hover:to-purple-600/30 text-indigo-300 border border-indigo-500/30 font-bold px-3 py-1.5 rounded-xl text-xs flex items-center gap-1.5 transition cursor-pointer shadow-sm"
            >
              <Mic className="w-3.5 h-3.5 text-indigo-400" /> <span className="hidden sm:inline">AI Mock</span> Interview
            </button>

            <button
              onClick={onOpenDocAudit}
              className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold px-3 py-1.5 rounded-xl text-xs flex items-center gap-1.5 transition cursor-pointer"
            >
              <FileCheck className="w-3.5 h-3.5 text-emerald-400" /> <span className="hidden sm:inline">EHF</span> Audit
            </button>
          </div>
        </div>
      </header>

      {/* Dynamic Task Alert Notification */}
      {dynamicTaskAlert && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="bg-gradient-to-r from-amber-500/20 via-orange-500/20 to-rose-500/20 border border-amber-500/40 rounded-2xl p-4 flex items-center justify-between shadow-2xl animate-in slide-in-from-top duration-300">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-amber-400 text-slate-950 flex items-center justify-center font-black shrink-0">
                <Zap className="w-4 h-4 fill-slate-950" />
              </div>
              <span className="text-xs sm:text-sm font-bold text-amber-300">
                {dynamicTaskAlert}
              </span>
            </div>
            <button
              onClick={() => setDynamicTaskAlert(null)}
              className="text-slate-400 hover:text-white p-1"
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Grid Layout */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Sidebar */}
        <aside className="lg:col-span-4 space-y-5">
          
          {/* Adaptive Mastery Level Widget */}
          <div className="bg-gradient-to-br from-amber-500/15 via-slate-900 to-cyan-900/20 border border-amber-500/40 rounded-3xl p-5 shadow-xl space-y-3 relative overflow-hidden">
            <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-amber-500/10 rounded-full blur-xl pointer-events-none" />
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400 fill-amber-400" />
                <span className="text-xs font-black text-amber-400 uppercase tracking-wider">Adaptive Mastery</span>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/40">
                Level {masteryLevel} &bull; {masteryLevel === 1 ? 'Novice' : masteryLevel === 2 ? 'Senior Pro' : masteryLevel === 3 ? 'Lead Master' : 'Architect'}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Dinamik cheksiz rejimda har bir bosqich avtomatik tarzda yanada qiyinlashgan favqulodda keyslar (P1 anomaliya, yuqori yuklama) bilan kengayadi.
            </p>
            <button
              onClick={handleTriggerDynamicMastery}
              disabled={isGeneratingDynamicTask}
              className="w-full bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 disabled:opacity-50 text-slate-950 font-black py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-amber-400/20 cursor-pointer"
            >
              {isGeneratingDynamicTask ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 fill-slate-950" />}
              {isGeneratingDynamicTask ? 'Anomal Keys Tayyorlanmoqda...' : '⚡ Keyingi Qiyinroq Bosqich (Level Up)'}
            </button>
          </div>

          {/* Tasks Navigation */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider">Bosqichlar Xaritasi</h2>
              <span className="text-xs font-bold text-cyan-400">
                {completedTaskIds.size} / {simulation.tasks?.length} yakunlandi
              </span>
            </div>

            {/* Overall Progress Bar */}
            <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                className="bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-400 h-full transition-all duration-500"
                style={{
                  width: `${simulation.tasks?.length ? (completedTaskIds.size / simulation.tasks.length) * 100 : 0}%`
                }}
              />
            </div>

            <div className="space-y-2">
              {simulation.tasks?.map((task, idx) => {
                const isSelected = idx === currentTaskIndex;
                const isCompleted = completedTaskIds.has(task.id);
                return (
                  <button
                    key={task.id}
                    onClick={() => handleSelectTask(idx)}
                    className={`w-full text-left p-3.5 rounded-2xl border transition flex items-start gap-3 cursor-pointer ${
                      isSelected
                        ? 'bg-slate-800/90 border-cyan-500/60 shadow-lg shadow-cyan-500/10'
                        : 'border-slate-800/80 hover:border-cyan-500/40 hover:bg-slate-800/50'
                    }`}
                  >
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${
                        isCompleted
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                          : isSelected
                          ? 'bg-cyan-500 text-slate-950 font-black'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {isCompleted ? <Check className="w-3.5 h-3.5" /> : task.order}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs sm:text-sm font-bold text-white truncate">{task.title}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                        <span className="truncate">{task.mentor_persona}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Certificate Trigger Button */}
            <div className="pt-4 border-t border-slate-800/80">
              <button
                onClick={handleIssueCertificate}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black py-3 rounded-2xl shadow-lg shadow-emerald-500/20 transition flex items-center justify-center gap-2 text-xs cursor-pointer"
              >
                <Award className="w-4 h-4" /> Rasmiy Sertifikatni Olish
              </button>
              <p className="text-[10px] text-slate-500 text-center mt-2 font-medium">
                {allTasksDone ? 'Barcha bosqichlar tayyor!' : 'Barcha topshiriqlar topshirilgach sertifikat tasdiqlanadi'}
              </p>
            </div>
          </div>

          {/* Corporate Starter Pack / Downloads */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 space-y-3">
            <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Download className="w-4 h-4 text-cyan-400" /> Ishchi Resurslar To'plami
            </h3>
            <p className="text-[11px] text-slate-400">Ushbu vazifada ishlatiladigan rasmiy korporativ fayllar:</p>

            <div className="space-y-2">
              {downloads.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs hover:border-slate-700 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
                    <div>
                      <div className="font-bold text-slate-200 truncate max-w-[170px]">{item.name}</div>
                      <div className="text-[10px] text-slate-500">{item.type} &bull; {item.size}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadFile(item.name)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 transition cursor-pointer"
                    title="Yuklab olish"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {downloads.length === 0 && (
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-cyan-400" />
                    <span className="font-bold text-slate-200">vazifa_qollanmasi.pdf</span>
                  </div>
                  <button onClick={() => handleDownloadFile('vazifa_qollanmasi.pdf')} className="p-1.5 rounded-lg bg-slate-800 text-cyan-400">
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Quick Tools */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 space-y-2.5">
            <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider">Tezkor Vositalar</h3>
            <button
              onClick={onOpenDocAudit}
              className="w-full text-left p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-300 flex items-center justify-between transition cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-emerald-400" /> Didox / EHF Hujjat Tekshirgich
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
            </button>
            <button
              onClick={onOpenInterview}
              className="w-full text-left p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-300 flex items-center justify-between transition cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-indigo-400" /> AI Mock Intervyu Simulyatori
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
            </button>
          </div>

        </aside>

        {/* Right Main Content (4 Tabs) */}
        <main className="lg:col-span-8 space-y-6">
          
          {/* Tab Navigation */}
          <div className="flex items-center gap-1.5 sm:gap-2 bg-slate-900/90 p-1.5 rounded-2xl border border-slate-800 shadow-xl overflow-x-auto">
            <button
              onClick={() => setActiveTab('briefing')}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
                activeTab === 'briefing'
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <PlayCircle className="w-3.5 h-3.5" /> 1. Brifing & Audio
            </button>
            <button
              onClick={() => setActiveTab('data')}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
                activeTab === 'data'
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Table className="w-3.5 h-3.5" /> 2. Jonli Ma'lumotlar
            </button>
            <button
              onClick={() => setActiveTab('workspace')}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
                activeTab === 'workspace'
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Edit3 className="w-3.5 h-3.5" /> 3. Yechim Maydoni (IDE)
            </button>
            <button
              onClick={() => setActiveTab('model')}
              className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shrink-0 cursor-pointer ${
                activeTab === 'model'
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <CheckCheck className="w-3.5 h-3.5" /> 4. Senior Yechimi
            </button>
          </div>

          {/* TAB 1: Brifing & Audio Player */}
          {activeTab === 'briefing' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              
              {/* Supervisor Profile & Voiceover */}
              <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
                  <div className="flex items-center gap-3.5">
                    <img
                      src={supervisor?.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&q=80'}
                      alt={supervisor?.name || 'Supervisor'}
                      className="w-12 h-12 rounded-2xl object-cover border-2 border-cyan-500/40 shadow-md"
                    />
                    <div>
                      <h4 className="text-sm font-extrabold text-white">{supervisor?.name || 'Alexandre Dubois'}</h4>
                      <p className="text-xs text-slate-400">{supervisor?.role || 'Managing Director'} &bull; {supervisor?.department || 'Quantitative Technology'}</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-extrabold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 self-start sm:self-auto">
                    RASMIY BRIFING
                  </span>
                </div>

                {/* Equalizer Audio Player */}
                <AudioWaveformPlayer
                  supervisorName={supervisor?.name}
                  duration={supervisor?.audio_duration || '01:45'}
                  transcript={resMeta.audio_transcript}
                />
              </div>

              {/* Task Title & Scenario */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-slate-800 text-cyan-400 border border-slate-700">
                    Bosqich #{currentTask.order}
                  </span>
                  <span className="text-xs text-slate-400">AI Mentor: <strong className="text-slate-200">{currentTask.mentor_persona}</strong></span>
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-white leading-snug">
                  {currentTask.title}
                </h2>
                <div className="bg-slate-950/80 border border-slate-800/90 rounded-2xl p-5 text-slate-200 text-xs sm:text-sm leading-relaxed">
                  {currentTask.briefing_text}
                </div>
              </div>

              {/* Corporate Context */}
              {resMeta.corporate_context && (
                <div className="bg-gradient-to-r from-cyan-950/30 to-blue-950/30 border border-cyan-800/40 rounded-2xl p-4 text-xs text-slate-300 flex items-start gap-3">
                  <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-cyan-300">Korporativ Kontekst: </span>
                    {resMeta.corporate_context}
                  </div>
                </div>
              )}

              {/* Action Plan / Instructions */}
              <div>
                <h3 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400" /> Qadam-baqadam Harakatlar Rejasi:
                </h3>
                <div className="text-slate-300 text-xs sm:text-sm leading-relaxed whitespace-pre-line bg-slate-950/50 border border-slate-800/80 p-5 rounded-2xl font-sans">
                  {currentTask.instructions}
                </div>
              </div>

              {/* Deliverables */}
              <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-5 space-y-3">
                <h4 className="text-xs font-extrabold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Sizdan Kutilayotgan Natijalar (Deliverables):
                </h4>
                <div className="grid sm:grid-cols-2 gap-2.5">
                  {deliverables.map((deliv, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
                      <span>{deliv}</span>
                    </div>
                  ))}
                  {deliverables.length === 0 && (
                    <div className="text-xs text-slate-400">Vazifa talablariga to'liq mos yechimni tayyorlash</div>
                  )}
                </div>
              </div>

              {/* CTA to Workspace */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setActiveTab('workspace')}
                  className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black px-7 py-3 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition cursor-pointer"
                >
                  Yechim Maydoniga O'tish <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: Jonli Ma'lumotlar (Live Dataset) */}
          {activeTab === 'data' && (
            <InteractiveDataTable
              dataset={dataset}
              onExportCSV={handleExportCSV}
            />
          )}

          {/* TAB 3: Yechim & Topshirish (Workspace IDE) */}
          {activeTab === 'workspace' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              
              {/* Header & Mode info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                <div>
                  <label className="text-xs font-extrabold text-slate-300 uppercase tracking-wider block">
                    {isCodeTask ? 'Python Code Sandbox & Terminal:' : 'Tahliliy Hisobot va Xulosa Redaktori:'}
                  </label>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {isCodeTask 
                      ? 'Kodingizni yozing, Sandbox orqali sinab ko\'ring va AI Mentor baholashi uchun topshiring' 
                      : 'Markdown formatida professional korporativ xulosa tayyorlang'}
                  </p>
                </div>

                {isCodeTask ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCodeContent(currentTask.template_data || '# Boshlang\'ich shablon\n')}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold flex items-center gap-1.5 border border-slate-700 transition cursor-pointer"
                      title="Shablonga qaytarish"
                    >
                      <RotateCcw className="w-3.5 h-3.5 text-slate-400" /> Shablon
                    </button>
                    <button
                      onClick={handleRunSandbox}
                      disabled={runningSandbox}
                      className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 disabled:opacity-50 text-slate-950 font-black text-xs px-4 py-1.5 rounded-xl flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 transition cursor-pointer"
                    >
                      {runningSandbox ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                      Kodni Sinash
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                    <button
                      onClick={() => setReportViewMode('edit')}
                      className={`px-3 py-1 rounded-lg font-bold transition cursor-pointer ${
                        reportViewMode === 'edit' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Edit3 className="w-3 h-3 inline mr-1" /> Tahrirlash
                    </button>
                    <button
                      onClick={() => setReportViewMode('split')}
                      className={`px-3 py-1 rounded-lg font-bold transition cursor-pointer ${
                        reportViewMode === 'split' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Columns className="w-3 h-3 inline mr-1" /> Split View
                    </button>
                    <button
                      onClick={() => setReportViewMode('preview')}
                      className={`px-3 py-1 rounded-lg font-bold transition cursor-pointer ${
                        reportViewMode === 'preview' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Eye className="w-3 h-3 inline mr-1" /> Ko'rish
                    </button>
                  </div>
                )}
              </div>

              {/* Code Editor vs Markdown Report Workspace */}
              {isCodeTask ? (
                <div className="space-y-4">
                  {/* Code Editor IDE Container */}
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                    {/* IDE Top Bar */}
                    <div className="bg-slate-900/90 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1.5">
                          <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                          <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                          <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                        </div>
                        <span className="text-slate-400 text-[11px] ml-2 font-sans font-semibold">
                          solution.py &bull; Python 3.11 Runtime
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-slate-500 text-[11px]">
                        <span>UTF-8</span>
                        <span>{codeContent.split('\n').length} qator</span>
                      </div>
                    </div>

                    {/* Textarea with Code Gutter */}
                    <div className="relative flex font-mono text-xs sm:text-sm">
                      <textarea
                        rows={14}
                        value={codeContent}
                        onChange={(e) => setCodeContent(e.target.value)}
                        placeholder="# Python kodingizni shu yerga yozing..."
                        className="w-full bg-slate-950 p-4 text-cyan-300 font-mono text-xs sm:text-sm leading-relaxed focus:outline-none resize-y selection:bg-cyan-500/30"
                        spellCheck={false}
                      />
                    </div>
                  </div>

                  {/* Sandbox Terminal Window */}
                  {sandboxResult && (
                    <div className="bg-black border border-slate-800 rounded-2xl overflow-hidden font-mono text-xs shadow-2xl animate-in fade-in duration-200">
                      <div className="bg-slate-900/90 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                          <span className="text-slate-300 font-bold text-[11px]">Python Sandbox Terminal</span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                            sandboxResult.success ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                          }`}>
                            {sandboxResult.success ? 'EXIT CODE 0 (OK)' : 'ERROR (NON-ZERO)'}
                          </span>
                        </div>
                        <span className="text-cyan-400 text-[10px] font-bold">
                          ⚡ {sandboxResult.execution_time_ms.toFixed(1)} ms
                        </span>
                      </div>

                      <div className="p-4 max-h-60 overflow-y-auto">
                        <pre className={`whitespace-pre-wrap leading-relaxed ${
                          sandboxResult.success ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          {sandboxResult.success 
                            ? (sandboxResult.output || 'Dastur hech qanday xatosiz ishga tushdi va yakunlandi.') 
                            : `Xatolik yuz berdi:\n${sandboxResult.error || ''}\n${sandboxResult.output || ''}`}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Report / Document Editor */
                <div className="space-y-4">
                  {/* Markdown Toolbar */}
                  {reportViewMode !== 'preview' && (
                    <div className="flex flex-wrap items-center gap-1 bg-slate-950 p-2 rounded-xl border border-slate-800 text-xs">
                      <button
                        onClick={() => setReportContent(prev => prev + '\n**Qalin matn**\n')}
                        className="px-2.5 py-1 rounded-lg hover:bg-slate-800 text-slate-300 font-bold cursor-pointer"
                        title="Qalin (Bold)"
                      >
                        B
                      </button>
                      <button
                        onClick={() => setReportContent(prev => prev + '\n*Qiya matn*\n')}
                        className="px-2.5 py-1 rounded-lg hover:bg-slate-800 text-slate-300 italic cursor-pointer"
                        title="Kursiv (Italic)"
                      >
                        I
                      </button>
                      <span className="w-px h-4 bg-slate-800 mx-1" />
                      <button
                        onClick={() => setReportContent(prev => prev + '\n# Bosh Sarlavha\n')}
                        className="px-2 py-1 rounded-lg hover:bg-slate-800 text-slate-300 font-black cursor-pointer"
                      >
                        H1
                      </button>
                      <button
                        onClick={() => setReportContent(prev => prev + '\n## Kichik Sarlavha\n')}
                        className="px-2 py-1 rounded-lg hover:bg-slate-800 text-slate-300 font-bold cursor-pointer"
                      >
                        H2
                      </button>
                      <button
                        onClick={() => setReportContent(prev => prev + '\n### Bo\'lim Sarlavhasi\n')}
                        className="px-2 py-1 rounded-lg hover:bg-slate-800 text-slate-300 font-semibold cursor-pointer"
                      >
                        H3
                      </button>
                      <span className="w-px h-4 bg-slate-800 mx-1" />
                      <button
                        onClick={() => setReportContent(prev => prev + '\n- Ro\'yxat elementi 1\n- Ro\'yxat elementi 2\n')}
                        className="px-2.5 py-1 rounded-lg hover:bg-slate-800 text-slate-300 cursor-pointer"
                        title="Ro'yxat (List)"
                      >
                        • List
                      </button>
                      <button
                        onClick={() => setReportContent(prev => prev + '\n> Korporativ tavsiya yoki iqtibos\n')}
                        className="px-2.5 py-1 rounded-lg hover:bg-slate-800 text-slate-300 cursor-pointer"
                        title="Iqtibos (Quote)"
                      >
                        " Quote
                      </button>
                      <button
                        onClick={() => setReportContent(prev => prev + '\n```python\n# Kod namunasi\n```\n')}
                        className="px-2.5 py-1 rounded-lg hover:bg-slate-800 text-slate-300 font-mono cursor-pointer"
                        title="Kod bloki"
                      >
                        &lt;/&gt;
                      </button>

                      {/* Stats pill */}
                      <div className="ml-auto flex items-center gap-3 text-[11px] text-slate-500 pr-2">
                        <span><strong>{wordCount}</strong> so'z</span>
                        <span>{charCount} belgi</span>
                        <span>~{estimatedReadTime} daqiqa o'qish</span>
                      </div>
                    </div>
                  )}

                  {/* Editor / Split / Preview View Modes */}
                  {reportViewMode === 'edit' && (
                    <textarea
                      rows={12}
                      value={reportContent}
                      onChange={(e) => setReportContent(e.target.value)}
                      placeholder="Hisobotingiz, tahliliy xulosangiz yoki strategik takliflaringizni shu yerga yozing..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-xs sm:text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-sans leading-relaxed shadow-inner"
                    />
                  )}

                  {reportViewMode === 'split' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <textarea
                        rows={14}
                        value={reportContent}
                        onChange={(e) => setReportContent(e.target.value)}
                        placeholder="Hisobotingizni yozing..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans leading-relaxed"
                      />
                      <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 overflow-y-auto max-h-[350px]">
                        <div className="text-[10px] uppercase font-bold text-slate-500 mb-2 border-b border-slate-800 pb-1">
                          Jonli Formatlangan Ko'rinish:
                        </div>
                        <MarkdownPreview content={reportContent} />
                      </div>
                    </div>
                  )}

                  {reportViewMode === 'preview' && (
                    <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 min-h-[250px] shadow-inner">
                      <MarkdownPreview content={reportContent} />
                    </div>
                  )}
                </div>
              )}

              {/* File Attachment & Submission Section */}
              <div className="pt-4 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <label className="cursor-pointer bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 border border-slate-700 transition shadow">
                    <Paperclip className="w-4 h-4 text-cyan-400" /> Fayl biriktirish (.xlsx, .docx, .pdf)
                    <input
                      type="file"
                      className="hidden"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    />
                  </label>
                  {selectedFile && (
                    <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs text-slate-300">
                      <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="truncate max-w-[160px] font-mono">{selectedFile.name}</span>
                      <button
                        onClick={() => setSelectedFile(null)}
                        className="text-slate-500 hover:text-rose-400 text-xs ml-1"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                  {!selectedFile && (
                    <span className="text-xs text-slate-500 hidden sm:inline">Ixtiyoriy hujjat fayli</span>
                  )}
                </div>

                <button
                  onClick={handleSubmitTask}
                  disabled={submitting}
                  className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-black px-8 py-3 rounded-xl shadow-lg shadow-cyan-500/25 transition flex items-center justify-center gap-2 text-xs cursor-pointer"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 fill-slate-950" />}
                  {submitting ? 'AI Mentor Tahlil Qilmoqda...' : 'AI Mentordan Baho Olish'}
                </button>
              </div>

              {/* AI Mentor Review Feedback Card */}
              {feedback && (
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl mt-6 animate-in fade-in slide-in-from-bottom-3 duration-300">
                  
                  {/* Feedback Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
                    <div className="flex items-center gap-3.5">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center font-bold shadow">
                        <Bot className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-extrabold text-white">
                            {feedback.ai_feedback?.mentor_name || 'AI Mentor'}
                          </h3>
                          <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                            RASMIY TAQRIZ
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {feedback.ai_feedback?.mentor_role || 'Senior Mutaxassis va Auditor'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center sm:flex-col sm:items-end justify-between gap-2">
                      <div className="text-3xl sm:text-4xl font-black text-cyan-400">
                        {Math.round(feedback.score)}<span className="text-lg text-slate-500 font-bold">/100</span>
                      </div>
                      <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${
                        feedback.score >= 70 
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' 
                          : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      }`}>
                        {feedback.score >= 70 ? '✓ Muvaffaqiyatli O\'tdi' : '⚠ Qayta ko\'rib chiqish tavsiya etiladi'}
                      </span>
                    </div>
                  </div>

                  {/* Rubric Breakdown (4 Criteria) */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <SlidersHorizontal className="w-4 h-4 text-cyan-400" /> Mezonlar Bo'yicha Progress & Ballar:
                    </h4>
                    
                    <div className="grid sm:grid-cols-2 gap-3">
                      {(feedback.ai_feedback?.rubric_breakdown || feedback.ai_feedback?.rubric_scores || currentTask.rubric_criteria).map((r: any, i: number) => {
                        const score = r.score ?? Math.round(r.max_score * (feedback.score / 100));
                        const max = r.max_score || 25;
                        const pct = Math.min(100, Math.round((score / max) * 100));
                        const isHigh = pct >= 75;

                        return (
                          <div key={i} className="bg-slate-950 p-4 rounded-2xl border border-slate-800/80 space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-slate-200 font-bold truncate max-w-[200px]">{r.criterion}</span>
                              <span className={`font-mono font-bold ${isHigh ? 'text-emerald-400' : 'text-amber-400'}`}>
                                {score} / {max} ball ({pct}%)
                              </span>
                            </div>
                            
                            <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                              <div
                                className={`h-full transition-all duration-500 ${
                                  isHigh 
                                    ? 'bg-gradient-to-r from-cyan-500 to-emerald-400' 
                                    : 'bg-gradient-to-r from-amber-500 to-orange-500'
                                }`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            {r.comment && (
                              <p className="text-[11px] text-slate-400 italic pt-1">{r.comment}</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Strengths and Mistakes Grid */}
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-2xl p-5 space-y-3">
                      <h4 className="text-xs font-extrabold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" /> Kuchli Tomonlar (Strengths):
                      </h4>
                      <ul className="text-xs text-slate-300 space-y-2">
                        {feedback.ai_feedback?.strengths?.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-emerald-400 font-bold mt-0.5">✓</span>
                            <span>{s}</span>
                          </li>
                        ))}
                        {(!feedback.ai_feedback?.strengths || feedback.ai_feedback.strengths.length === 0) && (
                          <li className="text-slate-400">Yechim strukturasi va maqsadga erishish uslubi yaxshi shakllantirilgan.</li>
                        )}
                      </ul>
                    </div>

                    <div className="bg-amber-950/20 border border-amber-800/40 rounded-2xl p-5 space-y-3">
                      <h4 className="text-xs font-extrabold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4" /> Xatoliklar & Takliflar (Mistakes):
                      </h4>
                      <ul className="text-xs text-slate-300 space-y-2">
                        {feedback.ai_feedback?.mistakes?.map((m, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-amber-400 font-bold mt-0.5">⚠</span>
                            <span>{m}</span>
                          </li>
                        ))}
                        {(!feedback.ai_feedback?.mistakes || feedback.ai_feedback.mistakes.length === 0) && (
                          <li className="text-slate-400">Resurslar sarfi va chegaraviy holatlarni qayta ko'rib chiqish tavsiya etiladi.</li>
                        )}
                      </ul>
                    </div>
                  </div>

                  {/* Corporate Best Practices Recommendation */}
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl p-5 space-y-2">
                    <h4 className="text-xs font-extrabold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Lightbulb className="w-4 h-4 text-indigo-400" /> Korporativ Standart Maslahati (Best Practice):
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {feedback.ai_feedback?.best_practices || 'Kompaniya yetakchi muhandislari bunday holatlarda sliding-window algoritmlari va xatarlarni kamaytirish bo\'yicha memorandum tuzishni standart amaliyot deb bilishadi.'}
                    </p>
                  </div>

                  {/* Infinite Adaptive Mastery Level Up Section */}
                  {feedback.score >= 70 && (
                    <div className="bg-gradient-to-r from-amber-500/15 via-orange-500/15 to-purple-500/15 border border-amber-500/40 rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
                      <div className="flex items-center gap-3.5">
                        <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-slate-950 flex items-center justify-center font-black shadow-lg shadow-amber-500/25 shrink-0">
                          <Zap className="w-5 h-5 fill-slate-950" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-black text-amber-300 uppercase tracking-wider">
                              Dinamik Cheksiz Rejim (Infinite Adaptive Mastery)
                            </h4>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/40">
                              Level {masteryLevel} &bull; {masteryLevel === 1 ? 'Novice' : masteryLevel === 2 ? 'Senior Pro' : masteryLevel === 3 ? 'Lead Master' : 'Architect'}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300 mt-0.5">
                            Keyingi darajadagi kutilmagan favqulodda anomal topshiriqni yuklab, tajribangizni oshiring!
                          </p>
                        </div>
                      </div>

                      <button
                        onClick={handleTriggerDynamicMastery}
                        disabled={isGeneratingDynamicTask}
                        className="bg-gradient-to-r from-amber-400 via-orange-500 to-rose-500 hover:from-amber-300 hover:to-rose-400 text-slate-950 font-black px-5 py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-orange-500/20 transition cursor-pointer shrink-0"
                      >
                        {isGeneratingDynamicTask ? <Loader2 className="w-4 h-4 animate-spin" /> : <Flame className="w-4 h-4 fill-slate-950" />}
                        {isGeneratingDynamicTask ? 'Anomal Topshiriq Yaratilmoqda...' : '⚡ Keyingi Qiyinroq Bosqichga O\'tish (Level Up)'}
                      </button>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
                    <button
                      onClick={() => setActiveTab('model')}
                      className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black px-6 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition cursor-pointer"
                    >
                      Senior Xodim Namunaviy Yechimini Ko'rish <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* TAB 4: Senior Yechimi (Model Answer & Exemplar) */}
          {activeTab === 'model' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
                    <Award className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold text-white">Senior Mutaxassis Namunasi (Model Answer)</h3>
                    <p className="text-xs text-slate-400">Kompaniya yetakchi muhandislari tomonidan tasdiqlangan rasmiy yechim</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCompareMode(!compareMode)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition flex items-center gap-1.5 cursor-pointer ${
                      compareMode 
                        ? 'bg-cyan-500 text-slate-950 border-cyan-400' 
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                    }`}
                  >
                    <Columns className="w-3.5 h-3.5" />
                    {compareMode ? 'Yakka Ko\'rinish' : 'Solishtirish (Diff View)'}
                  </button>

                  <span className="px-3 py-1 rounded-xl text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    EXEMPLAR
                  </span>
                </div>
              </div>

              {/* Compare Mode vs Standard Model Answer */}
              {compareMode ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* User Solution */}
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 pb-2 border-b border-slate-800">
                      <span>Sizning Yechimingiz:</span>
                      <span className="text-[10px] text-cyan-400">{isCodeTask ? 'solution.py' : 'report.md'}</span>
                    </div>
                    <pre className="font-mono text-xs text-slate-300 bg-slate-900/50 p-3 rounded-xl max-h-[360px] overflow-y-auto whitespace-pre-wrap">
                      {isCodeTask ? (codeContent || '# Yechim kiritilmagan') : (reportContent || '# Hisobot kiritilmagan')}
                    </pre>
                  </div>

                  {/* Senior Solution */}
                  <div className="bg-slate-950 border border-emerald-500/30 rounded-2xl p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold text-emerald-400 pb-2 border-b border-slate-800">
                      <span>Senior Xodim Namunasi:</span>
                      <span className="text-[10px] bg-emerald-500/10 px-2 py-0.5 rounded text-emerald-300">IDEAL 100%</span>
                    </div>
                    <pre className="font-mono text-xs text-emerald-400 bg-slate-900/50 p-3 rounded-xl max-h-[360px] overflow-y-auto whitespace-pre-wrap">
                      {currentTask.model_answer || 'Namunaviy yechim mavjud emas'}
                    </pre>
                  </div>
                </div>
              ) : (
                /* Standard Model Answer View */
                <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-5 space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
                    <span>Namunaviy Yechim Matni / Kodi:</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(currentTask.model_answer || '');
                        setCopiedModelAnswer(true);
                        setTimeout(() => setCopiedModelAnswer(false), 2000);
                      }}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px] font-bold cursor-pointer"
                    >
                      {copiedModelAnswer ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedModelAnswer ? 'Nusxalandi' : 'Nusxalash'}
                    </button>
                  </div>
                  <pre className="font-mono text-xs text-emerald-400 bg-slate-950 p-4 rounded-xl border border-slate-800/80 overflow-x-auto whitespace-pre-wrap max-h-[380px]">
                    {currentTask.model_answer || 'Namunaviy yechim mavjud emas'}
                  </pre>
                </div>
              )}

              {/* Expert Explanation */}
              <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Lightbulb className="w-4 h-4 text-amber-400" /> Ekspert Sharhi & Tushuntirish:
                </h4>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {resMeta.model_explanation || 'Ushbu yechim korxona ichki xavfsizlik, xotirani optimallashtirish va tezkorlik talablariga to\'liq muvofiq ishlab chiqilgan.'}
                </p>
              </div>

              {/* Dynamic Level Up Prompt in Model Tab */}
              <div className="bg-gradient-to-r from-cyan-950/40 via-purple-950/40 to-slate-950 border border-cyan-800/40 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-amber-400 shrink-0" />
                  <span className="text-xs text-slate-200 font-medium leading-relaxed">
                    Oddiy keyslarni yakunladingizmi? <b>Dinamik Cheksiz Rejim</b> orqali yanada yuqori darajadagi favqulodda anomaliyalarni yeching!
                  </span>
                </div>
                <button
                  onClick={handleTriggerDynamicMastery}
                  disabled={isGeneratingDynamicTask}
                  className="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-5 py-2.5 rounded-xl text-xs flex items-center gap-2 transition shrink-0 shadow-lg shadow-amber-400/20 cursor-pointer"
                >
                  {isGeneratingDynamicTask ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Flame className="w-3.5 h-3.5" />}
                  ⚡ Keyingi Qiyinroq Bosqichga O'tish
                </button>
              </div>

              {/* Bottom Action Buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                <button
                  onClick={() => handleDownloadFile('model_solution_final.pdf')}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold px-4 py-2.5 rounded-xl border border-slate-700 flex items-center gap-2 transition cursor-pointer"
                >
                  <Download className="w-4 h-4 text-cyan-400" /> To'liq Yechim Faylini Yuklab Olish (.PDF)
                </button>

                <div className="flex items-center gap-2">
                  {currentTaskIndex < (simulation.tasks?.length || 1) - 1 ? (
                    <button
                      onClick={() => handleSelectTask(currentTaskIndex + 1)}
                      className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black px-6 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition cursor-pointer"
                    >
                      Keyingi Bosqichga O'tish <ArrowRight className="w-4 h-4" />
                    </button>
                  ) : (
                    <button
                      onClick={handleIssueCertificate}
                      className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black px-6 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-emerald-500/20 cursor-pointer"
                    >
                      <Award className="w-4 h-4" /> Rasmiy Sertifikatni Olish
                    </button>
                  )}
                </div>
              </div>

            </div>
          )}

        </main>
      </div>

    </div>
  );
};
