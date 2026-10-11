import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Award, Crown, ExternalLink, Linkedin, Loader2, UsersRound } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from './Badge'
import { api } from '@/lib/api'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { linkedInUrl } from '@/components/credentials/share'
import type { Certificate, DayReport, FinalReport, RunReport, TaskResult } from '@/lib/types'
import { ChecksBadge } from '@/components/desk/Checks'

const score = (v: number | null | undefined) => (v === null || v === undefined ? '—' : Math.round(v))

export default function RunReportPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const [report, setReport] = useState<RunReport | null>(null)
  const [error, setError] = useState(false)
  const [cert, setCert] = useState<Certificate | null>(null)

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = async () => {
      try {
        const r = await api<RunReport>(`/runs/${id}/report`)
        setReport(r)
        // yakuniy hisobot fon job'da yoziladi — tayyor bo'lguncha kutamiz
        if (r.final_pending) timer = setTimeout(load, 20_000)
      } catch {
        setError(true)
      }
    }
    load()
    return () => clearTimeout(timer)
  }, [id])

  // sertifikat yakuniy hisobot bilan bir tranzaksiyada beriladi (CONTRACT.md §13.1)
  const certified = report?.final?.certificate ?? false
  useEffect(() => {
    if (!certified) return
    api<Certificate[]>('/users/me/certificates')
      .then((list) => setCert(list.find((c) => c.run_id === id) ?? null))
      .catch(() => setCert(null))
  }, [certified, id])

  if (error) return <p className="container mx-auto p-8 text-destructive">{t('common.error')}</p>
  if (!report) return <p className="container mx-auto p-8 text-muted-foreground">{t('common.loading')}</p>

  const final = report.final
  // jamoaviy Run (§29.4): "kim bajardi" ustuni uchun ismlar
  const names = final?.team ? Object.fromEntries(final.team.members.map((m) => [m.user_id, m.name])) : undefined
  const competencies = Object.entries(report.competency_scores ?? {})

  return (
    <div className="container mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold tracking-tight">{t('report.title')}</h1>
        <div className="flex gap-2">
          <Badge variant="outline">{t(`run.status.${report.status}`)}</Badge>
          <Button size="sm" variant="outline" asChild>
            <Link to={`/runs/${id}`}>{t('report.backToDesk')}</Link>
          </Button>
        </div>
      </div>

      {report.final_pending && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> {t('report.pending')}
        </p>
      )}
      {!final && !report.final_pending && report.days.length === 0 && (
        <p className="text-muted-foreground">{t(report.status === 'abandoned' ? 'report.abandoned' : 'report.none')}</p>
      )}

      {final && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>{t('report.final')}</CardTitle>
            {final.certificate ? (
              <Badge className="gap-1"><Award className="h-3 w-3" /> {t('report.certificate')}</Badge>
            ) : final.team ? (
              <Badge variant="secondary" className="gap-1"><UsersRound className="h-3 w-3" /> {t('catalog.teamRun')}</Badge>
            ) : (
              <Badge variant="secondary">{t('report.incomplete')}</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div className="col-span-2 flex items-center gap-4 rounded-2xl border bg-background/60 p-4 sm:col-span-1">
                <ScoreRing value={final.overall_score ?? 0} size={72} />
                <div>
                  <p className="text-xs text-muted-foreground">{t('report.overall')}</p>
                  <p className="text-sm font-semibold">
                    {final.certificate ? t('report.certificate') : final.team && !final.incomplete ? t('report.team.title') : t('report.incomplete')}
                  </p>
                </div>
              </div>
              <Stat label={t('report.onTime')} value={final.on_time_rate === null ? '—' : `${Math.round(final.on_time_rate)}%`} />
              <Stat label={t('report.tasksDone')} value={final.tasks.filter((x) => x.status === 'submitted').length + '/' + final.tasks.length} />
            </div>

            {competencies.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold">{t('report.competencies')}</h3>
                <CompetencyBars scores={Object.fromEntries(competencies)} />
              </div>
            )}

            {final.summary && (
              <div className="space-y-3 text-sm">
                <p className="whitespace-pre-wrap">{final.summary.summary}</p>
                <Lists strengths={final.summary.strengths} improvements={final.summary.improvements} />
              </div>
            )}

            {cert && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/30 bg-primary/5 p-4">
                <div className="flex items-center gap-3">
                  <span className="bg-brand grid h-10 w-10 place-items-center rounded-xl text-primary-foreground"><Award className="h-5 w-5" /></span>
                  <div>
                    <p className="font-semibold">{t('report.certificateReady')}</p>
                    <p className="font-mono text-xs text-muted-foreground">{cert.code}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {cert.status === 'valid' && (
                    <Button size="sm" variant="outline" asChild>
                      <a href={linkedInUrl(cert)} target="_blank" rel="noopener noreferrer"><Linkedin className="h-4 w-4" /> {t('cert.linkedin')}</a>
                    </Button>
                  )}
                  <Button size="sm" asChild>
                    <Link to={`/c/${cert.code}`}><ExternalLink className="h-4 w-4" /> {t('report.openCertificate')}</Link>
                  </Button>
                </div>
              </div>
            )}

            {final.team && <TeamResults team={final.team} />}

            <TaskTable tasks={final.tasks} names={names} />
          </CardContent>
        </Card>
      )}

      {report.days.map((day) => (
        <DayCard key={day.day} day={day} names={names} />
      ))}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border bg-background/60 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-extrabold tabular-nums">{value}</p>
    </div>
  )
}

