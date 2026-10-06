import React from 'react';
import { ShieldCheck, Heart } from 'lucide-react';
import { useLanguage } from '../i18n/LanguageContext';
import { Logo } from './Logo';

export const Footer: React.FC = () => {
  const { t } = useLanguage();

  return (
    <footer className="mt-auto border-t border-slate-800/80 bg-slate-950 py-12 text-slate-400">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 pb-8 border-b border-slate-900">
          
          {/* Logo & Description */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Logo size={28} />
              <span className="text-lg font-bold text-white">Try<span className="text-indigo-400">Job</span></span>
            </div>
            <p className="text-xs leading-relaxed text-slate-400">
              {t('footer_desc')}
            </p>
          </div>

          {/* Simulyatsiyalar */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">{t('footer_simulations')}</h4>
            <ul className="space-y-2 text-xs">
              <li><span className="hover:text-indigo-400 transition cursor-pointer">💼 {t('footer_cat_1')}</span></li>
              <li><span className="hover:text-indigo-400 transition cursor-pointer">💳 {t('footer_cat_2')}</span></li>
              <li><span className="hover:text-indigo-400 transition cursor-pointer">📊 {t('footer_cat_3')}</span></li>
              <li><span className="hover:text-indigo-400 transition cursor-pointer">📄 {t('footer_cat_4')}</span></li>
            </ul>
          </div>

          {/* Hamkorlar */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">{t('footer_partners')}</h4>
            <ul className="space-y-2 text-xs">
              <li>JPMorgan Chase & Co.</li>
              <li>Goldman Sachs</li>
              <li>Accenture Strategy</li>
              <li>Kapitalbank ATB & Uzum</li>
            </ul>
          </div>

          {/* Xavfsizlik & Standartlar */}
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-3">{t('footer_security_title')}</h4>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <ShieldCheck className="w-4 h-4 shrink-0" /> {t('footer_security_badge')}
              </div>
              <p className="text-[11px] text-slate-500">
                {t('footer_security_desc')}
              </p>
            </div>
          </div>

        </div>

        {/* Mualliflik huquqi */}
        <div className="flex flex-col sm:flex-row items-center justify-between text-xs gap-4">
          <div>&copy; {new Date().getFullYear()} TryJob &bull; {t('footer_rights')}</div>
          <div className="flex items-center gap-1.5 text-slate-500">
            {t('footer_made_in')} <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500 inline" />
          </div>
        </div>
      </div>
    </footer>
  );
};
