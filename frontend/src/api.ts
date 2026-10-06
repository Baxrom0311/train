import axios from 'axios';
import { 
  Simulation, 
  SubmissionResponse, 
  CertificateData, 
  CaseCup, 
  LeaderboardEntry, 
  CandidateProfile, 
  TalentOffer, 
  UniversityStats 
} from './types';

const API_BASE = '/api/v1';

export const api = axios.create({
  baseURL: API_BASE,
});

// Auto attach token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tryjob_token') || localStorage.getItem('train_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh token queue and mutex
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Automatic 401 Interceptor with Refresh Token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and request hasn't been retried yet
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/refresh')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('tryjob_refresh_token') || localStorage.getItem('train_refresh_token');

      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token, refresh_token: newRefreshToken, user } = res.data;
          if (access_token) {
            localStorage.setItem('tryjob_token', access_token);
            localStorage.setItem('train_token', access_token);
            if (newRefreshToken) {
              localStorage.setItem('tryjob_refresh_token', newRefreshToken);
              localStorage.setItem('train_refresh_token', newRefreshToken);
            }
            if (user) {
              localStorage.setItem('tryjob_auth_user', JSON.stringify(user));
            }

            api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
            processQueue(null, access_token);
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return api(originalRequest);
          }
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          // Token expired completely - clear credentials
          localStorage.removeItem('tryjob_token');
          localStorage.removeItem('tryjob_refresh_token');
          localStorage.removeItem('train_token');
          localStorage.removeItem('train_refresh_token');
          localStorage.removeItem('tryjob_auth_user');
          return Promise.reject(refreshErr);
        } finally {
          isRefreshing = false;
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auto demo login helper
export async function ensureAuth(): Promise<string> {
  let token = localStorage.getItem('tryjob_token') || localStorage.getItem('train_token');
  if (!token) {
    try {
      const res = await axios.post(`${API_BASE}/auth/login`, {
        email: 'student@train.uz',
        password: 'student123'
      });
      token = res.data.access_token;
      const refreshToken = res.data.refresh_token;
      if (token) {
        localStorage.setItem('tryjob_token', token);
        localStorage.setItem('train_token', token);
      }
      if (refreshToken) {
        localStorage.setItem('tryjob_refresh_token', refreshToken);
        localStorage.setItem('train_refresh_token', refreshToken);
      }
    } catch (e) {
      console.error('Auto login error:', e);
    }
  }
  return token || '';
}

export function getCustomSimulations(): Simulation[] {
  try {
    return JSON.parse(localStorage.getItem('tryjob_custom_simulations') || '[]');
  } catch (e) {
    return [];
  }
}

export function saveCustomSimulation(sim: Simulation): Simulation {
  const customs = getCustomSimulations();
  const existingIdx = customs.findIndex(s => s.id === sim.id || s.slug === sim.slug);
  if (existingIdx >= 0) {
    customs[existingIdx] = sim;
  } else {
    customs.unshift(sim);
  }
  localStorage.setItem('tryjob_custom_simulations', JSON.stringify(customs));
  return sim;
}

export async function fetchSimulations(category?: string): Promise<Simulation[]> {
  const customList = getCustomSimulations();
  let serverList: Simulation[] = [];
  try {
    const params = category && category !== 'all' ? { category } : {};
    const res = await api.get<Simulation[]>('/simulations', { params });
    serverList = res.data || [];
  } catch (e) {
    console.warn('Could not fetch server simulations, using custom & fallback', e);
  }

  // Merge custom simulations
  const combined = [...customList, ...serverList.filter(s => !customList.some(c => c.slug === s.slug))];
  if (category && category !== 'all') {
    return combined.filter(s => s.category.toLowerCase().includes(category.toLowerCase()));
  }
  return combined;
}

export async function fetchSimulationDetail(slug: string): Promise<Simulation> {
  const customList = getCustomSimulations();
  const localMatch = customList.find(s => s.slug === slug || s.id === slug);
  if (localMatch) {
    return localMatch;
  }
  const res = await api.get<Simulation>(`/simulations/${slug}`);
  return res.data;
}

export async function runPythonSandbox(code: string): Promise<{ success: boolean; output: string; error?: string; execution_time_ms: number }> {
  const res = await api.post('/tools/sandbox', { code, timeout_seconds: 5.0 });
  return res.data;
}

export async function submitTaskSolution(
  simulationId: string,
  taskId: string,
  submittedText: string,
  file?: File
): Promise<SubmissionResponse> {
  await ensureAuth();
  const formData = new FormData();
  formData.append('simulation_id', simulationId);
  formData.append('task_id', taskId);
  formData.append('submitted_text', submittedText);
  if (file) {
    formData.append('file', file);
  }
  const res = await api.post<SubmissionResponse>('/submissions', formData);
  return res.data;
}

export async function submitMockInterview(
  simulationSlug: string,
  question: string,
  studentAnswer: string
): Promise<{ score: number; feedback: string }> {
  const res = await api.post('/tools/mock-interview', {
    simulation_slug: simulationSlug,
    question,
    student_answer: studentAnswer
  });
  return res.data;
}

export async function issueCertificate(simulationId: string): Promise<CertificateData> {
  await ensureAuth();
  const res = await api.post<CertificateData>('/certificates/issue', { simulation_id: simulationId });
  return res.data;
}

export async function verifyCertificate(certUuid: string): Promise<{
  is_valid: boolean;
  cert_uuid: string;
  student_name: string;
  simulation_title: string;
  company_name: string;
  score: number;
  issued_at: string;
}> {
  const res = await api.get(`/certificates/verify/${certUuid}`);
  return res.data;
}

// ── Case Cup API ──────────────────────────────────────────────────────────
export async function getCaseCups(): Promise<CaseCup[]> {
  try {
    const res = await api.get<CaseCup[]>('/case-cups');
    if (res.data && res.data.length > 0) return res.data;
  } catch (e) {
    // fallback to rich mock data
  }
  return [
    {
      id: 'cup-1',
      title: 'Uzum Fintech & Payments Challenge 2026',
      slug: 'uzum-fintech-challenge-2026',
      host_company: 'Uzum Market & Bank',
      company_logo: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=120&h=120&fit=crop',
      prize_pool: '50,000,000 UZS',
      prize_distribution: [
        { rank: '1-o\'rin', prize: '25,000,000 UZS + Uzum Bank Fast-track Job Offer' },
        { rank: '2-o\'rin', prize: '15,000,000 UZS + Uzum Pro Merch Pack & MacBook' },
        { rank: '3-o\'rin', prize: '10,000,000 UZS + Yillik amaliyot shartnomasi' },
      ],
      start_date: '10 Oktyabr, 2026',
      deadline: '28 Oktyabr, 2026',
      participants_count: 428,
      status: 'active',
      difficulty: 'Middle',
      category: 'Fintech & Dasturlash',
      description: 'Uzum ekotizimi uchun 100k+ RPS yuklamani ko\'taruvchi tranzaksiyalar gateway arxitekturasi va AI fraud-monitoring tizimini ishlab chiqish keysi.',
      tasks_count: 4,
      rules: [
        'Har bir bosqich topshirig\'i AI validator va Uzum muhandislari tomonidan tekshiriladi.',
        'Kodni GitHub repo orqali yuklash va arxitektura hisobotini topshirish shart.',
        'Plagiat va boshqa ishtirokchilar kodini nusxalash avtomatik diskvalifikatsiyaga sabab bo\'ladi.'
      ],
      stages: [
        { stage: 1, title: 'Database & Redis Caching optimallashtirish', date: '10-15 Oktyabr' },
        { stage: 2, title: 'Real-time Anti-Fraud Rule Engine qurish', date: '16-20 Oktyabr' },
        { stage: 3, title: 'High-load stress test & API Gateway', date: '21-25 Oktyabr' },
        { stage: 4, title: 'Final Pitch va Uzum hakamlar hay\'atiga taqdimot', date: '28 Oktyabr' },
      ],
      tags: ['Fintech', 'Golang / Python', 'Redis', 'Anti-Fraud', 'Microservices']
    },
    {
      id: 'cup-2',
      title: 'Payme National AI Security Hackathon',
      slug: 'payme-ai-security-hackathon',
      host_company: 'Payme Uzbekistan',
      company_logo: 'https://images.unsplash.com/photo-1563986768609-322da13575f3?w=120&h=120&fit=crop',
      prize_pool: '35,000,000 UZS',
      prize_distribution: [
        { rank: '1-o\'rin', prize: '18,000,000 UZS + Payme CyberSec Team Invite' },
        { rank: '2-o\'rin', prize: '10,000,000 UZS + Maxsus sovg\'alar' },
        { rank: '3-o\'rin', prize: '7,000,000 UZS + Xavfsizlik bo\'yicha xalqaro sertifikat' },
      ],
      start_date: '15 Oktyabr, 2026',
      deadline: '5 Noyabr, 2026',
      participants_count: 310,
      status: 'active',
      difficulty: 'Advanced',
      category: 'Kiberxavfsizlik & AI',
      description: 'P2P o\'tkazmalardagi shubhali xatti-harakatlarni mashinali o\'rganish modellari bilan aniqlash va SQL Injection/XSS zaifliklarini bartaraf etish keysi.',
      tasks_count: 3,
      rules: [
        'Ishlatiladigan modellar F1-score > 0.94 aniqlikda bo\'lishi shart.',
        'Xavfsizlik audit xulosasi OWASP Top 10 standartiga mos kelishi lozim.'
      ],
      stages: [
        { stage: 1, title: 'OWASP Security Audit & Vulnerability Assessment', date: '15-22 Oktyabr' },
        { stage: 2, title: 'Anomaly Detection ML Model Training', date: '23-30 Oktyabr' },
        { stage: 3, title: 'Live Pen-test Defence Arena', date: '5 Noyabr' }
      ],
      tags: ['Cybersecurity', 'Machine Learning', 'OWASP', 'FastAPI']
    },
    {
      id: 'cup-3',
      title: 'PwC Central Asia Financial Audit Cup',
      slug: 'pwc-financial-audit-cup',
      host_company: 'PwC Uzbekistan',
      company_logo: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=120&h=120&fit=crop',
      prize_pool: '30,000,000 UZS',
      prize_distribution: [
        { rank: '1-o\'rin', prize: '15,000,000 UZS + PwC Junior Associate Offer' },
        { rank: '2-o\'rin', prize: '9,000,000 UZS + ACCA Study Sponsorship' },
        { rank: '3-o\'rin', prize: '6,000,000 UZS + Mentorlik dasturi' },
      ],
      start_date: '1 Noyabr, 2026',
      deadline: '20 Noyabr, 2026',
      participants_count: 245,
      status: 'upcoming',
      difficulty: 'Junior',
      category: 'Audit & Moliya',
      description: 'Katta korporatsiyaning MHXS (IFRS) hisobotlarini tekshirish, EBITDA tahlili va soliq tavakkalchiliklarini modellashtirish.',
      tasks_count: 3,
      rules: [
        'Excel moliyaviy modeli dinamik va audit talablariga mos tuzilgan bo\'lishi kerak.',
        'Xulosa memorandumida raqamlar manbasi ko\'rsatilishi zarur.'
      ],
      stages: [
        { stage: 1, title: 'Balans va Pul oqimlari auditi', date: '1-7 Noyabr' },
        { stage: 2, title: 'Soliq risklari tahlili', date: '8-14 Noyabr' },
        { stage: 3, title: 'Rahbariyat uchun boshqaruv xulosasi', date: '15-20 Noyabr' }
      ],
      tags: ['IFRS', 'Financial Modeling', 'Excel / PowerBI', 'Tax Risk']
    },
    {
      id: 'cup-4',
      title: 'Click Digital Banking UX & Product Cup',
      slug: 'click-digital-banking-cup',
      host_company: 'Click Uzbekistan',
      company_logo: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=120&h=120&fit=crop',
      prize_pool: '25,000,000 UZS',
      prize_distribution: [
        { rank: '1-o\'rin', prize: '12,000,000 UZS + Click Product Manager Internship' },
        { rank: '2-o\'rin', prize: '8,000,000 UZS + Click Premium gadget' },
        { rank: '3-o\'rin', prize: '5,000,000 UZS + Kurs grantlari' },
      ],
      start_date: '10 Noyabr, 2026',
      deadline: '30 Noyabr, 2026',
      participants_count: 180,
      status: 'upcoming',
      difficulty: 'Barcha darajalar',
      category: 'Product Management & UI/UX',
      description: '10 million foydalanuvchiga ega mobil ilova uchun mikro-kreditlar va keshbek tizimi mahsulot metrikalarini oshirish strategiyasi.',
      tasks_count: 3,
      rules: [
        'Mahsulot prototipi Figma da to\'liq interaktiv holatda topshirilishi kerak.',
        'Unit economics va CJM asoslangan bo\'lishi lozim.'
      ],
      stages: [
        { stage: 1, title: 'Customer Journey Map & User Research', date: '10-16 Noyabr' },
        { stage: 2, title: 'Figma Interactive Prototype & Design System', date: '17-23 Noyabr' },
        { stage: 3, title: 'A/B Testing & Unit Economics', date: '24-30 Noyabr' }
      ],
      tags: ['Product Management', 'Figma', 'CJM', 'Unit Economics']
    }
  ];
}

// ── Leaderboard API ───────────────────────────────────────────────────────
export async function getLeaderboard(category?: string): Promise<LeaderboardEntry[]> {
  try {
    const res = await api.get<LeaderboardEntry[]>('/leaderboard', { params: category ? { category } : {} });
    if (res.data && res.data.length > 0) return res.data;
  } catch (e) {
    // fallback
  }

  const baseLeaderboard: LeaderboardEntry[] = [
    {
      rank: 1,
      user_name: 'Jasurbek Aliyev',
      university: 'UrDU (Urganch davlat universiteti)',
      score: 98.4,
      completed_simulations: 7,
      badges: ['🏆 3x Case Cup Winner', '🔥 Top 1% Developer', '⚡ Python Guru'],
      avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop',
      solved_at: 'Bugun, 18:24',
      category: 'Backend & Data',
      is_verified_talent: true
    },
    {
      rank: 2,
      user_name: 'Madina Karimova',
      university: 'Westminster Xalqaro Universiteti (WIUT)',
      score: 97.2,
      completed_simulations: 6,
      badges: ['💎 PwC Audit Master', '⭐ Top Analyst', '📊 Financial Model Pro'],
      avatar_url: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&h=100&fit=crop',
      solved_at: 'Kecha, 21:10',
      category: 'Moliya & Audit',
      is_verified_talent: true
    },
    {
      rank: 3,
      user_name: 'Bobur Mirzayev',
      university: 'Inha Universiteti Toshkent (IUT)',
      score: 96.8,
      completed_simulations: 6,
      badges: ['🛡️ CyberSec Champion', '🚀 React & Node Ace', '⚡ Algoritmist'],
      avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop',
      solved_at: '2 kun oldin',
      category: 'Full-stack & Security',
      is_verified_talent: true
    },
    {
      rank: 4,
      user_name: 'Shahnoza Ergasheva',
      university: 'TDIU (Toshkent Davlat Iqtisodiyot Universiteti)',
      score: 94.5,
      completed_simulations: 5,
      badges: ['📈 Data Driven', '💡 Biznes Tahlilchi'],
      avatar_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop',
      solved_at: '3 kun oldin',
      category: 'Moliya & Audit',
      is_verified_talent: true
    },
    {
      rank: 5,
      user_name: 'Sardor Qodirov',
      university: 'Amity Universiteti Toshkent',
      score: 93.9,
      completed_simulations: 5,
      badges: ['🤖 AI Innovator', '⚡ ML Engineer'],
      avatar_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop',
      solved_at: '4 kun oldin',
      category: 'Backend & Data',
      is_verified_talent: false
    },
    {
      rank: 6,
      user_name: 'Dilnoza Yusupova',
      university: 'O\'zMU (O\'zbekiston Milliy Universiteti)',
      score: 92.7,
      completed_simulations: 4,
      badges: ['⚖️ Korporativ Huquq', '📝 Contract Pro'],
      avatar_url: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=100&h=100&fit=crop',
      solved_at: '5 kun oldin',
      category: 'Huquq & Compliance',
      is_verified_talent: true
    },
    {
      rank: 7,
      user_name: 'Akmal Normatov',
      university: 'Turin Politexnika Universiteti (TTPU)',
      score: 91.3,
      completed_simulations: 4,
      badges: ['🛠️ System Architect', '⚡ DevOps Novice'],
      avatar_url: 'https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=100&h=100&fit=crop',
      solved_at: '1 hafta oldin',
      category: 'Backend & Data',
      is_verified_talent: false
    }
  ];

  if (!category || category === 'all') return baseLeaderboard;
  return baseLeaderboard.filter(e => e.category?.toLowerCase().includes(category.toLowerCase()));
}

// ── HR Talent Hunt API ────────────────────────────────────────────────────
export async function getTalentCandidates(filters?: {
  skill?: string;
  minScore?: number;
  university?: string;
  vipOnly?: boolean;
}): Promise<CandidateProfile[]> {
  try {
    const res = await api.get<CandidateProfile[]>('/talents', { params: filters });
    if (res.data && res.data.length > 0) return res.data;
  } catch (e) {
    // fallback
  }

  const candidates: CandidateProfile[] = [
    {
      id: 'cand-1',
      name: 'Jasurbek Aliyev',
      avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop',
      email: 'jasur.dev@gmail.com',
      phone: '+998 90 123 45 67',
      university: 'UrDU (Urganch davlat universiteti)',
      faculty: 'Dasturiy Injiniring',
      graduation_year: 2026,
      gpa: 4.85,
      completed_simulations_count: 7,
      avg_score: 98.4,
      skills: ['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis', 'HighLoad', 'System Design'],
      top_projects: [
        { title: 'JPMorgan Chase High-Frequency Trading Interface', company: 'JPMorgan Chase & Co.', score: 99, completed_at: '2026-09-20', certificate_uuid: 'tj-cert-jpm-001' },
        { title: 'KATM Milliy Kredit Baholash Tizimi & Skoring', company: 'KATM Markaziy Baza', score: 98, completed_at: '2026-09-28', certificate_uuid: 'tj-cert-katm-002' },
        { title: 'PwC Customer Churn Analytics ML', company: 'PwC Uzbekistan', score: 98, completed_at: '2026-10-02', certificate_uuid: 'tj-cert-pwc-003' }
      ],
      is_open_to_work: true,
      is_vip: true,
      bio: 'Junior/Middle Backend Muhandisi. TryJob da 7 ta murakkab amaliy simulyatsiyani 98%+ ball bilan muvaffaqiyatli topshirgan. Haqiqiy loyihalarda tranzaksiyalar xavfsizligi va yuqori yuklamali arxitekturalar bo\'yicha tajribaga ega.',
      location: 'Toshkent, O\'zbekiston (Gibrid / Ofis)',
      preferred_roles: ['Backend Software Engineer', 'Python / Go Developer', 'Data Engineer'],
      badge_titles: ['TryJob Top 1% Talent', 'Verified Code Master', 'Fast Responder']
    },
    {
      id: 'cand-2',
      name: 'Madina Karimova',
      avatar_url: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=120&h=120&fit=crop',
      email: 'madina.fin@gmail.com',
      phone: '+998 97 765 43 21',
      university: 'Westminster Xalqaro Universiteti (WIUT)',
      faculty: 'Economics with Finance',
      graduation_year: 2026,
      gpa: 4.90,
      completed_simulations_count: 6,
      avg_score: 97.2,
      skills: ['IFRS / MHXS', 'Financial Modeling', 'Excel Advanced', 'PowerBI', 'EBITDA Analysis', 'Audit Planning'],
      top_projects: [
        { title: 'PwC Audit & Korporativ Moliyaviy Tahlil', company: 'PwC Uzbekistan', score: 98, completed_at: '2026-09-15', certificate_uuid: 'tj-cert-pwc-101' },
        { title: 'KATM Kredit Risklari va Skoring Tahlili', company: 'KATM Markaziy Baza', score: 96, completed_at: '2026-09-25', certificate_uuid: 'tj-cert-katm-102' }
      ],
      is_open_to_work: true,
      is_vip: true,
      bio: 'Xalqaro moliya va audit bo\'yicha talaba. Katta 4-lik (Big 4) standartlari bo\'yicha moliyaviy hisobotlarni tuzish, soliq auditini o\'tkazish va biznes risklarini baholash ko\'nikmalariga ega.',
      location: 'Toshkent (Ofis)',
      preferred_roles: ['Financial Analyst', 'Junior Auditor', 'Risk Management Specialist'],
      badge_titles: ['Big 4 Certified', 'Top Financial Mind', 'Honors Graduate']
    },
    {
      id: 'cand-3',
      name: 'Bobur Mirzayev',
      avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120&h=120&fit=crop',
      email: 'bobur.dev@inbox.uz',
      phone: '+998 93 555 88 99',
      university: 'Inha Universiteti Toshkent (IUT)',
      faculty: 'Computer Science and Engineering (CSE)',
      graduation_year: 2026,
      gpa: 4.70,
      completed_simulations_count: 6,
      avg_score: 96.8,
      skills: ['React.js', 'TypeScript', 'Node.js', 'TailwindCSS', 'REST APIs', 'CyberSecurity Basics'],
      top_projects: [
        { title: 'JPMorgan Chase Stock Visualizer Dashboard', company: 'JPMorgan Chase & Co.', score: 97, completed_at: '2026-09-10', certificate_uuid: 'tj-cert-jpm-201' },
        { title: 'IT-Park Tech Startup Investment Case', company: 'IT Park Uzbekistan', score: 96, completed_at: '2026-09-29', certificate_uuid: 'tj-cert-itp-202' }
      ],
      is_open_to_work: true,
      is_vip: false,
      bio: 'Frontend & Full-stack dasturchi. Zamonaviy foydalanuvchi interfeyslari, yuqori tezlikdagi veb ilovalar va interaktiv ma\'lumotlar vizualizatsiyasini yaratish bo\'yicha mutaxassis.',
      location: 'Toshkent / Masofaviy',
      preferred_roles: ['Frontend Engineer', 'Full-stack Developer', 'UI Engineer'],
      badge_titles: ['UI Artisan', 'Clean Code Advocate']
    },
    {
      id: 'cand-4',
      name: 'Shahnoza Ergasheva',
      avatar_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=120&h=120&fit=crop',
      email: 'shahnoza.biz@mail.ru',
      phone: '+998 91 333 22 11',
      university: 'TDIU (Toshkent Davlat Iqtisodiyot Universiteti)',
      faculty: 'Bank ishi va Audit',
      graduation_year: 2026,
      gpa: 4.60,
      completed_simulations_count: 5,
      avg_score: 94.5,
      skills: ['Data Analysis', 'SQL', 'Tableau', 'Business Strategy', 'Excel'],
      top_projects: [
        { title: 'PwC Customer Churn Analytics', company: 'PwC Uzbekistan', score: 95, completed_at: '2026-09-18' }
      ],
      is_open_to_work: true,
      is_vip: false,
      bio: 'Biznes tahlili va bank amaliyotlari bo\'yicha iqtidorli talaba. Ma\'lumotlarga asoslangan qaror qabul qilish (Data-Driven Decision Making) tarafdori.',
      location: 'Toshkent',
      preferred_roles: ['Business Analyst', 'Junior Data Analyst'],
      badge_titles: ['Analytical Thinker']
    },
    {
      id: 'cand-5',
      name: 'Dilnoza Yusupova',
      avatar_url: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=120&h=120&fit=crop',
      email: 'dilnoza.law@tashkent.uz',
      phone: '+998 94 444 12 34',
      university: 'TDYU (Toshkent Davlat Yuridik Universiteti)',
      faculty: 'Xalqaro Huquq va Qiyosiy Qonunchilik',
      graduation_year: 2026,
      gpa: 4.88,
      completed_simulations_count: 4,
      avg_score: 92.7,
      skills: ['Korporativ Huquq', 'Shartnomalar Auditi', 'Compliance', 'GDPR / Shaxsiy Ma\'lumotlar Qonuni'],
      top_projects: [
        { title: 'Centil Law Korporativ Shartnomalar Ekspertizasi', company: 'Centil Law Firm', score: 94, completed_at: '2026-09-22' }
      ],
      is_open_to_work: true,
      is_vip: true,
      bio: 'Yuridik hujjatlarni audit qilish, xalqaro shartnomalarni tekshirish va kompaniyalar compliance tizimini shakllantirish bo\'yicha chuqur bilimga ega.',
      location: 'Toshkent (Ofis)',
      preferred_roles: ['Legal Counsel Junior', 'Compliance Officer', 'Contract Specialist'],
      badge_titles: ['Legal Shield', 'Verified Compliance']
    }
  ];

  let filtered = [...candidates];
  if (filters?.skill) {
    const s = filters.skill.toLowerCase();
    filtered = filtered.filter(c => c.skills.some(sk => sk.toLowerCase().includes(s)));
  }
  if (filters?.minScore) {
    filtered = filtered.filter(c => c.avg_score >= (filters.minScore || 0));
  }
  if (filters?.university && filters.university !== 'all') {
    const u = filters.university.toLowerCase();
    filtered = filtered.filter(c => c.university.toLowerCase().includes(u));
  }
  if (filters?.vipOnly) {
    filtered = filtered.filter(c => c.is_vip);
  }

  return filtered;
}

export async function sendTalentOffer(
  offer: Omit<TalentOffer, 'id' | 'status' | 'created_at'>
): Promise<TalentOffer> {
  const newOffer: TalentOffer = {
    ...offer,
    id: 'offer-' + Date.now(),
    status: 'sent',
    created_at: new Date().toISOString()
  };

  try {
    const res = await api.post<TalentOffer>('/talents/offers', newOffer);
    if (res.data) return res.data;
  } catch (e) {
    // fallback local storage
  }

  // Save to localStorage for demo persistence
  const existing = JSON.parse(localStorage.getItem('tryjob_sent_offers') || '[]');
  existing.unshift(newOffer);
  localStorage.setItem('tryjob_sent_offers', JSON.stringify(existing));

  return newOffer;
}

export function getSentOffers(): TalentOffer[] {
  try {
    return JSON.parse(localStorage.getItem('tryjob_sent_offers') || '[]');
  } catch (e) {
    return [];
  }
}

export async function upgradeVip(candidateId: string): Promise<{ success: boolean; message: string }> {
  try {
    const res = await api.post(`/talents/${candidateId}/vip-upgrade`);
    return res.data;
  } catch (e) {
    return {
      success: true,
      message: 'Nomzod VIP statusiga muvaffaqiyatli o\'tkazildi! HR xabarnomalari ustuvor ko\'rinadi.'
    };
  }
}

// ── University Portal & Stats API ──────────────────────────────────────────
export async function getUniversityStats(universityId?: string): Promise<UniversityStats> {
  try {
    const res = await api.get<UniversityStats>(`/university/stats`, { params: universityId ? { university_id: universityId } : {} });
    if (res.data) return res.data;
  } catch (e) {
    // fallback
  }

  return {
    id: universityId || 'urdu',
    university_name: 'Urganch davlat universiteti (UrDU)',
    short_name: 'UrDU',
    logo_url: 'https://images.unsplash.com/photo-1562774053-701939374585?w=100&h=100&fit=crop',
    total_students: 1420,
    active_interns: 840,
    completed_simulations: 2150,
    average_score: 91.8,
    top_department: 'Dasturiy Injiniring Fakulteti',
    hiring_rate_percent: 78.5,
    partner_companies_count: 24,
    monthly_trend: [
      { month: 'May', completions: 180, avg_score: 87.2 },
      { month: 'Iyun', completions: 290, avg_score: 89.0 },
      { month: 'Iyul', completions: 340, avg_score: 90.1 },
      { month: 'Avgust', completions: 420, avg_score: 91.0 },
      { month: 'Sentyabr', completions: 560, avg_score: 92.4 },
      { month: 'Oktyabr', completions: 360, avg_score: 93.1 },
    ],
    top_performers: [
      { name: 'Jasurbek Aliyev', course: 4, faculty: 'Dasturiy Injiniring', score: 98.4, cert_count: 7, status: 'Uzum Bank dan Offer olgan' },
      { name: 'Ulug\'bek Toshmatov', course: 3, faculty: 'Kiberxavfsizlik', score: 96.1, cert_count: 5, status: 'Amaliyotda (Payme)' },
      { name: 'Sevara Rahimova', course: 4, faculty: 'Sun\'iy intellekt', score: 95.8, cert_count: 5, status: 'Top Talent' },
      { name: 'Farrux Saidov', course: 4, faculty: 'Telekommunikatsiya', score: 94.2, cert_count: 4, status: 'Amaliyotda (Beeline)' },
      { name: 'Nilufar Mirzarahimova', course: 3, faculty: 'Dasturiy Injiniring', score: 93.7, cert_count: 4, status: 'Kutuvda' },
    ],
    departments: [
      { name: 'Dasturiy Injiniring', student_count: 520, completion_rate: 89, avg_score: 93.4 },
      { name: 'Kiberxavfsizlik', student_count: 310, completion_rate: 82, avg_score: 92.1 },
      { name: 'Sun\'iy Intellekt & Data Science', student_count: 280, completion_rate: 85, avg_score: 91.5 },
      { name: 'Telekommunikatsiya & Tarmoqlar', student_count: 310, completion_rate: 68, avg_score: 88.2 },
    ]
  };
}

