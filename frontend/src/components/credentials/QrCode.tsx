import { useEffect, useState } from 'react'
import QRCode from 'qrcode'

/** Havola uchun QR (SVG, tarmoqsiz — brauzerda yasaladi). */
export default function QrCode({ value, label, className = '' }: { value: string; label: string; className?: string }) {
  const [svg, setSvg] = useState('')

  useEffect(() => {
    let alive = true
    QRCode.toString(value, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#0d2a20', light: '#0000' } })
      .then((s) => alive && setSvg(s))
      .catch(() => alive && setSvg(''))
    return () => {
      alive = false
    }
  }, [value])

  // qrcode kutubxonasi o'zi yasagan SVG — tashqi matn yo'q
  return <div role="img" aria-label={label} className={className} dangerouslySetInnerHTML={{ __html: svg }} />
}
