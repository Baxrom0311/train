// Test ma'lumotlari backend domen kodi orqali (`tools/e2e/seed.py`, CONTRACT.md §34.2).
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const SEED = fileURLToPath(new URL('../../../tools/e2e/seed.sh', import.meta.url))

export const PASSWORD = 'E2e-Parol-12345'

export interface Account {
  email: string
  password: string
  name: string
  userId: string
}

function seed(args: string[]): Record<string, unknown> {
  const out = execFileSync('bash', [SEED, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
  // oxirgi qator — natija JSON'i (oldingi qatorlar log bo'lishi mumkin)
  return JSON.parse(out.trim().split('\n').at(-1) ?? '{}')
}

export interface ErrorGroup { source: string; title: string; location: string; count: number }

/** Ochiq xato guruhlari (§32.3): API 5xx, worker job xatosi, brauzer xatosi (`lib/monitoring.ts`). */
export function openErrors(): ErrorGroup[] {
  return seed(['errors']).errors as unknown as ErrorGroup[]
}

/** Har test o'z foydalanuvchilarini oladi — testlar bir-biriga va qayta ishga tushirishga bog'liq emas. */
export function uniqueTag(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`
}

/** Email tasdiqlangan talaba; `completed` — shu ssenariydan tugallangan Run (profil, sertifikat bilan). */
export function seedStudent(name: string, opts: { completed?: string } = {}): Account {
  const email = `talaba-${uniqueTag()}@e2e.tryjob.uz`
  const args = ['student', '--email', email, '--password', PASSWORD, '--name', name]
  if (opts.completed) args.push('--completed', opts.completed)
  const out = seed(args)
  return { email, password: PASSWORD, name, userId: String(out.user_id) }
}

/** Tasdiqlangan kompaniya va uning HR xodimi. */
export function seedCompany(name: string, company: string): Account & { company: string } {
  const email = `hr-${uniqueTag()}@e2e.tryjob.uz`
  const out = seed(['company', '--email', email, '--password', PASSWORD, '--name', name, '--company', company])
  return { email, password: PASSWORD, name, userId: String(out.user_id), company }
}
