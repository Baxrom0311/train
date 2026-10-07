// Ssenariy matni: oddiy matn, ``` bilan o'ralgan kod bloklari, `a | b | c` jadvallar va
// `A) ...` + chekinishli qatorlardan iborat kartochkalar (CV, profil) — markdown parser shart emas.

const LIST_ITEM = /^\s*([-•*]|\d+[.)]|[A-Za-z][.)])\s/
const TABLE_RULE = /^\s*\|?\s*:?-{2,}/
const LONG_CELL = 32
// Kartochka: abzas `A) Sarlavha. Qolgani` bilan boshlanadi, keyingi qatorlari chekinishli
const CARD_HEAD = /^([A-Z])\)\s+(.+)$/
const PERIOD = /^(\d{4}-\d{2})\s*[–-]\s*(\d{4}-\d{2}|hozir)\s*:\s*(.+)$/
const FIELD = /^([^:]{2,30}):\s+(.+)$/

/** Qator jadval qatorimi: `| a | b |` yoki kamida ikkita `|` ajratgichli `a | b | c`. */
function isTableRow(line: string): boolean {
  const t = line.trim()
  return t.startsWith('|') || (t.match(/\s\|\s/g)?.length ?? 0) >= 2
}

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
}

/**
 * YAML `|` bloklaridagi qator uzilishlari — abzas ichida bo'sh joy. Alohida qatorda qoladi:
 * ro'yxat bandlari (`-`, `1.`, `A)`) va chekinishli qatorlar (masalan, CV'dagi sanalar).
 */
export function reflow(text: string): string {
  return text
    .split(/\n{2,}/)
    .map((para) =>
      para
        .split('\n')
        .reduce((out, line, i) => {
          if (i === 0) return line
          const keep = LIST_ITEM.test(line) || /^\s/.test(line)
          return out + (keep ? '\n' : ' ') + (keep ? line.trimEnd() : line.trim())
        }, ''),
    )
    .join('\n\n')
}

type Card = { badge: string; title: string; subtitle: string; lines: string[] }
type Block = { kind: 'text'; text: string } | { kind: 'table'; rows: string[][] } | { kind: 'cards'; cards: Card[] }

function asCard(para: string): Card | null {
  const [first, ...rest] = para.split('\n')
  const head = CARD_HEAD.exec(first.trim())
  if (!head || rest.length === 0 || !rest.every((l) => /^\s/.test(l))) return null
  const dot = head[2].indexOf('. ')
  return {
    badge: head[1],
    title: dot > 0 ? head[2].slice(0, dot) : head[2],
    subtitle: dot > 0 ? head[2].slice(dot + 2) : '',
    lines: rest.map((l) => l.trim()),
  }
}

/** Abzaslarni matn va kartochkalarga ajratadi; ketma-ket kartochkalar bitta guruh. */
function textBlocks(text: string): Block[] {
  const out: Block[] = []
  for (const para of text.split(/\n{2,}/)) {
    const card = asCard(para)
    const last = out[out.length - 1]
    if (card && last?.kind === 'cards') last.cards.push(card)
    else if (card) out.push({ kind: 'cards', cards: [card] })
    else if (last?.kind === 'text') last.text += '\n\n' + reflow(para)
    else out.push({ kind: 'text', text: reflow(para) })
  }
  return out
}

/** Matnni jadval va oddiy matn bo'laklariga ajratadi; jadval — ketma-ket kamida 2 ta jadval qatori. */
function blocks(text: string): Block[] {
  const out: Block[] = []
  let buf: string[] = []
  let table: string[] = []
  const flushText = () => {
    if (buf.join('').trim()) out.push(...textBlocks(buf.join('\n').replace(/^\n+|\s+$/g, '')))
    buf = []
  }
  const flushTable = () => {
    if (table.length >= 2) {
      flushText()
      out.push({ kind: 'table', rows: table.filter((l) => !TABLE_RULE.test(l)).map(cells) })
    } else {
      buf.push(...table)
    }
    table = []
  }
  for (const line of text.split('\n')) {
    if (isTableRow(line)) {
      table.push(line)
    } else {
      flushTable()
      buf.push(line)
    }
  }
  flushTable()
  flushText()
  return out
}

function Table({ rows }: { rows: string[][] }) {
  const [head, ...body] = rows
  // uzun matnli ustun (izoh) o'raladi; qolganlari (raqam, kod, sana) bir qatorda
  const wraps = head.map((_, j) => body.some((r) => (r[j] ?? '').length > LONG_CELL))
  return (
    <div className="overflow-x-auto rounded-xl border border-border/60">
      <table className="w-full text-left text-xs tabular-nums">
        <thead className="bg-muted/60">
          <tr>{head.map((c, i) => <th key={i} className="whitespace-nowrap px-3 py-2 font-semibold">{c}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {body.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j} className={`px-3 py-1.5 align-top ${wraps[j] ? 'min-w-64' : 'whitespace-nowrap'}`}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CardLine({ line }: { line: string }) {
  const period = PERIOD.exec(line)
  if (period) {
    return (
      <li className="relative before:absolute before:-left-[1.3rem] before:top-[0.45rem] before:h-2 before:w-2 before:rounded-full before:bg-primary before:ring-4 before:ring-background">
        <span className="mr-2 whitespace-nowrap rounded-md bg-primary/10 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-primary">
          {period[1]} – {period[2]}
        </span>
        {period[3]}
      </li>
    )
  }
  const field = FIELD.exec(line)
  if (field) {
    return (
      <li>
        <span className="mr-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{field[1]}</span>
        {field[2]}
      </li>
    )
  }
  return <li>{line}</li>
}

function Cards({ cards }: { cards: Card[] }) {
  return (
    <div className="grid gap-3 py-1">
      {cards.map((c) => (
        <article key={c.badge + c.title} className="rounded-xl border border-border/60 bg-background/60 p-4 shadow-sm">
          <header className="mb-3 flex items-start gap-3">
            <span className="bg-brand grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold text-primary-foreground">
              {c.badge}
            </span>
            <div className="min-w-0">
              <h3 className="font-semibold leading-snug">{c.title}</h3>
              {c.subtitle && <p className="text-xs text-muted-foreground">{c.subtitle}</p>}
            </div>
          </header>
          <ul className="ml-[1.1rem] space-y-1.5 border-l border-border/60 pl-4">
            {c.lines.map((l, k) => <CardLine key={k} line={l} />)}
          </ul>
        </article>
      ))}
    </div>
  )
}

export default function RichText({ text, className = '' }: { text: string; className?: string }) {
  const parts = text.split(/```[a-z]*\n?/)
  return (
    <div className={`space-y-2 text-sm leading-relaxed ${className}`}>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <pre key={i} className="overflow-x-auto rounded-xl border border-border/60 bg-muted/70 p-4 font-mono text-xs leading-relaxed">
            {part.replace(/\n$/, '')}
          </pre>
        ) : (
          blocks(part).map((b, j) =>
            b.kind === 'table' ? (
              <Table key={`${i}-${j}`} rows={b.rows} />
            ) : b.kind === 'cards' ? (
              <Cards key={`${i}-${j}`} cards={b.cards} />
            ) : (
              <p key={`${i}-${j}`} className="whitespace-pre-wrap">{b.text}</p>
            ),
          )
        ),
      )}
    </div>
  )
}
