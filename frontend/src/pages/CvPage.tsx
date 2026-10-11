import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { FileText, Loader2, Pencil, Plus, Printer, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Segmented } from '@/components/ui/segmented'
import { Switch } from '@/components/ui/switch'
import CvSheet, { type CvLang } from '@/components/credentials/CvSheet'
import { api, ApiError } from '@/lib/api'
import { formatDate } from '@/lib/time'
import type { Cv, CvSettings } from '@/lib/types'

// CONTRACT.md §28.2 bilan bir xil cheklovlar — server baribir tekshiradi
const MAX_LANGUAGES = 5
const PHONE = /^\+?[0-9 ()-]+$/
const LANGS: CvLang[] = ['uz', 'ru', 'en']
const LANG_KEY = 'tryjob.cvLang'

const phoneOk = (v: string) => !v.trim() || (PHONE.test(v.trim()) && v.replace(/\D/g, '').length >= 7)

function initialLang(ui: string): CvLang {
  try {
    const saved = localStorage.getItem(LANG_KEY)
    if (LANGS.includes(saved as CvLang)) return saved as CvLang
  } catch {
    // saqlash yopiq (maxfiy rejim) — interfeys tili
  }
  const base = ui.slice(0, 2) as CvLang
  return LANGS.includes(base) ? base : 'uz'
}

