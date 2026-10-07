import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { Award, ExternalLink, Linkedin, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from './Badge'
import { api } from '@/lib/api'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { linkedInUrl } from '@/components/credentials/share'
import type { Certificate, DayReport, RunReport, TaskResult } from '@/lib/types'

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
                  <p className="text-sm font-semibold">{final.certificate ? t('report.certificate') : t('report.incomplete')}</p>
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

            <TaskTable tasks={final.tasks} />
          </CardContent>
        </Card>
      )}

      {report.days.map((day) => (
        <DayCard key={day.day} day={day} />
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

function DayCard({ day }: { day: DayReport }) {
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
        <TaskTable tasks={day.tasks} />
      </CardContent>
    </Card>
  )
}

function TaskTable({ tasks }: { tasks: TaskResult[] }) {
  const { t } = useTranslation()
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted-foreground">
          <tr>
            <th className="py-1 pr-2">{t('report.task')}</th>
            <th className="py-1 pr-2">{t('report.status')}</th>
            <th className="py-1 text-right">{t('report.score')}</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {tasks.map((task) => (
            <tr key={task.node_id}>
              <td className="py-2 pr-2">{task.title}</td>
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
