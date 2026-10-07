// Ssenariy matni: oddiy matn + ``` bilan o'ralgan kod bloklari (markdown parser shart emas).

const LIST_ITEM = /^\s*([-•*]|\d+[.)])\s/

/** YAML `|` bloklaridagi qator uzilishlari — abzas ichida bo'sh joy; ro'yxat bandlari alohida qatorda qoladi. */
export function reflow(text: string): string {
  return text
    .split(/\n{2,}/)
    .map((para) =>
      para
        .split('\n')
        .reduce((out, line, i) => (i === 0 ? line : out + (LIST_ITEM.test(line) ? '\n' : ' ') + line.trim()), ''),
    )
    .join('\n\n')
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
          part.trim() && (
            <p key={i} className="whitespace-pre-wrap">
              {reflow(part.trim())}
            </p>
          )
        ),
      )}
    </div>
  )
}
