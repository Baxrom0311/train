// YAML bo'limi: muharrir holati ↔ YAML matni (CONTRACT.md §16.2 `to-yaml`, `yaml`).
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, FileUp, Loader2, RefreshCw, Wand2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { ErrorNote } from './fields'
import { normalize, type FieldError, type ScenarioDef } from './model'

const describe = (e: FieldError) => (e.path.length ? `${e.path.join('.')}: ${e.message}` : e.message)

export default function YamlPanel({ defn, onApply }: { defn: ScenarioDef; onApply: (d: ScenarioDef) => void }) {
  const { t } = useTranslation()
  const [text, setText] = useState<string | null>(null)
  const [edited, setEdited] = useState(false)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [applied, setApplied] = useState(false)
  const file = useRef<HTMLInputElement>(null)

  const load = () => {
    setBusy(true)
    api<{ text: string }>('/admin/scenarios/to-yaml', { method: 'POST', json: { definition: defn } })
      .then((r) => { setText(r.text); setEdited(false); setErrors([]) })
      .catch((e) => setErrors([e.message]))
      .finally(() => setBusy(false))
  }
  // bo'lim ochilganda — joriy holat (saqlanmagan o'zgarishlar bilan)
  useEffect(load, [])

  const apply = async (source: string) => {
    setBusy(true)
    setApplied(false)
    try {
      const r = await api<{ definition: unknown; errors: FieldError[] }>('/admin/scenarios/yaml', { method: 'POST', json: { text: source } })
      setErrors(r.errors.map(describe))
      if (r.definition) {
        onApply(normalize(r.definition))
        setEdited(false)
        setApplied(true)
      }
    } catch (e) {
      setErrors([(e as Error).message])
    } finally {
      setBusy(false)
    }
  }

  const download = () => {
    const url = URL.createObjectURL(new Blob([text ?? ''], { type: 'text/yaml;charset=utf-8' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: `${defn.slug || 'scenario'}.yaml` })
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="glass space-y-4 rounded-3xl p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto max-w-xl text-sm text-muted-foreground">{t('editor.yaml.intro')}</p>
        <input ref={file} type="file" accept=".yaml,.yml,text/yaml" className="hidden"
          onChange={async (e) => {
            const f = e.target.files?.[0]
            e.target.value = ''
            if (!f) return
            const content = await f.text()
            setText(content)
            await apply(content)
          }} />
        <Button variant="outline" size="sm" onClick={() => file.current?.click()} disabled={busy}>
          <FileUp className="h-4 w-4" /> {t('editor.yaml.open')}
        </Button>
        <Button variant="outline" size="sm" onClick={download} disabled={busy || text === null}>
          <Download className="h-4 w-4" /> {t('editor.yaml.download')}
        </Button>
        {edited && (
          <Button variant="ghost" size="sm" onClick={load} disabled={busy}>
            <RefreshCw className="h-4 w-4" /> {t('editor.yaml.reset')}
          </Button>
        )}
        <Button size="sm" onClick={() => text !== null && apply(text)} disabled={busy || !edited}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} {t('editor.yaml.apply')}
        </Button>
      </div>
      {edited && <p className="text-xs font-medium text-primary">{t('editor.yaml.unapplied')}</p>}
      {applied && <p className="text-xs font-medium text-success">{t('editor.yaml.applied')}</p>}
      <ErrorNote messages={errors} />
      <Textarea value={text ?? ''} spellCheck={false} aria-label="YAML" disabled={text === null}
        className="min-h-[60vh] font-mono text-[13px] leading-relaxed"
        onChange={(e) => { setText(e.target.value); setEdited(true); setApplied(false) }} />
    </div>
  )
}
