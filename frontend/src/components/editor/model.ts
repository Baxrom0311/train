// Ssenariy ta'rifi (backend/app/scenario/schema.py, CONTRACT.md §9.3) va muharrir yordamchilari (§16).
import type { Competency, NodeType, Sector } from '@/lib/types'

export type AnswerType = 'text' | 'file' | 'link' | 'code'
export const ANSWER_TYPES: AnswerType[] = ['text', 'file', 'link', 'code']
export const NODE_TYPES: NodeType[] = ['message', 'task', 'incident', 'decision', 'day_end']
export const DIFFICULTIES = ['junior', 'middle', 'senior'] as const
export type Difficulty = (typeof DIFFICULTIES)[number]
export type Grade = 'correct' | 'acceptable' | 'wrong'

export interface PersonaDef {
  key: string
  name: string
  role: string
  kind: 'colleague' | 'mentor'
  tone: string
  knows: string[]
  secrets: string[]
  busy_reply?: string
  deflect_reply?: string
  nudge_reply?: string
}

export interface DocumentDef {
  key: string
  title: string
  content: string
}

export interface RubricDef {
  id: string
  description: string
  weight: number
}

export interface OptionDef {
  key: string
  label: string
  grade: Grade
  flag: string | null
}

export interface AfterDef {
  node: string
  event: 'delivered' | 'submitted'
  minutes: number
}

// §9.3.3 — cheklangan DSL
export type Leaf =
  | { score_lt: { node: string; value: number } }
  | { score_gte: { node: string; value: number } }
  | { missed: string }
  | { submitted: string }
  | { chose: { node: string; option: string } }
  | { flag: string }
export type Condition = Leaf | { all: Condition[] } | { any: Condition[] }

export interface NodeDef {
  id: string
  type: NodeType
  day: number | null
  at: string | null
  after: AfterDef | null
  when: Condition | null
  from: string | null
  brief: string
  attachments: string[]
  answer_types: AnswerType[]
  due_in_minutes: number | null
  weight: number
  competencies: Competency[]
  rubric: RubricDef[]
  checks: Record<string, unknown> | null
  hints: string[]
  reference_answer: string | null
  options: OptionDef[]
  max_attempts: number
  late_penalty: number
  hint_penalty: number
}

export interface ScenarioDef {
  slug: string
  title: string
  sector: Sector
  company_name: string
  difficulty: Difficulty
  duration_days: number
  personas: PersonaDef[]
  documents: DocumentDef[]
  nodes: NodeDef[]
}

// ── API (backend/app/api/scenario_admin.py) ─────────────────────────

export type VersionStatus = 'draft' | 'published' | 'archived'
export type Path = (string | number)[]

export interface FieldError {
  path: Path
  message: string
}

export interface VersionInfo {
  version: number
  status: VersionStatus
  created_at: string
  published_at: string | null
}

export interface ScenarioAdmin {
  id: string
  slug: string
  title: string
  sector: Sector
  company_name: string
  duration_days: number
  is_active: boolean
  runs: number
  versions: VersionInfo[]
}

export interface VersionOut extends VersionInfo {
  scenario_id: string
  definition: ScenarioDef
  warnings: string[]
}

export interface Summary {
  days: number
  nodes: number
  graded: number
  personas: number
  documents: number
  mentor: boolean
}

export interface Validation {
  ok: boolean
  errors: FieldError[]
  warnings: string[]
  summary: Summary | null
}

// ── Yangi elementlar ────────────────────────────────────────────────

export const GRADED: NodeType[] = ['task', 'incident', 'decision', 'day_end']
export const ANSWERED: NodeType[] = ['task', 'incident']

export function blankNode(type: NodeType, id: string, day = 1): NodeDef {
  return {
    id, type, day, at: type === 'day_end' ? '17:30' : '10:00', after: null, when: null, from: null,
    brief: '', attachments: [],
    answer_types: ANSWERED.includes(type) ? ['text'] : [],
    due_in_minutes: ANSWERED.includes(type) ? 60 : null,
    weight: 1, competencies: [], rubric: [], checks: null, hints: [], reference_answer: null,
    options: type === 'decision'
      ? [{ key: 'a', label: '', grade: 'correct', flag: null }, { key: 'b', label: '', grade: 'wrong', flag: null }]
      : [],
    max_attempts: 3, late_penalty: 0.2, hint_penalty: 0.1,
  }
}

export function blankPersona(key: string): PersonaDef {
  return { key, name: '', role: '', kind: 'colleague', tone: '', knows: [], secrets: [] }
}

/** Yangi ssenariy: tekshiruvdan o'tadigan eng kichik skelet (1 kun, rahbar, salom va kun yakuni). */
export function templateScenario(): ScenarioDef {
  const lead: PersonaDef = { ...blankPersona('lead'), name: 'Rahbar', role: 'Team Lead' }
  const welcome = { ...blankNode('message', 'welcome'), at: '09:00', from: 'lead', brief: 'Xush kelibsiz! Bugungi reja bilan tanishing.' }
  const end = { ...blankNode('day_end', 'day1_end'), brief: 'Kun yakuni: bugun nima qildingiz va ertaga nima qilasiz?' }
  return {
    slug: '', title: '', sector: 'IT', company_name: '', difficulty: 'junior', duration_days: 1,
    personas: [lead], documents: [], nodes: [welcome, end],
  }
}

