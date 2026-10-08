import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** Ekranga kirganda bir marta yumshoq paydo bo'ladi; `delay` — ketma-ket kartalar uchun (ms). */
export default function Reveal({ children, className, delay = 0 }: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined')

  useEffect(() => {
    const el = ref.current
    if (!el || visible) return
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setVisible(true)
        io.disconnect()
      }
    }, { rootMargin: '0px 0px -8% 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [visible])

  return (
    <div ref={ref} style={delay ? { transitionDelay: `${delay}ms` } : undefined}
      className={cn('landing-reveal', visible && 'is-visible', className)}>
      {children}
    </div>
  )
}
