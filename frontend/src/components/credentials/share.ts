import type { CertificatePublic } from '@/lib/types'
import { certificateUrl } from './CertificateSheet'

/** LinkedIn "Add license or certification" formasi oldindan to'ldirilgan holda. */
export function linkedInUrl(cert: CertificatePublic): string {
  const issued = new Date(cert.completed_at)
  const params = new URLSearchParams({
    startTask: 'CERTIFICATION_NAME',
    name: cert.scenario_title,
    organizationName: 'TryJob',
    issueYear: String(issued.getUTCFullYear()),
    issueMonth: String(issued.getUTCMonth() + 1),
    certUrl: certificateUrl(cert.code),
    certId: cert.code,
  })
  return `https://www.linkedin.com/profile/add?${params}`
}
