import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Award, ExternalLink, Eye, Linkedin, Loader2, Plus, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import CertificateCard from '@/components/credentials/CertificateCard'
import CopyButton from '@/components/credentials/CopyButton'
import { certificateUrl } from '@/components/credentials/CertificateSheet'
import { linkedInUrl } from '@/components/credentials/share'
import { api, ApiError } from '@/lib/api'
import type { Certificate, PortfolioSettings } from '@/lib/types'

// CONTRACT.md §13.2 bilan bir xil cheklovlar — server baribir tekshiradi
const SLUG = /^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/
const MAX_LINKS = 3
const HEADLINE_MAX = 120
const ABOUT_MAX = 1000

/** "Portfolio": talabaning sertifikatlari va ochiq sahifa sozlamalari (`manage_portfolio`). */
export default function PortfolioPage() {
  const { t } = useTranslation()
  const [certs, setCerts] = useState<Certificate[] | null>(null)
  const [form, setForm] = useState<PortfolioSettings | null>(null)
  const [saved, setSaved] = useState<PortfolioSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [loadError, setLoadError] = useState(false)

  useEffect(() => {
    Promise.all([api<Certificate[]>('/users/me/certificates'), api<PortfolioSettings>('/users/me/portfolio')])
      .then(([c, p]) => {
        setCerts(c)
        setForm(p)
        setSaved(p)
      })
      .catch(() => setLoadError(true))
  }, [])

  if (loadError) return <p className="container mx-auto p-8 text-destructive">{t('common.error')}</p>
  if (!certs || !form) {
    return <p className="flex items-center justify-center gap-2 p-16 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {t('common.loading')}</p>
  }

  const set = (patch: Partial<PortfolioSettings>) => {
    setForm({ ...form, ...patch })
    setMessage(null)
  }
  const setLink = (i: number, patch: Partial<PortfolioSettings['links'][number]>) =>
    set({ links: form.links.map((l, j) => (j === i ? { ...l, ...patch } : l)) })

  const slugOk = SLUG.test(form.slug)
  const linksOk = form.links.every((l) => l.label.trim() && /^https:\/\/\S+$/.test(l.url.trim()))
  const dirty = JSON.stringify(form) !== JSON.stringify(saved)
  const publicUrl = `${window.location.origin}/p/${saved?.slug}`
  const live = saved?.exists && saved.is_public

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const next = await api<PortfolioSettings>('/users/me/portfolio', {
        method: 'PUT',
        json: {
          slug: form.slug,
          is_public: form.is_public,
          headline: form.headline,
          about: form.about,
          links: form.links.map((l) => ({ label: l.label.trim(), url: l.url.trim() })),
        },
      })
      setForm(next)
      setSaved(next)
      setMessage({ ok: true, text: t('portfolio.saved') })
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0
      setMessage({ ok: false, text: t(status === 409 ? 'portfolio.slugTaken' : status === 422 ? 'portfolio.invalid' : 'common.error') })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="container mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3 animate-rise">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">{t('portfolio.title')}</h1>
          <p className="text-muted-foreground">{t('portfolio.subtitle')}</p>
        </div>
        {live && (
          <div className="flex flex-wrap gap-2">
            <CopyButton value={publicUrl} />
            <Button size="sm" asChild>
              <Link to={`/p/${saved.slug}`}><Eye className="h-4 w-4" /> {t('portfolio.viewPublic')}</Link>
            </Button>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <section className="glass animate-rise space-y-3 self-start rounded-2xl p-5">
          <h2 className="flex items-center gap-2 font-bold">
            <Award className="h-4 w-4 text-primary" /> {t('portfolio.myCertificates', { count: certs.length })}
          </h2>
          {certs.length === 0 ? (
            <div className="space-y-3 rounded-2xl border border-dashed p-8 text-center">
              <Award className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{t('portfolio.empty')}</p>
              <Button size="sm" asChild><Link to="/simulations">{t('portfolio.startScenario')}</Link></Button>
            </div>
          ) : (
            certs.map((c) => (
              <CertificateCard
                key={c.code}
                cert={c}
                actions={
                  <>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/c/${c.code}`}><ExternalLink className="h-4 w-4" /> {t('portfolio.open')}</Link>
                    </Button>
                    {c.status === 'valid' && (
                      <>
                        <CopyButton value={certificateUrl(c.code)} />
                        <Button size="sm" variant="outline" asChild>
                          <a href={linkedInUrl(c)} target="_blank" rel="noopener noreferrer">
                            <Linkedin className="h-4 w-4" /> {t('cert.linkedin')}
                          </a>
                        </Button>
                      </>
                    )}
                  </>
                }
              />
            ))
          )}
        </section>

        <Card className="animate-rise self-start" style={{ animationDelay: '80ms' }}>
          <CardHeader>
            <CardTitle className="text-lg">{t('portfolio.settings')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={save} className="space-y-5">
              <label className="flex items-start justify-between gap-4 rounded-xl border bg-background/50 p-3">
                <span className="space-y-1">
                  <span className="block font-semibold">{t('portfolio.public')}</span>
                  <span className="block text-sm text-muted-foreground">{t('portfolio.publicHint')}</span>
                </span>
                <Switch checked={form.is_public} onCheckedChange={(on) => set({ is_public: on })} className="mt-1" />
              </label>

              <div className="space-y-1.5">
                <Label htmlFor="pf-slug">{t('portfolio.slug')}</Label>
                <div className="flex items-center overflow-hidden rounded-xl border border-input bg-background/60 focus-within:border-primary/60 focus-within:ring-4 focus-within:ring-ring/15">
                  <span className="hidden whitespace-nowrap border-r bg-muted/50 px-3 py-2 text-sm text-muted-foreground sm:block">
                    {window.location.host}/p/
                  </span>
                  <input
                    id="pf-slug"
                    value={form.slug}
                    onChange={(e) => set({ slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                    maxLength={40}
                    className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none"
                    aria-invalid={!slugOk}
                  />
                </div>
                <p className={`text-xs ${slugOk ? 'text-muted-foreground' : 'text-destructive'}`}>{t('portfolio.slugHint')}</p>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="pf-headline">{t('portfolio.headline')}</Label>
                <Input id="pf-headline" value={form.headline} maxLength={HEADLINE_MAX}
                  placeholder={t('portfolio.headlinePlaceholder')} onChange={(e) => set({ headline: e.target.value })} />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-baseline justify-between">
                  <Label htmlFor="pf-about">{t('portfolio.about')}</Label>
                  <span className="text-xs tabular-nums text-muted-foreground">{form.about.length}/{ABOUT_MAX}</span>
                </div>
                <Textarea id="pf-about" rows={5} value={form.about} maxLength={ABOUT_MAX}
                  placeholder={t('portfolio.aboutPlaceholder')} onChange={(e) => set({ about: e.target.value })} />
              </div>

              <div className="space-y-2">
                <Label>{t('portfolio.links')}</Label>
                {form.links.map((l, i) => (
                  <div key={i} className="flex gap-2">
                    <Input aria-label={t('portfolio.linkLabel')} placeholder="GitHub" value={l.label} maxLength={40}
                      className="w-28 shrink-0" onChange={(e) => setLink(i, { label: e.target.value })} />
                    <Input aria-label={t('portfolio.linkUrl')} placeholder="https://" value={l.url} maxLength={200}
                      type="url" onChange={(e) => setLink(i, { url: e.target.value })} />
                    <Button type="button" variant="ghost" size="icon" aria-label={t('portfolio.removeLink')}
                      onClick={() => set({ links: form.links.filter((_, j) => j !== i) })}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {!linksOk && <p className="text-xs text-destructive">{t('portfolio.linkHint')}</p>}
                {form.links.length < MAX_LINKS && (
                  <Button type="button" variant="outline" size="sm"
                    onClick={() => set({ links: [...form.links, { label: '', url: 'https://' }] })}>
                    <Plus className="h-4 w-4" /> {t('portfolio.addLink')}
                  </Button>
                )}
              </div>

              {message && (
                <p role="status" className={`rounded-xl px-3 py-2 text-sm ${message.ok ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'}`}>
                  {message.text}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={saving || !dirty || !slugOk || !linksOk}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t('common.save')}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
