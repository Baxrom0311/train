import { useEffect, useState } from 'react'
import type { TFunction } from 'i18next'

/** 429 dan keyingi kutish (CONTRACT.md §30.4): qolgan soniyalar, 0 — tugma yana faol. */
export function useCooldown() {
  const [until, setUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (until === 0) return
    const timer = setInterval(() => {
      const t = Date.now()
      setNow(t)
      if (t >= until) clearInterval(timer)
    }, 1000)
    return () => clearInterval(timer)
  }, [until])
  const left = Math.max(0, Math.ceil((until - now) / 1000))
  const start = (seconds: number) => {
    setNow(Date.now())
    setUntil(Date.now() + seconds * 1000)
  }
  return { left, start }
}

/** Tugmadagi qolgan vaqt: 14:56 */
export function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** "Juda ko'p urinish — 14 daqiqadan keyin": daqiqa yuqoriga yaxlitlanadi. */
export function tooManyText(t: TFunction, seconds: number): string {
  return seconds >= 60
    ? t('account.tooMany.minutes', { count: Math.ceil(seconds / 60) })
    : t('account.tooMany.seconds', { count: seconds })
}
