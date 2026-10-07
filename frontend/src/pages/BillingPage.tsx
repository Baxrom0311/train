import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Receipt } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import InvoiceList, { formatMoney } from '@/components/billing/InvoiceList'
import { api } from '@/lib/api'
import type { Invoice } from '@/lib/types'

/** Tashkilot xodimi: o'z tashkilotining invoice'lari (CONTRACT.md §11.3). */
export default function BillingPage() {
  const { t, i18n } = useTranslation()
  const [invoices, setInvoices] = useState<Invoice[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api<Invoice[]>('/billing/invoices').then(setInvoices).catch(() => setError(true))
  }, [])

  const due = (invoices ?? []).filter((i) => i.status === 'pending')
  const totals = Object.entries(
    due.reduce<Record<string, number>>((acc, i) => ({ ...acc, [i.currency]: (acc[i.currency] ?? 0) + Number(i.amount) }), {}),
  )

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('billing.title')}</h1>
        <p className="text-muted-foreground">{t('billing.subtitle')}</p>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{t('common.error')}</p>}

      {totals.length > 0 && (
        <Card className="glow-ring animate-rise">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
            <span className="text-sm text-muted-foreground">{t('billing.dueTotal', { count: due.length })}</span>
            <span className="text-2xl font-extrabold tabular-nums">
              {totals.map(([cur, sum]) => formatMoney(String(sum), cur, i18n.language)).join(' + ')}
            </span>
          </CardContent>
        </Card>
      )}

      <Card className="animate-rise">
        <CardContent className="p-4">
          {invoices?.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center text-sm text-muted-foreground">
              <Receipt className="h-8 w-8" /> {t('billing.none')}
            </div>
          ) : (
            invoices && <InvoiceList invoices={invoices} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
