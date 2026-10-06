import React, { useState } from 'react';
import { X, FileCheck, CheckCircle, AlertTriangle } from 'lucide-react';
import { api } from '../api';

interface DocumentAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocumentAuditModal: React.FC<DocumentAuditModalProps> = ({ isOpen, onClose }) => {
  const [tin, setTin] = useState<string>('305128941');
  const [itemsTotal, setItemsTotal] = useState<number>(20000000);
  const [declaredTotal, setDeclaredTotal] = useState<number>(22400000);
  const [auditResult, setAuditResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleRunAudit = async () => {
    setLoading(true);
    try {
      const res = await api.post('/tools/document-audit', {
        doc_type: 'ehf',
        tin: tin,
        items_total: itemsTotal,
        vat_rate: 0.12,
        declared_total: declaredTotal
      });
      setAuditResult(res.data);
    } catch (err: any) {
      alert("Xatolik: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-xl w-full space-y-5 shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center font-bold">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-black text-white">Didox / EHF Hujjat Tekshirgich</h3>
              <p className="text-[11px] text-slate-400">Elektron Hisob-Faktura va STIR Standartlari</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="space-y-1.5">
            <label className="font-bold text-slate-300">STIR (INN - 9 ta raqam):</label>
            <input
              type="text"
              value={tin}
              onChange={(e) => setTin(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-300">Tovar Summasi (UZS):</label>
            <input
              type="number"
              value={itemsTotal}
              onChange={(e) => setItemsTotal(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="space-y-1.5 sm:col-span-2">
            <label className="font-bold text-slate-300">Jami EHF Summasi (QQS 12% bilan):</label>
            <input
              type="number"
              value={declaredTotal}
              onChange={(e) => setDeclaredTotal(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
        </div>

        {auditResult && (
          <div className={`p-4 rounded-2xl border text-xs space-y-2 ${auditResult.is_compliant ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300' : 'bg-rose-950/20 border-rose-800/40 text-rose-300'}`}>
            <div className="flex items-center gap-2 font-black text-sm">
              {auditResult.is_compliant ? <CheckCircle className="w-5 h-5 text-emerald-400" /> : <AlertTriangle className="w-5 h-5 text-rose-400" />}
              {auditResult.status_summary}
            </div>
            {auditResult.errors?.map((err: string, i: number) => (
              <div key={i} className="text-[11px] text-rose-300">• {err}</div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-4 py-2.5 rounded-xl text-xs transition">
            Yopish
          </button>
          <button
            onClick={handleRunAudit}
            disabled={loading}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black px-6 py-2.5 rounded-xl text-xs transition"
          >
            Auditni Ishga Tushirish
          </button>
        </div>
      </div>
    </div>
  );
};