/** `base`, `base_2`, `base_3`... — band bo'lmagan birinchi kalit. */
export function uniqueKey(base: string, taken: string[]): string {
  if (!taken.includes(base)) return base
  for (let i = 2; ; i++) if (!taken.includes(`${base}_${i}`)) return `${base}_${i}`
}

// ── Vaqt chizig'i ───────────────────────────────────────────────────

export interface TimelineRow {
  index: number
  depth: number
}

/**
 * Node'lar kunlar bo'yicha: `day`+`at` vaqt tartibida, `after` bilan keladiganlari
 * o'z "langari" ostida. Langari topilmaganlar (noma'lum node, sikl) — `loose`.
 */
export function timeline(nodes: NodeDef[]): { days: Map<number, TimelineRow[]>; loose: number[] } {
  const children = new Map<string, number[]>()
  nodes.forEach((n, i) => {
    if (n.after) children.set(n.after.node, [...(children.get(n.after.node) ?? []), i])
  })
  const placed = new Set<number>()
  const walk = (i: number, depth: number, out: TimelineRow[]) => {
    if (placed.has(i)) return
    placed.add(i)
    out.push({ index: i, depth })
    const kids = [...(children.get(nodes[i].id) ?? [])].sort((a, b) => (nodes[a].after?.minutes ?? 0) - (nodes[b].after?.minutes ?? 0))
    kids.forEach((k) => walk(k, depth + 1, out))
  }
  const days = new Map<number, TimelineRow[]>()
  nodes
    .map((n, i) => ({ n, i }))
    .filter(({ n }) => !n.after && n.day != null)
    .sort((a, b) => (a.n.day! - b.n.day!) || (a.n.at ?? '').localeCompare(b.n.at ?? '') || (a.n.type === 'day_end' ? 1 : 0) - (b.n.type === 'day_end' ? 1 : 0))
    .forEach(({ n, i }) => {
      const rows = days.get(n.day!) ?? []
      walk(i, 0, rows)
      days.set(n.day!, rows)
    })
  const loose = nodes.map((_, i) => i).filter((i) => !placed.has(i))
  return { days, loose }
}

// ── Xatolarni muharrir joyiga bog'lash ──────────────────────────────

export type Section = 'general' | 'personas' | 'documents' | 'nodes'
export interface ErrorTarget {
  section: Section
  index?: number
  field?: string
}

const GENERAL_FIELDS = ['slug', 'title', 'sector', 'company_name', 'difficulty', 'duration_days']

/**
 * Xato qayerga tegishli: maydon xatosida — Pydantic yo'li (`["nodes", 3, "due_in_minutes"]`),
 * ta'rif darajasidagida — xabar boshidagi node id yoki `persona <key>:` (CONTRACT.md §16.2).
 */
export function locate(error: FieldError, defn: ScenarioDef): ErrorTarget {
  const [head, index, field] = error.path
  if (head === 'nodes' || head === 'personas' || head === 'documents') {
    return { section: head, index: typeof index === 'number' ? index : undefined, field: typeof field === 'string' ? field : undefined }
  }
  if (typeof head === 'string' && GENERAL_FIELDS.includes(head)) return { section: 'general', field: head }
  const persona = /^persona (\w+):/.exec(error.message)
  if (persona) {
    const i = defn.personas.findIndex((p) => p.key === persona[1])
    return { section: 'personas', index: i >= 0 ? i : undefined }
  }
  const prefix = /^(\w+):/.exec(error.message)
  if (prefix) {
    const i = defn.nodes.findIndex((n) => n.id === prefix[1])
    if (i >= 0) return { section: 'nodes', index: i }
  }
  // `persona kaliti takrorlangan`, `ko'pi bilan bitta mentor`, `2-kun uchun aynan bitta day_end`...
  if (/^persona|mentor/.test(error.message)) return { section: 'personas' }
  if (/^document/.test(error.message)) return { section: 'documents' }
  if (/^node|kun|day_end|after/.test(error.message)) return { section: 'nodes' }
  return { section: 'general' }
}

/** Xabardan takroriy `node_id:` boshini olib tashlash (node formasi ichida ko'rsatilganda). */
export const stripPrefix = (message: string, id: string) => message.replace(new RegExp(`^${id}: `), '')

export function errorsFor(errors: FieldError[], defn: ScenarioDef, section: Section, index?: number): (FieldError & ErrorTarget)[] {
  return errors
    .map((e) => ({ ...e, ...locate(e, defn) }))
    .filter((e) => e.section === section && (index === undefined || e.index === index))
}

// ── Kalitni qayta nomlash: havolalar ham yangilanadi ────────────────

