// Butun ilova orqasidagi sekin harakatlanuvchi yorug'lik (glass qatlamlari shuni "sindiradi").
// Ranglar CSS o'zgaruvchilaridan: kunduz — yashil, tun — sariq; ish stolida kun qismiga qarab.
export default function Backdrop() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-[10%] -top-[15%] h-[55vmax] w-[55vmax] rounded-full opacity-45 blur-3xl animate-drift-1 dark:opacity-25"
        style={{ background: 'radial-gradient(circle, hsl(var(--glow-1)) 0%, transparent 65%)' }} />
      <div className="absolute -right-[15%] top-[10%] h-[50vmax] w-[50vmax] rounded-full opacity-40 blur-3xl animate-drift-2 dark:opacity-20"
        style={{ background: 'radial-gradient(circle, hsl(var(--glow-2)) 0%, transparent 65%)' }} />
      <div className="absolute -bottom-[25%] left-[25%] h-[45vmax] w-[45vmax] rounded-full opacity-35 blur-3xl animate-drift-3 dark:opacity-30"
        style={{ background: 'radial-gradient(circle, hsl(var(--glow-3)) 0%, transparent 65%)' }} />
      {/* yengil nuqtali to'r — chuqurlik hissi */}
      <div className="absolute inset-0 opacity-[0.35] dark:opacity-[0.18]"
        style={{ backgroundImage: 'radial-gradient(hsl(var(--foreground) / 0.08) 1px, transparent 1px)', backgroundSize: '22px 22px' }} />
    </div>
  )
}
