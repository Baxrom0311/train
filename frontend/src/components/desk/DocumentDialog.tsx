import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { DocumentOut } from '@/lib/types'
import RichText from './RichText'

export default function DocumentDialog({ runId, docKey, onClose }: { runId: string; docKey: string; onClose: () => void }) {
  const { t } = useTranslation()
  const [doc, setDoc] = useState<DocumentOut | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api<DocumentOut>(`/runs/${runId}/documents/${docKey}`).then(setDoc).catch(() => setError(true))
  }, [runId, docKey])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <div role="dialog" aria-modal="true"
        className="glass-strong flex max-h-[85vh] w-full max-w-3xl animate-rise flex-col rounded-2xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
          <h2 className="flex items-center gap-2 font-semibold">
            <FileText className="h-4 w-4" /> {doc?.title ?? '…'}
          </h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label={t('common.close')}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="overflow-y-auto p-5">
          {error ? <p className="text-sm text-destructive">{t('common.error')}</p> : doc && <RichText text={doc.content} />}
        </div>
      </div>
    </div>
  )
}
