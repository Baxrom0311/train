// Tarmoq uzilganda sahifa tepasida yo'lak (CONTRACT.md §22.1). Javoblar yo'qolmasligi
// uchun talaba bilsin: yuborish tarmoq qaytgach qayta urinilishi kerak.
import { useTranslation } from 'react-i18next'
import { WifiOff } from 'lucide-react'
import { useOnline } from '@/lib/pwa'

export default function OfflineBanner() {
  const { t } = useTranslation()
  if (useOnline()) return null
  return (
    <div role="status" className="mx-3 mt-2 print:hidden">
      <p className="glass mx-auto flex max-w-7xl items-center gap-2 rounded-2xl border-amber-400/40 px-4 py-2 text-sm font-medium text-amber-800 dark:text-amber-200">
        <WifiOff className="h-4 w-4 shrink-0" /> {t('pwa.offline')}
      </p>
    </div>
  )
}
