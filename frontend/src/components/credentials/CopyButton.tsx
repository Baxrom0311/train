import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function CopyButton({ value, label, size = 'sm' }: { value: string; label?: string; size?: 'sm' | 'default' }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      window.prompt(t('cert.copyPrompt'), value)
    }
  }
  return (
    <Button type="button" variant="outline" size={size} onClick={copy}>
      {copied ? <Check className="h-4 w-4 text-success" /> : <Link2 className="h-4 w-4" />}
      {copied ? t('cert.copied') : label ?? t('cert.copyLink')}
    </Button>
  )
}