function Lists({ strengths, improvements }: { strengths: string[]; improvements: string[] }) {
  const { t } = useTranslation()
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {strengths.length > 0 && (
        <div>
          <p className="font-medium">{t('report.strengths')}</p>
          <ul className="list-disc pl-5">{strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
      {improvements.length > 0 && (
        <div>
          <p className="font-medium">{t('report.improvements')}</p>
          <ul className="list-disc pl-5">{improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

function DayCard({ day, names }: { day: DayReport; names?: Record<string, string> }) {
  const { t } = useTranslation()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {t('report.day', { day: day.day })} · {score(day.average_score)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {day.summary && (
          <>
            <Lists strengths={day.summary.strengths} improvements={day.summary.improvements} />
            <p className="rounded-xl border border-primary/20 bg-primary/8 p-3">💡 {day.summary.advice}</p>
          </>
        )}
        <TaskTable tasks={day.tasks} names={names} />
      </CardContent>
    </Card>
  )
}

/** §29.4: har a'zo hissasi — kodda hisoblangan ko'rsatkichlar. */
function TeamResults({ team }: { team: NonNullable<FinalReport['team']> }) {
  const { t } = useTranslation()
  const title = (key: string) => team.roles.find((r) => r.key === key)?.title ?? key
  return (
    <div className="space-y-3">
      <div>
        <h3 className="flex items-center gap-2 font-semibold"><UsersRound className="h-4 w-4 text-primary" /> {t('report.team.title')}</h3>
        <p className="text-xs text-muted-foreground">{t('report.team.noCertificate')}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {team.members.map((m) => (
          <div key={m.user_id} className="flex gap-4 rounded-2xl border bg-background/60 p-4">
            <ScoreRing value={m.overall_score ?? 0} size={56} />
            <div className="min-w-0 flex-1 space-y-1.5 text-sm">
              <p className="flex items-center gap-1.5 font-semibold">
                {m.is_captain && <Crown className="h-3.5 w-3.5 text-amber-500" />}
                <span className="truncate">{m.name}</span>
                {m.left && <span className="text-xs font-normal text-muted-foreground">({t('report.team.left')})</span>}
              </p>
              {m.roles.length > 0 && <p className="truncate text-xs text-muted-foreground">{m.roles.map(title).join(', ')}</p>}
              <p className="text-xs text-muted-foreground">
                {t('report.team.submitted')}: {m.submitted}/{m.assigned}
                {m.on_time_rate !== null && ` · ${t('report.onTime')}: ${Math.round(m.on_time_rate)}%`}
              </p>
              {m.share !== null && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground">{t('report.team.share')}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="bg-brand h-full rounded-full" style={{ width: `${m.share}%` }} />
                  </div>
                  <span className="font-semibold tabular-nums">{Math.round(m.share)}%</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function TaskTable({ tasks, names }: { tasks: TaskResult[]; names?: Record<string, string> }) {
  const { t } = useTranslation()
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted-foreground">
          <tr>
            <th className="py-1 pr-2">{t('report.task')}</th>
            {names && <th className="py-1 pr-2">{t('report.team.by')}</th>}
            <th className="py-1 pr-2">{t('report.status')}</th>
            <th className="py-1 text-right">{t('report.score')}</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {tasks.map((task) => (
            <tr key={task.node_id}>
              <td className="py-2 pr-2">
                {task.title}
                {task.checks && <span className="ml-2 align-middle"><ChecksBadge checks={task.checks} /></span>}
              </td>
              {names && <td className="py-2 pr-2">{task.by ? names[task.by] ?? '—' : '—'}</td>}
              <td className="py-2 pr-2 text-muted-foreground">
                {t(`desk.status.${task.status}`)}
                {task.late && ` · ${t('report.late')}`}
              </td>
              <td className="py-2 text-right font-medium">{score(task.score)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
