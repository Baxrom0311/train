import React, { useState } from 'react';
import { X, Mic, Send, Bot, CheckCircle, Sparkles, Loader2 } from 'lucide-react';
import { submitMockInterview } from '../api';

interface MockInterviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  simulationSlug: string;
}

export const MockInterviewModal: React.FC<MockInterviewModalProps> = ({ isOpen, onClose, simulationSlug }) => {
  const [question] = useState<string>(
    "Ushbu simulyatsiyadagi topshiriqni bajarishda qanday eng murakkab muammoga duch keldingiz va uni STARR metodologiyasi (Situation, Task, Action, Result, Reflection) asosida qanday hal qildingiz?"
  );
  const [answer, setAnswer] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ score: number; feedback: string } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    setLoading(true);
    try {
      const res = await submitMockInterview(simulationSlug, question, answer);
      setFeedback(res);
    } catch (err: any) {
      alert("Xatolik: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-xl w-full space-y-5 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-bold">
              <Mic className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-black text-white">AI Mock Interview Simulator</h3>
              <p className="text-[11px] text-slate-400">STARR Metodologiyasi Bo'yicha Suhbat</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Savol Card */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 space-y-2">
          <div className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
            <Bot className="w-3.5 h-3.5" /> HR / Bo'lim Rahbari Savoli:
          </div>
          <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
            "{question}"
          </p>
        </div>

        {/* Javob Input */}
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Sizning Javobingiz (STARR tuzilmasi):
          </label>
          <textarea
            rows={4}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Situation: Loyihadagi holat...&#10;Task: Oldimga qo'yilgan vazifa...&#10;Action: Ko'rgan amaliy choralarim va bajargan ishim...&#10;Result: Erishilgan amaliy natija..."
            className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3.5 text-xs sm:text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed"
          />
        </div>

        {/* Natija */}
        {feedback && (
          <div className="bg-gradient-to-r from-indigo-950/30 to-purple-950/30 border border-indigo-800/40 rounded-2xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-400" /> STARR Baholash Natijasi:
              </span>
              <span className="text-sm font-black text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
                {feedback.score}%
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
              {feedback.feedback}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-4 py-2.5 rounded-xl text-xs transition">
            Yopish
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !answer.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-black px-6 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Javobni Baholash
          </button>
        </div>
      </div>
    </div>
  );
};
