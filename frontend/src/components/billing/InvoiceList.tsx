import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Building2, CheckCircle2, CircleDashed, School, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/lib/time'
import type { Invoice } from '@/lib/types'

export function formatMoney(amount: string, currency: string, locale: string) {
  return new Intl.NumberFormat(locale, { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(amount))
}

const STATUS = {
  pending: { Icon: CircleDashed, cls: 'text-primary' },
  paid: { Icon: CheckCircle2, cls: 'text-success' },
  cancelled: { Icon: XCircle, cls: 'text-muted-foreground' },
}

/** Invoice qatorlari; `actions` — admin uchun tugmalar (tashkilotda yo'q). */
export default function InvoiceList({ invoices, actions }: { invoices: Invoice[]; actions?: (i: Invoice) => ReactNode }) {
  const { t, i18n } = useTranslation()
  return (
    <ul className="divide-y divide-border/60">
      {invoices.map((inv) => {
        const s = STATUS[inv.status]
        const PayerIcon = inv.payer_type === 'company' ? Building2 : School
        return (
          <li key={inv.id} className="flex flex-wrap items-center gap-3 px-1 py-3.5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
              <PayerIcon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{inv.payer_name ?? '—'}</p>
              <p className="truncate text-xs text-muted-foreground">
                {formatDateTime(inv.created_at)}{inv.notes && ` · ${inv.notes}`}
              </p>
            </div>
            <div className="text-right">
              <p className={cn('font-bold tabular-nums', inv.status === 'cancelled' && 'text-muted-foreground line-through')}>
                {formatMoney(inv.amount, inv.currency, i18n.language)}
              </p>
              <p className={cn('inline-flex items-center gap-1 text-xs', s.cls)}>
                <s.Icon className="h-3 w-3" /> {t(`billing.status.${inv.status}`)}
                {inv.paid_marked_at && ` · ${formatDateTime(inv.paid_marked_at)}`}
              </p>
            </div>
            {actions && <div className="flex w-full justify-end gap-2 sm:w-auto">{actions(inv)}</div>}
          </li>
        )
      })}
    </ul>
  )
}