function mapCondition(c: Condition, f: (id: string) => string): Condition {
  if ('all' in c) return { all: c.all.map((x) => mapCondition(x, f)) }
  if ('any' in c) return { any: c.any.map((x) => mapCondition(x, f)) }
  if ('score_lt' in c) return { score_lt: { ...c.score_lt, node: f(c.score_lt.node) } }
  if ('score_gte' in c) return { score_gte: { ...c.score_gte, node: f(c.score_gte.node) } }
  if ('missed' in c) return { missed: f(c.missed) }
  if ('submitted' in c) return { submitted: f(c.submitted) }
  if ('chose' in c) return { chose: { ...c.chose, node: f(c.chose.node) } }
  return c
}

const swap = (from: string, to: string) => (x: string) => (x === from ? to : x)

export function renamePersona(d: ScenarioDef, i: number, to: string): ScenarioDef {
  const from = d.personas[i].key
  return {
    ...d,
    personas: d.personas.map((p, j) => (j === i ? { ...p, key: to } : p)),
    nodes: d.nodes.map((n) => (n.from === from ? { ...n, from: to } : n)),
  }
}

export function renameDocument(d: ScenarioDef, i: number, to: string): ScenarioDef {
  const f = swap(d.documents[i].key, to)
  return {
    ...d,
    documents: d.documents.map((x, j) => (j === i ? { ...x, key: to } : x)),
    personas: d.personas.map((p) => ({ ...p, knows: p.knows.map(f) })),
    nodes: d.nodes.map((n) => ({ ...n, attachments: n.attachments.map(f) })),
  }
}

export function renameNode(d: ScenarioDef, i: number, to: string): ScenarioDef {
  const f = swap(d.nodes[i].id, to)
  return {
    ...d,
    nodes: d.nodes.map((n, j) => ({
      ...n,
      id: j === i ? to : n.id,
      after: n.after ? { ...n.after, node: f(n.after.node) } : null,
      when: n.when ? mapCondition(n.when, f) : null,
    })),
  }
}

/** Tur o'zgarganda sxemaga zid maydonlar tozalanadi, kerakli bo'sh maydonlar to'ldiriladi (§9.3). */
export function retypeNode(n: NodeDef, type: NodeType): NodeDef {
  const blank = blankNode(type, n.id, n.day ?? 1)
  const answered = ANSWERED.includes(type)
  const graded = GRADED.includes(type)
  return {
    ...n,
    type,
    answer_types: answered ? (n.answer_types.length ? n.answer_types : blank.answer_types) : [],
    due_in_minutes: type === 'message' ? null : answered ? n.due_in_minutes ?? blank.due_in_minutes : n.due_in_minutes,
    options: type === 'decision' ? (n.options.length >= 2 ? n.options : blank.options) : [],
    rubric: graded ? n.rubric : [],
    hints: graded ? n.hints : [],
    reference_answer: graded ? n.reference_answer : null,
    // day_end faqat `day`+`at` bilan
    ...(type === 'day_end' && n.after ? { after: null, day: blank.day, at: blank.at } : {}),
  }
}

// ── YAML'dan kelgan (sxemadan o'tmagan bo'lishi mumkin) ta'rifni forma shakliga keltirish ──

type Raw = Record<string, unknown>
const obj = (v: unknown): Raw => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Raw) : {})
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])

const NODE_DEFAULTS: Omit<NodeDef, 'id' | 'type'> = {
  day: null, at: null, after: null, when: null, from: null, brief: '', attachments: [], answer_types: [],
  due_in_minutes: null, weight: 1, competencies: [], rubric: [], checks: null, hints: [], reference_answer: null,
  options: [], max_attempts: 3, late_penalty: 0.2, hint_penalty: 0.1,
}

/**
 * Yetishmagan maydonlarga standart qiymat: forma har doim to'liq shakl bilan ishlaydi.
 * Noto'g'ri qiymatlar (masalan, raqam o'rniga matn) o'zgartirilmaydi — tekshiruv ularni ko'rsatadi.
 */
export function normalize(raw: unknown): ScenarioDef {
  const d = obj(raw)
  const base = templateScenario()
  return {
    ...base,
    ...d,
    personas: arr(d.personas).map((p) => {
      const persona = obj(p)
      return { ...blankPersona(''), ...persona, knows: arr(persona.knows), secrets: arr(persona.secrets) } as PersonaDef
    }),
    documents: arr(d.documents).map((x) => ({ key: '', title: '', content: '', ...obj(x) }) as DocumentDef),
    nodes: arr(d.nodes).map((n) => {
      const node = obj(n)
      return {
        id: '', type: 'message', ...NODE_DEFAULTS, ...node,
        attachments: arr(node.attachments), answer_types: arr(node.answer_types),
        competencies: arr(node.competencies), hints: arr(node.hints),
        options: arr(node.options).map((o) => ({ key: '', label: '', grade: 'acceptable', flag: null, ...obj(o) })),
        rubric: arr(node.rubric).map((c) => ({ id: '', description: '', weight: 1, ...obj(c) })),
      } as NodeDef
    }),
  } as ScenarioDef
}
