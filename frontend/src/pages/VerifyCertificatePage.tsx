import React, { useState, useEffect } from 'react';
import { Award, ShieldCheck, CheckCircle2, Share2, Printer, ArrowLeft, Loader2, QrCode } from 'lucide-react';
import { verifyCertificate } from '../api';

interface VerifyCertificatePageProps {
  certUuid: string;
  onBack: () => void;
}

export const VerifyCertificatePage: React.FC<VerifyCertificatePageProps> = ({ certUuid, onBack }) => {
  const [certData, setCertData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadCert();
  }, [certUuid]);

  const loadCert = async () => {
    setLoading(true);
    try {
      const data = await verifyCertificate(certUuid);
      setCertData(data);
    } catch (err) {
      console.error('Cert verify error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleShareLinkedIn = () => {
    const text = encodeURIComponent(`Men TryJob platformasida ${certData?.company_name || 'JPMorgan'} ning rasmiy ish simulyatsiyasini muvaffaqiyatli yakunladim! Sertifikat ID: ${certUuid}`);
    const url = encodeURIComponent(window.location.href);
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}&summary=${text}`, '_blank');
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sertifikat tekshirilmoqda...</p>
      </div>
    );
  }

  if (!certData || !certData.is_valid) {
    return (
      <div className="max-w-md mx-auto py-20 text-center space-y-4">
        <p className="text-rose-400 text-sm font-bold">Sertifikat topilmadi yoki haqiqiy emas.</p>
        <button onClick={onBack} className="bg-slate-800 text-slate-200 px-6 py-2.5 rounded-xl text-xs font-bold">
          Bosh sahifaga qaytish
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10 space-y-8">
      
      {/* Header Back & Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-slate-400 hover:text-white flex items-center gap-2 text-xs font-bold transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Simulyatsiyalarga Qaytish
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="bg-slate-900 hover:bg-slate-800 text-slate-300 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 border border-slate-800 transition cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" /> Chop Etish
          </button>
          <button
            onClick={handleShareLinkedIn}
            className="bg-[#0A66C2] hover:bg-[#004182] text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-lg shadow-blue-600/20 transition cursor-pointer"
          >
            <Share2 className="w-3.5 h-3.5" /> LinkedIn ga Ulashish
          </button>
        </div>
      </div>

      {/* Official Certificate Card */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 border-2 border-cyan-500/30 rounded-3xl p-8 sm:p-12 space-y-8 shadow-2xl relative overflow-hidden text-center">
        
        {/* Verification Watermark Badge */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-black text-white text-base">
              TJ
            </div>
            <span className="text-xl font-black text-white">Try<span className="text-cyan-400">Job</span></span>
          </div>

          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
            <ShieldCheck className="w-4 h-4" /> RASMIY TASDIQLANGAN SERTIFIKAT
          </div>
        </div>

        {/* Certificate Content */}
        <div className="space-y-4 max-w-2xl mx-auto">
          <div className="text-xs font-extrabold uppercase tracking-widest text-slate-400">
            Malaka va Amaliy Tajriba Sertifikati
          </div>
          <h2 className="text-2xl sm:text-4xl font-black text-white">
            {certData.student_name}
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            ushbu sertifikat egasi quyidagi xalqaro korporativ ish simulyatsiyasini muvaffaqiyatli yakunladi:
          </p>
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 font-extrabold text-base sm:text-lg text-cyan-400">
            {certData.simulation_title}
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto pt-4 border-t border-slate-800 text-left text-xs">
          <div>
            <span className="text-slate-500 font-bold block">Hamkor Kompaniya:</span>
            <span className="text-slate-200 font-bold">{certData.company_name}</span>
          </div>
          <div>
            <span className="text-slate-500 font-bold block">O'rtacha Baho:</span>
            <span className="text-emerald-400 font-black text-sm">{certData.score}%</span>
          </div>
          <div>
            <span className="text-slate-500 font-bold block">Berilgan Sana:</span>
            <span className="text-slate-200 font-bold">{certData.issued_at?.split('T')[0] || '2026-10-05'}</span>
          </div>
          <div>
            <span className="text-slate-500 font-bold block">Sertifikat ID:</span>
            <span className="text-cyan-400 font-mono font-bold truncate block">{certUuid}</span>
          </div>
        </div>

        {/* QR Code and Verification Footer */}
        <div className="pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <div className="w-16 h-16 bg-white rounded-xl p-1.5 flex items-center justify-center shrink-0">
              <QrCode className="w-full h-full text-slate-950" />
            </div>
            <div className="text-left text-[11px] space-y-0.5">
              <div className="font-bold text-slate-200">Raqamli Xavfsizlik Kodi:</div>
              <div className="font-mono text-slate-400 text-[10px] break-all max-w-xs truncate">
                {certData.cert_uuid}-VERIFIED
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 text-right">
            Ushbu sertifikat TryJob platformasi va {certData.company_name} tomonidan rasman tasdiqlangan.
          </div>
        </div>

      </div>

    </div>
  );
};
