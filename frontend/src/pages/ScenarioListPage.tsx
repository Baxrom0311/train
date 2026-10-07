// Ssenariylar ro'yxati (CONTRACT.md §16.3): versiyalar holati, faollik, muharrirga o'tish.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Clapperboard, Loader2, Pencil, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { SECTOR_ART } from '@/components/sectorArt'
import type { ScenarioAdmin, VersionInfo } from '@/components/editor/model'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import { cn } from '@/lib/utils'

const BADGE: Record<VersionInfo['status'], string> = {
  published: 'bg-success/12 text-success',
  draft: 'bg-primary/12 text-primary',
  archived: 'bg-muted text-muted-foreground',
}

export default function ScenarioListPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<ScenarioAdmin[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api<ScenarioAdmin[]>('/admin/scenarios').then(setItems).catch((e) => setError(e.message))
  }, [])

  const toggle = async (s: ScenarioAdmin, is_active: boolean) => {
    setItems((list) => list?.map((x) => (x.id === s.id ? { ...x, is_active } : x)) ?? null)
    try {
      await api(`/admin/scenarios/${s.id}`, { method: 'PATCH', json: { is_active } })
    } catch (e) {
      setItems((list) => list?.map((x) => (x.id === s.id ? { ...x, is_active: !is_active } : x)) ?? null)
      setError((e as Error).message)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 animate-rise">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">{t('editor.list.title')}</h1>
          <p className="text-muted-foreground">{t('editor.list.subtitle')}</p>
        </div>
        <Button asChild>
          <Link to="/admin/scenarios/new"><Plus className="h-4 w-4" /> {t('editor.list.new')}</Link>
        </Button>
      </div>

      {error && <p className="rounded-2xl bg-destructive/10 px-4 py-2.5 text-sm font-medium text-destructive">{error}</p>}
      {!items && !error && <div className="grid place-items-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>}
      {items?.length === 0 && (
        <div className="glass grid place-items-center gap-3 rounded-3xl py-16 text-center text-muted-foreground">
          <Clapperboard className="h-8 w-8" />
          <p>{t('editor.list.empty')}</p>
        </div>
      )}

      <ul className="grid gap-3">
        {items?.map((s) => {
          const art = SECTOR_ART[s.sector]
          const latest = s.versions[0]
          return (
            <li key={s.id} className={cn('glass flex flex-wrap items-center gap-4 rounded-3xl p-4 sm:flex-nowrap', !s.is_active && 'opacity-70')}>
              <span className={cn('grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br', art.glow)}>
                <art.Icon className="h-6 w-6 text-foreground/70" />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <Link to={`/admin/scenarios/${s.id}/edit`} className="block truncate font-bold hover:text-primary">{s.title}</Link>
                <p className="truncate text-xs text-muted-foreground">
                  <span className="font-mono">{s.slug}</span> · {t(`catalog.sector.${s.sector}`)} · {s.company_name} · {t('catalog.days', { count: s.duration_days })}
                </p>
                <div className="flex flex-wrap items-center gap-1.5">
                  {s.versions.slice(0, 4).map((v) => (
                    <Link key={v.version} to={`/admin/scenarios/${s.id}/edit?v=${v.version}`}
                      title={formatDateTime(v.published_at ?? v.created_at)}
                      className={cn('rounded-full px-2 py-0.5 text-[11px] font-semibold transition-opacity hover:opacity-80', BADGE[v.status])}>
                      v{v.version} · {t(`editor.status.${v.status}`)}
                    </Link>
                  ))}
                  {s.versions.length > 4 && <span className="text-[11px] text-muted-foreground">+{s.versions.length - 4}</span>}
                  <span className="text-[11px] text-muted-foreground">· {t('editor.list.runs', { count: s.runs })}</span>
                </div>
              </div>
              <label className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
                <Switch checked={s.is_active} onCheckedChange={(v) => toggle(s, v)} aria-label={t('editor.list.active')} />
                {s.is_active ? t('editor.list.active') : t('editor.list.hidden')}
              </label>
              <Button variant="outline" size="sm" asChild>
                <Link to={`/admin/scenarios/${s.id}/edit`}>
                  <Pencil className="h-4 w-4" /> {latest?.status === 'draft' ? t('editor.list.continueDraft') : t('editor.list.edit')}
                </Link>
              </Button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