/** "CV" (`manage_portfolio`): sozlamalar va A4 varaqning jonli ko'rinishi, PDF — brauzer chop etishi (§28.4). */
export default function CvPage() {
  const { t, i18n } = useTranslation()
  const [cv, setCv] = useState<Cv | null>(null)
  const [form, setForm] = useState<CvSettings | null>(null)
  const [lang, setLang] = useState<CvLang>(() => initialLang(i18n.language))
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    api<Cv>('/users/me/cv')
      .then((data) => {
        setCv(data)
        setForm(data.settings)
      })
      .catch(() => setLoadError(true))
  }, [])

  // PDF fayl nomi brauzerda hujjat sarlavhasidan olinadi
  useEffect(() => {
    if (cv) document.title = `${cv.full_name} — CV`
    return () => {
      document.title = 'TryJob'
    }
  }, [cv])

  const pickLang = (next: CvLang) => {
    setLang(next)
    try {
      localStorage.setItem(LANG_KEY, next)
    } catch {
      // eslab qolinmasa ham ishlaydi
    }
  }

  if (loadError) return <p className="container mx-auto p-8 text-destructive">{t('common.error')}</p>
  if (!cv || !form) {
    return <p className="flex items-center justify-center gap-2 p-16 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {t('common.loading')}</p>
  }

  const set = (patch: Partial<CvSettings>) => {
    setForm({ ...form, ...patch })
    setMessage(null)
  }
  const toggleRun = (runId: string, visible: boolean) =>
    set({ hidden_run_ids: visible ? form.hidden_run_ids.filter((id) => id !== runId) : [...form.hidden_run_ids, runId] })

  const languagesOk = form.languages.every((l) => l.trim().length >= 1 && l.trim().length <= 40)
  const valid = phoneOk(form.phone ?? '') && languagesOk
  const dirty = JSON.stringify(form) !== JSON.stringify(cv.settings)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const next = await api<Cv>('/users/me/cv/settings', {
        method: 'PUT',
        json: { ...form, languages: form.languages.map((l) => l.trim()) },
      })
      setCv(next)
      setForm(next.settings)
      setMessage({ ok: true, text: t('cv.saved') })
    } catch (err) {
      setMessage({ ok: false, text: t(err instanceof ApiError && err.status === 422 ? 'cv.invalid' : 'common.error') })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 print:m-0 print:max-w-none print:space-y-0 print:p-0">
      <div className="animate-rise flex flex-wrap items-end justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">{t('cv.title')}</h1>
          <p className="max-w-2xl text-muted-foreground">{t('cv.subtitle')}</p>
        </div>
        {cv.experience.length > 0 && (
          <div className="flex flex-col items-end gap-1">
            <Button onClick={() => window.print()}><Printer className="h-4 w-4" /> {t('cv.download')}</Button>
            <span className="text-xs text-muted-foreground">{t('cv.printHint')}</span>
          </div>
        )}
      </div>

      {cv.experience.length === 0 ? (
        <div className="glass-strong animate-rise mx-auto max-w-xl space-y-4 rounded-3xl p-8 text-center">
          <FileText className="mx-auto h-12 w-12 text-primary" />
          <h2 className="text-xl font-extrabold">{t('cv.emptyTitle')}</h2>
          <p className="text-muted-foreground">{t('cv.emptyHint')}</p>
          <Button asChild><Link to="/simulations">{t('portfolio.startScenario')}</Link></Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[22rem_minmax(0,1fr)] print:block">
          <form onSubmit={save} className="glass animate-rise min-w-0 space-y-5 self-start rounded-3xl p-5 print:hidden lg:sticky lg:top-24">
            <div className="space-y-1.5">
              <Label>{t('cv.sheetLang')}</Label>
              <Segmented label={t('cv.sheetLang')} value={lang} onChange={pickLang}
                options={LANGS.map((l) => ({ value: l, label: t(`languages.${l}`) }))} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              <div className="space-y-1.5">
                <Label htmlFor="cv-phone">{t('cv.phone')}</Label>
                <Input id="cv-phone" type="tel" inputMode="tel" maxLength={20} placeholder="+998 90 123 45 67"
                  value={form.phone ?? ''} aria-invalid={!phoneOk(form.phone ?? '')}
                  onChange={(e) => set({ phone: e.target.value })} />
                {!phoneOk(form.phone ?? '') && <p className="text-xs text-destructive">{t('cv.phoneHint')}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cv-city">{t('cv.city')}</Label>
                <Input id="cv-city" maxLength={80} placeholder={t('cv.cityPlaceholder')}
                  value={form.city ?? ''} onChange={(e) => set({ city: e.target.value })} />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="block">{t('cv.languages', { max: MAX_LANGUAGES })}</Label>
              {form.languages.map((l, i) => (
                <div key={i} className="flex gap-2">
                  <Input aria-label={t('cv.language')} placeholder={t('cv.languagePlaceholder')} value={l} maxLength={40}
                    onChange={(e) => set({ languages: form.languages.map((x, j) => (j === i ? e.target.value : x)) })} />
                  <Button type="button" variant="ghost" size="icon" aria-label={t('cv.removeLanguage')}
                    onClick={() => set({ languages: form.languages.filter((_, j) => j !== i) })}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              {!languagesOk && <p className="text-xs text-destructive">{t('cv.languageHint')}</p>}
              {form.languages.length < MAX_LANGUAGES && (
                <Button type="button" variant="outline" size="sm" onClick={() => set({ languages: [...form.languages, ''] })}>
                  <Plus className="h-4 w-4" /> {t('cv.addLanguage')}
                </Button>
              )}
            </div>

            <fieldset className="min-w-0 space-y-2">
              <legend className="text-sm font-medium">{t('cv.runs')}</legend>
              <p className="text-xs text-muted-foreground">{t('cv.runsHint')}</p>
              <ul className="divide-y rounded-2xl border bg-background/50">
                {cv.experience.map((e) => {
                  const visible = !form.hidden_run_ids.includes(e.run_id)
                  return (
                    <li key={e.run_id}>
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5">
                        <span className="min-w-0 flex-1">
                          <span className={`block truncate text-sm font-semibold ${visible ? '' : 'text-muted-foreground line-through'}`}>
                            {e.scenario_title}
                          </span>
                          <span className="block text-xs text-muted-foreground">
                            {formatDate(e.completed_at, i18n.language)}
                            {e.overall_score !== null && ` · ${Math.round(e.overall_score)}/100`}
                          </span>
                        </span>
                        <Switch checked={visible} onCheckedChange={(on) => toggleRun(e.run_id, on)}
                          aria-label={t('cv.showRun', { title: e.scenario_title })} />
                      </label>
                    </li>
                  )
                })}
              </ul>
            </fieldset>

            <p className="rounded-2xl bg-primary/8 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
              {t('cv.profileHint')}{' '}
              <Link to="/portfolio" className="inline-flex items-center gap-1 font-semibold text-primary hover:underline">
                <Pencil className="h-3 w-3" /> {t('cv.editProfile')}
              </Link>
            </p>

            {message && (
              <p role="status" className={`rounded-xl px-3 py-2 text-sm ${message.ok ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'}`}>
                {message.text}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={saving || !dirty || !valid}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t('common.save')}
            </Button>
          </form>

          <div className="animate-rise min-w-0" style={{ animationDelay: '80ms' }}>
            <CvSheet cv={cv} settings={form} lang={lang} />
          </div>
        </div>
      )}
    </div>
  )
}
