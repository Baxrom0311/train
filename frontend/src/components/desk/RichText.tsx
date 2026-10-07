// Ssenariy matni: oddiy matn, ``` bilan o'ralgan kod bloklari va `a | b | c` jadvallar
// (markdown parser shart emas).

const LIST_ITEM = /^\s*([-•*]|\d+[.)]|[A-Za-z][.)])\s/
const TABLE_RULE = /^\s*\|?\s*:?-{2,}/
const LONG_CELL = 32

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

type Block = { kind: 'text'; text: string } | { kind: 'table'; rows: string[][] }

/** Matnni jadval va oddiy matn bo'laklariga ajratadi; jadval — ketma-ket kamida 2 ta jadval qatori. */
function blocks(text: string): Block[] {
  const out: Block[] = []
  let buf: string[] = []
  let table: string[] = []
  const flushText = () => {
    if (buf.join('').trim()) out.push({ kind: 'text', text: reflow(buf.join('\n').trim()) })
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
            ) : (
              <p key={`${i}-${j}`} className="whitespace-pre-wrap">{b.text}</p>
            ),
          )
        ),
      )}
    </div>
  )
}
