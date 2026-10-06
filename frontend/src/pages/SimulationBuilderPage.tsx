import React, { useState, useEffect } from 'react';
import { 
  Building2, Plus, Trash2, Save, Play, Sparkles, Download, Upload, 
  CheckCircle2, Layers, FileCode, FileText, Database, Shield, Award, 
  HelpCircle, Eye, ArrowRight, Table, Copy, Check, RefreshCw, X, ChevronRight,
  Lock, ShieldAlert, GraduationCap, School, LogIn
} from 'lucide-react';
import { Simulation, SimulationTask } from '../types';
import { saveCustomSimulation } from '../api';
import { useAuth } from '../context/AuthContext';
import { AuthModal } from '../components/AuthModal';

interface SimulationBuilderPageProps {
  onSimulationCreated: (slug: string) => void;
  onNavigate: (view: string) => void;
}

const PRESET_TEMPLATES: { name: string; category: string; data: Simulation }[] = [
  {
    name: 'Uzum Bank: Real-Time Fraud Detection Engine',
    category: 'Fintech & Engineering',
    data: {
      id: 'sim-uzum-fraud-2026',
      slug: 'uzum-fraud-detection-engine',
      title: 'Uzum Bank: Real-Time Fraud Detection Engine',
      category: 'Fintech & Dasturlash',
      difficulty: 'Middle',
      estimated_hours: 4,
      description: 'Har soniyada minglab tranzaksiyalarni tahlil qilib, shubhali firibgarlik (anti-fraud) holatlarini 50ms ichida to\'xtatuvchi microservice algoritmini ishlab chiqish.',
      learning_outcomes: [
        'High-load tranzaksiyalarni stream tahlil qilish',
        'Redis in-memory caching va limitlarni tekshirish',
        'Mashinali o\'rganish asosidagi anomaliyalarni aniqlash qoidalarini yozish'
      ],
      company: {
        id: 'comp-uzum',
        name: 'Uzum Bank Uzbekistan',
        logo_url: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=120&h=120&fit=crop',
        industry: 'Fintech & Digital Banking',
        description: 'O\'zbekistondagi eng yirik milliy raqamli ekotizim va bank xizmatlari provayderi.',
        website: 'https://uzumbank.uz',
        is_verified: true
      },
      tasks: [
        {
          id: 'task-fraud-1',
          order: 1,
          title: 'Tranzaksiya oqimidagi anomaliyalarni aniqlash funksiyasi',
          mentor_persona: 'lead_engineer',
          briefing_text: 'Hush kelibsiz! Bugun Uzum Bank to\'lovlar shlyuzi uchun yangi firibgarlik filtri yaratamiz. Maqsad: agar foydalanuvchi oxirgi 60 soniya ichida 5 dan ortiq tranzaksiya bajarsa yoki odatiy geografik joylashuvi keskin o\'zgarsa, tranzaksiyani "BLOCKED" deb belgilash.',
          instructions: 'Quyidagi Python funksiyasini yozing: `def detect_fraud(transactions: list) -> list`. Har bir tranzaksiya uchun risk balli va holatini (APPROVED / FLAGGED / BLOCKED) qaytaring.',
          template_data: `def detect_fraud(transactions: list) -> list:\n    \"\"\"\n    Tranzaksiyalarni tekshirish va firibgarlik riskini hisoblash.\n    Input: [{'id': 'tx1', 'user_id': 'u1', 'amount': 250000, 'timestamp': 1000, 'location': 'Tashkent'}]\n    Output: list of flagged transaction IDs\n    \"\"\"\n    flagged = []\n    # Kodingizni yozing:\n    \n    return flagged\n`,
          model_answer: `def detect_fraud(transactions: list) -> list:\n    flagged = []\n    user_history = {}\n    for tx in transactions:\n        uid = tx.get('user_id')\n        amt = tx.get('amount', 0)\n        if uid not in user_history:\n            user_history[uid] = []\n        user_history[uid].append(tx)\n        if amt > 10_000_000 or len(user_history[uid]) > 5:\n            flagged.append(tx['id'])\n    return flagged\n`,
          rubric_criteria: [
            { criterion: 'Algoritmik to\'g\'rilik va shartlarni to\'liq qamrab olish', max_score: 40 },
            { criterion: 'Vaqt murakkabligi (O(N) optimallik)', max_score: 30 },
            { criterion: 'Xatoliklar va edge-caselarni qayta ishlash', max_score: 30 }
          ],
          resource_files: {
            task_type: 'code',
            supervisor: {
              name: 'Jamshid Ismoilov',
              role: 'Head of Core Banking & Security',
              department: 'Payments & Risk Engineering',
              avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop',
              audio_duration: '01:45'
            },
            audio_transcript: 'Salom, yangi muhandis! Kecha kechqurun firibgarlik urinishlari 2 barobarga oshdi. Sizdan real-time filtrlash logikasini tezda ishlab chiqishni va testlardan o\'tkazishni so\'raymiz.',
            corporate_context: 'Uzum Bank kuniga 2.5 milliondan ortiq tranzaksiyalarni qayta ishlaydi. Har qanday xato tizim unumdorligiga yoki foydalanuvchilar ishonchiga ta\'sir qiladi.',
            deliverables: ['detect_fraud() Python algoritmi', 'Unit testlar to\'plami', 'Latency tahlili hisoboti'],
            dataset: {
              title: 'Live Transactions Stream Sample',
              headers: ['Tx_ID', 'User_ID', 'Amount_UZS', 'Timestamp', 'IP_Location', 'Device'],
              rows: [
                ['tx_901', 'usr_882', '450,000', '14:02:11', 'Tashkent, UZ', 'iOS App'],
                ['tx_902', 'usr_882', '2,800,000', '14:02:29', 'Samarkand, UZ', 'Android App'],
                ['tx_903', 'usr_410', '15,000,000', '14:03:00', 'Frankfurt, DE', 'Web Browser (VPN)'],
                ['tx_904', 'usr_991', '120,000', '14:03:15', 'Tashkent, UZ', 'iOS App']
              ]
            },
            downloads: [
              { name: 'uzum_transaction_schema.json', size: '24 KB', type: 'JSON' },
              { name: 'fraud_detection_rules.pdf', size: '1.2 MB', type: 'PDF' }
            ],
            model_explanation: 'Yechim O(N) murakkablikda ishlaydi va foydalanuvchi tranzaksiyalari chastotasini hamda shubhali IP sakrashlarini aniqlaydi.'
          }
        }
      ]
    }
  },
  {
    name: 'PwC Uzbekistan: IFRS 16 Lease & Asset Audit',
    category: 'Moliya & Audit',
    data: {
      id: 'sim-pwc-lease-audit',
      slug: 'pwc-ifrs-16-lease-audit',
      title: 'PwC Uzbekistan: IFRS 16 Lease & Financial Audit',
      category: 'Moliya & Audit',
      difficulty: 'Middle',
      estimated_hours: 3,
      description: 'Xalqaro moliyaviy hisobot standartlari (IFRS 16) bo\'yicha kompaniya ijara majburiyatlari va Right-of-Use aktivlarini qayta hisoblash va audit xulosasini tuzish.',
      learning_outcomes: [
        'IFRS 16 standartlari bo\'yicha diskont stavkalari (IBR) tahlili',
        'Right-of-Use (ROU) aktivi va amortizatsiya jadvalini tekshirish',
        'Audit memorandumini professional tarzda rasmiylashtirish'
      ],
      company: {
        id: 'comp-pwc',
        name: 'PwC Uzbekistan',
        logo_url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=120&h=120&fit=crop',
        industry: 'Audit, Tax & Advisory',
        description: 'Katta to\'rtlik (Big 4) yetakchi audit va konsalting kompaniyasi.',
        website: 'https://pwc.com/uz',
        is_verified: true
      },
      tasks: [
        {
          id: 'task-pwc-1',
          order: 1,
          title: 'Ijara majburiyatlari va diskontlangan qiymat auditi',
          mentor_persona: 'audit_manager',
          briefing_text: 'Mijozimiz bo\'lgan yirik chakana savdo tarmog\'i 15 ta do\'kon ijarasi bo\'yicha yangi IFRS 16 hisobotini taqdim etdi. Sizning vazifangiz berilgan ijara to\'lovlari jadvalini tekshirish va audit xulosasini tayyorlash.',
          instructions: 'Kompaniya taqdim etgan Excel hisob-kitoblaridagi diskont stavkasi (IBR 14.5%) to\'g\'ri qo\'llanganligini tekshiring va aniqlangan tafovutlar bo\'yicha rahbariyatga audit memorandumini yozing.',
          template_data: 'AUDIT MEMORANDUMI\n\nKIMGA: Audit Partner\nKIMDAN: Junior Audit Associate\nMAVZU: IFRS 16 Ijara hisobotlari auditi natijalari\n\n1. ASOSIY TOPILMALAR:\n...\n\n2. DISKONTLASH VA XATOLIKLAR TAHLILI:\n...\n\n3. TAVSIYALAR VA TUZATISH XULOSASI:\n...',
          model_answer: 'AUDIT MEMORANDUMI\n\nKIMGA: Audit Partner (PwC Uzbekistan)\nKIMDAN: Senior Audit Associate\nMAVZU: IFRS 16 Ijara hisobotlari bo\'yicha audit xulosasi\n\n1. ASOSIY TOPILMALAR:\nMijoz tomonidan 15 ta ijara shartnomasi bo\'yicha hisoblangan jami majburiyat 48.2 mlrd UZS qilib ko\'rsatilgan. Biroq 3 ta shartnomada indeksatsiya koeffitsienti diskont oqimidan chiqarib qoldirilgan.\n\n2. DISKONTLASH TAHLILI:\nDiskont stavkasi 14.5% o\'rniga bozor stavkasi 16.0% qo\'llanganda Right-of-Use aktivi 3.4 mlrd UZS ga kamayishi aniqlandi.\n\n3. AUDIT TAVSIYALARI:\nBalans moddasiga tuzatish kiritish va moliyaviy hisobot izohlariga (notes) qo\'shimcha ochiqlash berish talab etiladi.',
          rubric_criteria: [
            { criterion: 'IFRS 16 standartlari va qoidalarining to\'g\'ri talqini', max_score: 40 },
            { criterion: 'Raqamlar aniqligi va risklarni to\'g\'ri baholash', max_score: 35 },
            { criterion: 'Hisobotning professional tuzilishi va xulosa sifati', max_score: 25 }
          ],
          resource_files: {
            task_type: 'report',
            supervisor: {
              name: 'Madina Karimova',
              role: 'Audit Director',
              department: 'Assurance & Financial Services',
              avatar: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=120&h=120&fit=crop',
              audio_duration: '02:10'
            },
            audio_transcript: 'Madina gapiryapti. Mijozimiz hisobotida 4 milliard so\'mlik ehtimoliy xatolik borligidan xavotirdamiz. Iltimos barcha jadvallarni sinchiklab ko\'rib chiqing.',
            corporate_context: 'PwC xalqaro standartlar bo\'yicha 100% ishonchli audit xulosalarini taqdim etishi shart.',
            deliverables: ['Audit Memorandumi (.docx/.pdf)', 'Tuzatilgan Moliyaviy Jadval'],
            dataset: {
              title: 'Mijoz Ijara Shartnomalari Reestri',
              headers: ['Filial_Nomi', 'Yillik_To\'lov_UZS', 'Muddati_Yil', 'Stavka_%', 'Hisoblangan_ROU_Aktiv'],
              rows: [
                ['Chilonzor Savdo Markazi', '1,200,000,000', '5', '14.5%', '4,150,000,000'],
                ['Samarqand Darvoza', '2,400,000,000', '7', '14.5%', '9,820,000,000'],
                ['Qo\'qon Markaziy Do\'kon', '600,000,000', '3', '14.5%', '1,420,000,000']
              ]
            },
            downloads: [
              { name: 'ifrs_16_client_calculations.xlsx', size: '180 KB', type: 'XLSX' },
              { name: 'pwc_audit_memo_guidelines.pdf', size: '450 KB', type: 'PDF' }
            ],
            model_explanation: 'Ushbu audit xulosasi IFRS 16 talablariga mos keladi va mijoz moliyaviy hisobotiga kiritilishi shart bo\'lgan tuzatishlarni to\'liq yoritgan.'
          }
        }
      ]
    }
  }
];

export const SimulationBuilderPage: React.FC<SimulationBuilderPageProps> = ({
  onSimulationCreated,
  onNavigate
}) => {
  const [activeTab, setActiveTab] = useState<'general' | 'tasks' | 'rubric' | 'dataset' | 'preview'>('general');
  const [selectedTaskIndex, setSelectedTaskIndex] = useState<number>(0);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);
  const [copiedJson, setCopiedJson] = useState<boolean>(false);
  const [jsonInputModal, setJsonInputModal] = useState<boolean>(false);
  const [rawJsonText, setRawJsonText] = useState<string>('');

  // Main Simulation State
  const [simulation, setSimulation] = useState<Simulation>({
    id: 'sim-custom-' + Date.now(),
    slug: 'yangi-kompaniya-simulyatsiyasi',
    title: 'Kompaniya: Yangi Kasbiy Simulyatsiya',
    category: 'Dasturiy Injiniring',
    difficulty: 'Middle',
    estimated_hours: 3,
    description: 'Ushbu simulyatsiyada amaliyotchilar kompaniyaning real ish muhitida muammolarni hal qiladi.',
    learning_outcomes: [
      'Real korporativ keyslarni mustaqil tahlil qilish',
      'Standartlar asosida yechim ishlab chiqish',
      'AI mentor fikr-mulohazalariga asosan optimizatsiya qilish'
    ],
    company: {
      id: 'comp-' + Date.now(),
      name: 'Mening Kompaniyam',
      logo_url: 'https://images.unsplash.com/photo-1572021335469-31706a17aaef?w=120&h=120&fit=crop',
      industry: 'Axborot Texnologiyalari & Fintech',
      description: 'Zamonaviy biznes yechimlar va xizmatlar taqdim etuvchi korxona.',
      website: 'https://company.uz',
      is_verified: true
    },
    tasks: [
      {
        id: 'task-1',
        order: 1,
        title: 'Boshlang\'ich topshiriq va tahlil',
        mentor_persona: 'lead_engineer',
        briefing_text: 'Kompaniyamizga xush kelibsiz! Ushbu bosqichda sizga berilgan talablar bo\'yicha vazifani bajaring.',
        instructions: 'Talablarni o\'qib chiqing va quyidagi shablon asosida to\'liq yechim yozing.',
        template_data: '# Ushbu yerga kodingiz yoki hisobotingizni yozing\n',
        model_answer: '# Namunaviy senior yechim\nprint("Yechim tayyor")',
        rubric_criteria: [
          { criterion: 'Texnik talablarga to\'liq muvofiqlik', max_score: 50 },
          { criterion: 'Optimallik va xavfsizlik', max_score: 30 },
          { criterion: 'Kod / Hisobot tozaligi va struktura', max_score: 20 }
        ],
        resource_files: {
          task_type: 'code',
          supervisor: {
            name: 'Akmal Zokirov',
            role: 'Team Lead',
            department: 'Engineering Department',
            avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120&h=120&fit=crop',
            audio_duration: '01:30'
          },
          audio_transcript: 'Assalomu alaykum! Loyihamizning ushbu bosqichini boshlayotganingizdan xursandmiz.',
          corporate_context: 'Kompaniya xalqaro sifat standartlariga amal qiladi.',
          deliverables: ['Yechim kodi', 'Tahliliy xulosa'],
          dataset: {
            title: 'Boshlang\'ich Ma\'lumotlar Jadvali',
            headers: ['ID', 'Nom', 'Qiymat', 'Holat'],
            rows: [
              ['item_1', 'Foydalanuvchi ma\'lumoti', '1,200', 'Faol'],
              ['item_2', 'Server logi', '98.5%', 'Barqaror']
            ]
          },
          downloads: [
            { name: 'texnik_topshiriq.pdf', size: '520 KB', type: 'PDF' }
          ],
          model_explanation: 'Ushbu yechim barcha mezonlarga javob beradi.'
        }
      }
    ]
  });

  const currentTask = simulation.tasks?.[selectedTaskIndex] || simulation.tasks?.[0];

  // Helper auto slug generator
  const handleTitleChange = (val: string) => {
    const slug = val
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-');
    setSimulation(prev => ({
      ...prev,
      title: val,
      slug: slug || 'yangi-simulyatsiya'
    }));
  };

  // Outcome add/remove
  const handleAddOutcome = () => {
    setSimulation(prev => ({
      ...prev,
      learning_outcomes: [...prev.learning_outcomes, 'Yangi natija ko\'nikmasi']
    }));
  };

  const handleOutcomeChange = (idx: number, val: string) => {
    const updated = [...simulation.learning_outcomes];
    updated[idx] = val;
    setSimulation(prev => ({ ...prev, learning_outcomes: updated }));
  };

  const handleRemoveOutcome = (idx: number) => {
    setSimulation(prev => ({
      ...prev,
      learning_outcomes: prev.learning_outcomes.filter((_, i) => i !== idx)
    }));
  };

  // Task Handlers
  const handleAddTask = () => {
    const nextOrder = (simulation.tasks?.length || 0) + 1;
    const newTask: SimulationTask = {
      id: `task-${Date.now()}`,
      order: nextOrder,
      title: `${nextOrder}-Topshiriq: Loyihani kengaytirish`,
      mentor_persona: 'lead_engineer',
      briefing_text: 'Ushbu bosqichda murakkabroq vazifani hal qilasiz.',
      instructions: 'Talablar bo\'yicha yechim ishlab chiqing.',
      template_data: '# 2-bosqich shabloni\n',
      model_answer: '# Namunaviy yechim\n',
      rubric_criteria: [
        { criterion: 'Funksionallik va to\'g\'ri ishlashi', max_score: 50 },
        { criterion: 'Sifat va tezkorlik', max_score: 50 }
      ],
      resource_files: {
        task_type: 'code',
        supervisor: {
          name: 'Nodir Alimov',
          role: 'Senior Architect',
          department: 'Core Team',
          avatar: 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?w=120&h=120&fit=crop',
          audio_duration: '01:15'
        },
        audio_transcript: 'Yangi bosqichga xush kelibsiz! Talablarga diqqat qiling.',
        corporate_context: 'Standartlarga muvofiq ishlab chiqilishi shart.',
        deliverables: ['Topshiriq yechimi'],
        downloads: []
      }
    };

    setSimulation(prev => ({
      ...prev,
      tasks: [...(prev.tasks || []), newTask]
    }));
    setSelectedTaskIndex((simulation.tasks?.length || 0));
  };

  const handleRemoveTask = (idx: number) => {
    if ((simulation.tasks?.length || 0) <= 1) {
      alert("Simulyatsiyada kamida 1 ta topshiriq bo'lishi kerak!");
      return;
    }
    const filtered = (simulation.tasks || []).filter((_, i) => i !== idx);
    setSimulation(prev => ({ ...prev, tasks: filtered }));
    setSelectedTaskIndex(Math.max(0, idx - 1));
  };

  const updateCurrentTask = (patch: Partial<SimulationTask>) => {
    if (!simulation.tasks) return;
    const updated = [...simulation.tasks];
    updated[selectedTaskIndex] = {
      ...updated[selectedTaskIndex],
      ...patch
    };
    setSimulation(prev => ({ ...prev, tasks: updated }));
  };

  const updateCurrentTaskResource = (patch: Partial<NonNullable<SimulationTask['resource_files']>>) => {
    if (!simulation.tasks) return;
    const cur = simulation.tasks[selectedTaskIndex];
    const updatedRes = {
      ...(cur.resource_files || {}),
      ...patch
    };
    updateCurrentTask({ resource_files: updatedRes });
  };

  // Rubric handlers
  const handleAddRubricCriterion = () => {
    if (!currentTask) return;
    const curRubric = currentTask.rubric_criteria || [];
    updateCurrentTask({
      rubric_criteria: [...curRubric, { criterion: 'Yangi baholash mezoni', max_score: 20 }]
    });
  };

  const handleUpdateRubricCriterion = (idx: number, crit: string, score: number) => {
    if (!currentTask) return;
    const curRubric = [...(currentTask.rubric_criteria || [])];
    curRubric[idx] = { criterion: crit, max_score: score };
    updateCurrentTask({ rubric_criteria: curRubric });
  };

  const handleRemoveRubricCriterion = (idx: number) => {
    if (!currentTask) return;
    const curRubric = (currentTask.rubric_criteria || []).filter((_, i) => i !== idx);
    updateCurrentTask({ rubric_criteria: curRubric });
  };

  // Dataset Table Handlers
  const handleUpdateDatasetHeader = (headerIdx: number, val: string) => {
    const ds = currentTask?.resource_files?.dataset || { title: 'Jadval', headers: [], rows: [] };
    const newHeaders = [...ds.headers];
    newHeaders[headerIdx] = val;
    updateCurrentTaskResource({
      dataset: { ...ds, headers: newHeaders }
    });
  };

  const handleAddDatasetColumn = () => {
    const ds = currentTask?.resource_files?.dataset || { title: 'Yangi Jadval', headers: [], rows: [] };
    const newHeaders = [...ds.headers, `Ustun_${ds.headers.length + 1}`];
    const newRows = ds.rows.map(r => [...r, '-']);
    updateCurrentTaskResource({
      dataset: { ...ds, headers: newHeaders, rows: newRows }
    });
  };

  const handleAddDatasetRow = () => {
    const ds = currentTask?.resource_files?.dataset || { title: 'Yangi Jadval', headers: ['Ustun 1'], rows: [] };
    const newRow = ds.headers.map((_, i) => `Qiymat ${i + 1}`);
    updateCurrentTaskResource({
      dataset: { ...ds, rows: [...ds.rows, newRow] }
    });
  };

  const handleUpdateDatasetCell = (rIdx: number, cIdx: number, val: string) => {
    const ds = currentTask?.resource_files?.dataset;
    if (!ds) return;
    const newRows = ds.rows.map((row, ri) => {
      if (ri !== rIdx) return row;
      const newR = [...row];
      newR[cIdx] = val;
      return newR;
    });
    updateCurrentTaskResource({
      dataset: { ...ds, rows: newRows }
    });
  };

  const handleRemoveDatasetRow = (rIdx: number) => {
    const ds = currentTask?.resource_files?.dataset;
    if (!ds) return;
    updateCurrentTaskResource({
      dataset: { ...ds, rows: ds.rows.filter((_, i) => i !== rIdx) }
    });
  };

  // Preset loader
  const handleLoadPreset = (template: typeof PRESET_TEMPLATES[0]) => {
    const clone = JSON.parse(JSON.stringify(template.data));
    clone.id = 'sim-custom-' + Date.now();
    setSimulation(clone);
    setSelectedTaskIndex(0);
    alert(`"${template.name}" shabloni muvaffaqiyatli yuklandi!`);
  };

  // Save Simulation
  const handleSaveAndLaunch = () => {
    // Basic validation
    if (!simulation.title.trim()) {
      alert("Iltimos, simulyatsiya sarlavhasini kiriting!");
      return;
    }
    if (!simulation.tasks || simulation.tasks.length === 0) {
      alert("Kamida bitta topshiriq qo'shilishi shart!");
      return;
    }

    const saved = saveCustomSimulation(simulation);
    setSavedSuccess(true);
    setTimeout(() => {
      onSimulationCreated(saved.slug);
    }, 1200);
  };

  // Copy JSON
  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(simulation, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  // JSON Import
  const handleImportJson = () => {
    try {
      const parsed = JSON.parse(rawJsonText);
      if (!parsed.title || !parsed.slug) {
        throw new Error("JSON da title yoki slug mavjud emas");
      }
      setSimulation(parsed);
      setJsonInputModal(false);
      alert("Simulyatsiya JSON dan muvaffaqiyatli yuklandi!");
    } catch (err: any) {
      alert("JSON formati noto'g'ri: " + err.message);
    }
  };

  const { user, isAuthenticated } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const totalRubricScore = (currentTask?.rubric_criteria || []).reduce((acc, c) => acc + (Number(c.max_score) || 0), 0);

  // Auto-sync user company info if logged in as company_hr
  useEffect(() => {
    if (user?.role === 'company_hr' && user.company_name) {
      setSimulation(prev => ({
        ...prev,
        company: {
          ...prev.company,
          name: user.company_name || prev.company.name,
          id: user.company_id || prev.company.id
        }
      }));
    }
  }, [user]);

  // If user is not logged in or not a company_hr, show Company Verification Gate
  if (!isAuthenticated || (user?.role !== 'company_hr' && user?.role !== 'admin')) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-8 animate-fade-in">
        <div className="p-8 sm:p-12 rounded-3xl bg-gradient-to-b from-[#131826] to-[#0B0F19] border border-purple-500/30 shadow-2xl space-y-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="w-16 h-16 mx-auto rounded-2xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Building2 className="w-8 h-8" />
          </div>

          <div className="space-y-3 max-w-xl mx-auto">
            <span className="px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-bold uppercase tracking-wider">
              Kompaniyalar & HR Uchun
            </span>
            <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
              Kompaniya Profilingizni Ro'yxatdan O'tkazing
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              Simulyatsiya va topshiriqlar yaratish faqat <strong>verifikatsiyalangan ish beruvchi korxonalar</strong> uchun mo'ljallangan. Kompaniyangiz nomidan kirib, o'z amaliyot keyslaringizni joylang.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => setAuthModalOpen(true)}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-purple-500/25 transition flex items-center justify-center gap-2"
            >
              <Building2 className="w-4 h-4" />
              <span>🏢 Kompaniya Sifatida Kirish / Ro'yxatdan O'tish</span>
            </button>

            <button
              onClick={() => onNavigate('catalog')}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white font-medium text-sm transition flex items-center justify-center gap-2"
            >
              <GraduationCap className="w-4 h-4 text-indigo-400" />
              <span>Talabalar Amaliyoti Katalogi</span>
            </button>
          </div>

          {user && user.role === 'student' && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-center justify-center gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
              <span>Siz hozirda <strong>Talaba ({user.full_name})</strong> sifatida kirdingiz. Simulyatsiya yaratish uchun Kompaniya HR profiliga o'ting.</span>
            </div>
          )}
        </div>

        <AuthModal 
          isOpen={authModalOpen} 
          onClose={() => setAuthModalOpen(false)} 
          defaultRole="company_hr" 
        />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
      
      {/* Top Banner & Title */}
      <div className="bg-gradient-to-r from-cyan-900/30 via-slate-900 to-blue-900/30 border border-cyan-500/30 rounded-3xl p-6 sm:p-8 backdrop-blur-xl relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-black uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 animate-spin" /> Authoring & HR Studio 2026
            </div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white tracking-tight">
              Simulyatsiya Konstruktori <span className="text-cyan-400">(Builder Studio)</span>
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
              Kompaniyangiz uchun real keyslar, interaktiv brifinglar, datasetlar va AI baholash mezonlarini yarating. Talabalar real topshiriqlarni bajarib, kompaniyangizdan taklif olsin!
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => {
                setRawJsonText(JSON.stringify(simulation, null, 2));
                setJsonInputModal(true);
              }}
              className="bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white px-4 py-2.5 rounded-xl border border-slate-700 text-xs font-bold flex items-center gap-2 transition"
            >
              <Upload className="w-4 h-4 text-cyan-400" /> JSON Import
            </button>

            <button
              onClick={handleCopyJson}
              className="bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white px-4 py-2.5 rounded-xl border border-slate-700 text-xs font-bold flex items-center gap-2 transition"
            >
              {copiedJson ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-cyan-400" />}
              {copiedJson ? 'Nusxalandi!' : 'JSON Eksport'}
            </button>

            <button
              onClick={handleSaveAndLaunch}
              disabled={savedSuccess}
              className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black px-6 py-2.5 rounded-xl shadow-lg shadow-cyan-500/25 flex items-center gap-2 text-xs transition cursor-pointer"
            >
              {savedSuccess ? <CheckCircle2 className="w-4 h-4 text-emerald-950 animate-bounce" /> : <Save className="w-4 h-4" />}
              {savedSuccess ? 'Saqlandi! Ochilmoqda...' : 'Saqlash va Ishga Tushirish'}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Preset Templates Bar */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-black text-white uppercase tracking-wider block">Tayyor Shablonlar bilan Boshlash:</span>
            <span className="text-[11px] text-slate-400">Tez start uchun kompaniyalar tomonidan tasdiqlangan keys shablonini yuklang</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {PRESET_TEMPLATES.map((tmpl, idx) => (
            <button
              key={idx}
              onClick={() => handleLoadPreset(tmpl)}
              className="bg-slate-950 hover:bg-cyan-950/40 border border-slate-800 hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <span>{tmpl.name}</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">{tmpl.category}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {[
          { id: 'general', label: '1. Asosiy Ma\'lumotlar & Kompaniya', icon: Building2 },
          { id: 'tasks', label: '2. Topshiriqlar Konstruktori', icon: Layers, count: simulation.tasks?.length || 0 },
          { id: 'rubric', label: '3. Baholash Mezonlari (Rubric)', icon: Award },
          { id: 'dataset', label: '4. Dataset & Resurslar', icon: Database },
          { id: 'preview', label: '5. Jonli Ko\'rinish & JSON', icon: Eye }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-3 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="px-1.5 py-0.5 text-[10px] font-black rounded-full bg-slate-800 text-cyan-300">
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: General Info */}
      {activeTab === 'general' && (
        <div className="grid lg:grid-cols-3 gap-6 animate-in fade-in duration-200">
          
          {/* Left 2 Cols: Simulation meta */}
          <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-cyan-400" /> Simulyatsiya Asosiy Ko'rsatkichlari
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Simulyatsiya Sarlavhasi *
                </label>
                <input
                  type="text"
                  value={simulation.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  placeholder="Masalan: Uzum Bank - High Load Fraud Detection"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-cyan-500 transition font-medium"
                />
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    URL Slug (Avtomatik yoki maxsus)
                  </label>
                  <input
                    type="text"
                    value={simulation.slug}
                    onChange={(e) => setSimulation({ ...simulation, slug: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs text-cyan-400 font-mono focus:outline-none focus:border-cyan-500 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Yo'nalish (Soha / Category)
                  </label>
                  <select
                    value={simulation.category}
                    onChange={(e) => setSimulation({ ...simulation, category: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-cyan-500 transition"
                  >
                    <option value="Dasturiy Injiniring">Dasturiy Injiniring (Engineering)</option>
                    <option value="Fintech & Bank">Fintech & Bank Ishi</option>
                    <option value="Kiberxavfsizlik">Kiberxavfsizlik & Audit</option>
                    <option value="Moliya & Audit">Moliya & Audit (IFRS/ACCA)</option>
                    <option value="Biznes Tahlil & Data">Biznes Tahlil & Data Science</option>
                    <option value="Yuridik & Compliance">Yuridik & Korporativ Compliance</option>
                    <option value="Product Management">Product Management & UI/UX</option>
                  </select>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Qiyinlik Darajasi
                  </label>
                  <div className="flex gap-2">
                    {['Junior', 'Middle', 'Senior'].map((dif) => (
                      <button
                        key={dif}
                        type="button"
                        onClick={() => setSimulation({ ...simulation, difficulty: dif })}
                        className={`flex-1 py-2.5 rounded-xl text-xs font-bold border transition ${
                          simulation.difficulty === dif
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                        }`}
                      >
                        {dif}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Tavsiya Etilgan Vaqt (Soat)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="40"
                    value={simulation.estimated_hours}
                    onChange={(e) => setSimulation({ ...simulation, estimated_hours: Number(e.target.value) || 1 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500 transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Simulyatsiya Tavsifi (Umumiy sharh)
                </label>
                <textarea
                  rows={4}
                  value={simulation.description}
                  onChange={(e) => setSimulation({ ...simulation, description: e.target.value })}
                  placeholder="Ushbu simulyatsiyada talaba nimani o'rganadi va kompaniya uchun qanday muammoni hal qiladi..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-white focus:outline-none focus:border-cyan-500 transition leading-relaxed"
                />
              </div>

              {/* Learning Outcomes */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    O'zlashtiriladigan Ko'nikmalar (Learning Outcomes)
                  </label>
                  <button
                    type="button"
                    onClick={handleAddOutcome}
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-bold flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Qo'shish
                  </button>
                </div>
                <div className="space-y-2">
                  {simulation.learning_outcomes.map((outcome, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-lg bg-cyan-500/10 text-cyan-400 font-bold text-xs flex items-center justify-center shrink-0">
                        {idx + 1}
                      </span>
                      <input
                        type="text"
                        value={outcome}
                        onChange={(e) => handleOutcomeChange(idx, e.target.value)}
                        className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveOutcome(idx)}
                        className="p-2 text-slate-500 hover:text-red-400 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>

          {/* Right 1 Col: Company Profile */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl h-fit">
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Building2 className="w-5 h-5 text-cyan-400" /> Kompaniya Profili (HR/Muallif)
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Kompaniya Nomi *
                </label>
                <input
                  type="text"
                  value={simulation.company.name}
                  onChange={(e) => setSimulation({
                    ...simulation,
                    company: { ...simulation.company, name: e.target.value }
                  })}
                  placeholder="Masalan: Uzum Bank, Payme, PwC"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Kompaniya Logotipi URL
                </label>
                <input
                  type="text"
                  value={simulation.company.logo_url}
                  onChange={(e) => setSimulation({
                    ...simulation,
                    company: { ...simulation.company, logo_url: e.target.value }
                  })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500"
                />
                {simulation.company.logo_url && (
                  <div className="mt-3 flex items-center gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
                    <img
                      src={simulation.company.logo_url}
                      alt="Logo"
                      className="w-10 h-10 rounded-lg object-cover border border-slate-700"
                    />
                    <div>
                      <span className="text-xs font-bold text-white block">{simulation.company.name}</span>
                      <span className="text-[10px] text-cyan-400">Verifikatsiyalangan Ish Beruvchi</span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Soha / Industry
                </label>
                <input
                  type="text"
                  value={simulation.company.industry}
                  onChange={(e) => setSimulation({
                    ...simulation,
                    company: { ...simulation.company, industry: e.target.value }
                  })}
                  placeholder="Fintech, IT, Audit, Telecommunication"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Kompaniya Veb-sayti
                </label>
                <input
                  type="text"
                  value={simulation.company.website}
                  onChange={(e) => setSimulation({
                    ...simulation,
                    company: { ...simulation.company, website: e.target.value }
                  })}
                  placeholder="https://company.uz"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-cyan-400 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Kompaniya Haqida Qisqacha
                </label>
                <textarea
                  rows={3}
                  value={simulation.company.description}
                  onChange={(e) => setSimulation({
                    ...simulation,
                    company: { ...simulation.company, description: e.target.value }
                  })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Task Builder */}
      {activeTab === 'tasks' && currentTask && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Top Tasks bar */}
          <div className="flex items-center justify-between bg-slate-900/90 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 overflow-x-auto">
              {(simulation.tasks || []).map((t, idx) => (
                <button
                  key={t.id || idx}
                  onClick={() => setSelectedTaskIndex(idx)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition ${
                    selectedTaskIndex === idx
                      ? 'bg-cyan-500 text-slate-950 font-black shadow-lg shadow-cyan-500/20'
                      : 'bg-slate-950 text-slate-300 hover:bg-slate-800 border border-slate-800'
                  }`}
                >
                  <span>Bosqich {idx + 1}: {t.title.slice(0, 20)}...</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleAddTask}
                className="bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" /> Yangi Topshiriq Qo'shish
              </button>

              {(simulation.tasks?.length || 0) > 1 && (
                <button
                  onClick={() => handleRemoveTask(selectedTaskIndex)}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" /> O'chirish
                </button>
              )}
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Task Details */}
            <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-cyan-400" />
                  {selectedTaskIndex + 1}-Topshiriq Tafsilotlari
                </h3>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-bold">Turi:</span>
                  <select
                    value={currentTask.resource_files?.task_type || 'code'}
                    onChange={(e) => updateCurrentTaskResource({ task_type: e.target.value as any })}
                    className="bg-slate-950 border border-slate-800 text-cyan-400 rounded-lg px-3 py-1.5 text-xs font-bold focus:outline-none focus:border-cyan-500"
                  >
                    <option value="code">💻 Kod / Algoritm (Python Sandbox)</option>
                    <option value="report">📄 Tahliliy Hisobot (Memorandum / Text)</option>
                    <option value="financial">📊 Moliyaviy Model / Audit (Excel)</option>
                    <option value="legal_audit">⚖️ Yuridik Ekspertiza / Shartnoma</option>
                  </select>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Topshiriq Sarlavhasi
                  </label>
                  <input
                    type="text"
                    value={currentTask.title}
                    onChange={(e) => updateCurrentTask({ title: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Topshiriq Brifingi (Talabaga kirish xabari)
                  </label>
                  <textarea
                    rows={3}
                    value={currentTask.briefing_text}
                    onChange={(e) => updateCurrentTask({ briefing_text: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-cyan-500 leading-relaxed"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Batafsil Yo'riqnoma & Texnik Talablar (Instructions)
                  </label>
                  <textarea
                    rows={4}
                    value={currentTask.instructions}
                    onChange={(e) => updateCurrentTask({ instructions: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-cyan-500 leading-relaxed"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2">
                    Boshlang'ich Shablon (Talaba muharririda ochiluvchi kod/matn)
                  </label>
                  <textarea
                    rows={6}
                    value={currentTask.template_data || ''}
                    onChange={(e) => updateCurrentTask({ template_data: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-amber-400 uppercase tracking-wider mb-2">
                    Senior Mutaxassis Namunaviy Yechimi (Model Answer / Exemplar)
                  </label>
                  <textarea
                    rows={6}
                    value={currentTask.model_answer || ''}
                    onChange={(e) => updateCurrentTask({ model_answer: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-emerald-400 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Namunaviy Yechim Sharhi & Tushuntirishi
                  </label>
                  <textarea
                    rows={2}
                    value={currentTask.resource_files?.model_explanation || ''}
                    onChange={(e) => updateCurrentTaskResource({ model_explanation: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>

            {/* Right 1 Col: Mentor & Audio Persona */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl h-fit">
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-cyan-400" /> Mentor & Audio Persona
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Mentor / Rahbar Ismi
                  </label>
                  <input
                    type="text"
                    value={currentTask.resource_files?.supervisor?.name || ''}
                    onChange={(e) => updateCurrentTaskResource({
                      supervisor: {
                        ...(currentTask.resource_files?.supervisor || {
                          name: '', role: '', department: '', avatar: '', audio_duration: '01:30'
                        }),
                        name: e.target.value
                      }
                    })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Lavozimi (Role)
                  </label>
                  <input
                    type="text"
                    value={currentTask.resource_files?.supervisor?.role || ''}
                    onChange={(e) => updateCurrentTaskResource({
                      supervisor: {
                        ...(currentTask.resource_files?.supervisor || {
                          name: '', role: '', department: '', avatar: '', audio_duration: '01:30'
                        }),
                        role: e.target.value
                      }
                    })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Bo'lim (Department)
                  </label>
                  <input
                    type="text"
                    value={currentTask.resource_files?.supervisor?.department || ''}
                    onChange={(e) => updateCurrentTaskResource({
                      supervisor: {
                        ...(currentTask.resource_files?.supervisor || {
                          name: '', role: '', department: '', avatar: '', audio_duration: '01:30'
                        }),
                        department: e.target.value
                      }
                    })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Audio Brifing Transkripti (So'zlashuv matni)
                  </label>
                  <textarea
                    rows={4}
                    value={currentTask.resource_files?.audio_transcript || ''}
                    onChange={(e) => updateCurrentTaskResource({ audio_transcript: e.target.value })}
                    placeholder="Mentorning talabaga ovozli xabari matni..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 leading-relaxed"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Korporativ Kontekst (Kompaniya ichki muhiti)
                  </label>
                  <textarea
                    rows={3}
                    value={currentTask.resource_files?.corporate_context || ''}
                    onChange={(e) => updateCurrentTaskResource({ corporate_context: e.target.value })}
                    placeholder="Kompaniyadagi real yuklama, xavflar va qoidalar..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Rubric Builder */}
      {activeTab === 'rubric' && currentTask && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-cyan-400" />
                Baholash Rubriki ({selectedTaskIndex + 1}-Topshiriq uchun)
              </h3>
              <p className="text-xs text-slate-400">
                AI Mentor talabaning topshirgan ishini ushbu mezonlar bo'yicha baholaydi.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className={`px-3 py-1.5 rounded-xl border text-xs font-black ${
                totalRubricScore === 100 
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}>
                Jami ball: {totalRubricScore} / 100 ball
              </div>

              <button
                onClick={handleAddRubricCriterion}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 transition"
              >
                <Plus className="w-4 h-4" /> Mezon Qo'shish
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {(currentTask.rubric_criteria || []).map((crit, idx) => (
              <div
                key={idx}
                className="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 group"
              >
                <div className="flex items-center gap-3 flex-1 w-full">
                  <span className="w-7 h-7 rounded-xl bg-cyan-500/10 text-cyan-400 font-bold text-xs flex items-center justify-center shrink-0">
                    {idx + 1}
                  </span>
                  <input
                    type="text"
                    value={crit.criterion}
                    onChange={(e) => handleUpdateRubricCriterion(idx, e.target.value, crit.max_score)}
                    placeholder="Mezon nomi (masalan: Xavfsizlik va SQL injectiondan himoyalanganlik)"
                    className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium"
                  />
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-400">Maks ball:</span>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={crit.max_score}
                      onChange={(e) => handleUpdateRubricCriterion(idx, crit.criterion, Number(e.target.value) || 0)}
                      className="w-16 bg-slate-900 border border-slate-800 rounded-xl px-2 py-1.5 text-xs text-cyan-400 font-black text-center focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <button
                    onClick={() => handleRemoveRubricCriterion(idx)}
                    className="p-2 text-slate-500 hover:text-red-400 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: Dataset Builder */}
      {activeTab === 'dataset' && currentTask && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-cyan-400" />
                Interaktiv Mock Dataset & Resurslar
              </h3>
              <p className="text-xs text-slate-400">
                Talaba Workspace'da tahlil qilishi yoki kod orqali qayta ishlashi uchun jadval ma'lumotlari.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleAddDatasetColumn}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-2 rounded-xl text-xs font-bold border border-slate-700 flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5 text-cyan-400" /> Ustun Qo'shish
              </button>

              <button
                onClick={handleAddDatasetRow}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" /> Qator Qo'shish
              </button>
            </div>
          </div>

          {/* Dataset Table Matrix */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-slate-300">Jadval Nomi:</label>
              <input
                type="text"
                value={currentTask.resource_files?.dataset?.title || 'Korporativ Dataset'}
                onChange={(e) => updateCurrentTaskResource({
                  dataset: {
                    ...(currentTask.resource_files?.dataset || { headers: [], rows: [] }),
                    title: e.target.value,
                    headers: currentTask.resource_files?.dataset?.headers || [],
                    rows: currentTask.resource_files?.dataset?.rows || []
                  }
                })}
                className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-cyan-400 font-bold focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="overflow-x-auto border border-slate-800 rounded-2xl bg-slate-950">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-300">
                  <tr>
                    <th className="p-3 w-10 text-center text-slate-500">#</th>
                    {(currentTask.resource_files?.dataset?.headers || []).map((h, hi) => (
                      <th key={hi} className="p-2.5">
                        <input
                          type="text"
                          value={h}
                          onChange={(e) => handleUpdateDatasetHeader(hi, e.target.value)}
                          className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs font-bold text-cyan-400 w-full focus:outline-none focus:border-cyan-500"
                        />
                      </th>
                    ))}
                    <th className="p-3 w-12 text-center text-slate-500">Amal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(currentTask.resource_files?.dataset?.rows || []).map((row, ri) => (
                    <tr key={ri} className="hover:bg-slate-900/40">
                      <td className="p-3 text-center text-slate-500 font-mono">{ri + 1}</td>
                      {row.map((cell, ci) => (
                        <td key={ci} className="p-2">
                          <input
                            type="text"
                            value={cell}
                            onChange={(e) => handleUpdateDatasetCell(ri, ci, e.target.value)}
                            className="bg-slate-900/80 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 w-full focus:outline-none focus:border-cyan-500"
                          />
                        </td>
                      ))}
                      <td className="p-2 text-center">
                        <button
                          onClick={() => handleRemoveDatasetRow(ri)}
                          className="p-1 text-slate-500 hover:text-red-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: Live Preview & JSON */}
      {activeTab === 'preview' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl animate-in fade-in duration-200">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                <Eye className="w-5 h-5 text-cyan-400" />
                Jonli Sxema & JSON Eksport
              </h3>
              <p className="text-xs text-slate-400">
                Ushbu JSON strukturasi to'g'ridan-to'g'ri backend API ga mos keladi.
              </p>
            </div>

            <button
              onClick={handleCopyJson}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black px-4 py-2 rounded-xl text-xs flex items-center gap-1.5 transition"
            >
              <Copy className="w-4 h-4" /> JSON Nusxalash
            </button>
          </div>

          <div className="bg-slate-950 rounded-2xl p-4 border border-slate-800 font-mono text-xs text-cyan-300 max-h-[500px] overflow-y-auto">
            <pre>{JSON.stringify(simulation, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* JSON Modal */}
      {jsonInputModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Upload className="w-4 h-4 text-cyan-400" /> Simulyatsiya JSON Import
              </h3>
              <button
                onClick={() => setJsonInputModal(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Quyidagi maydonga simulyatsiya JSON matnini joylang va "Yuklash" tugmasini bosing:
            </p>

            <textarea
              rows={14}
              value={rawJsonText}
              onChange={(e) => setRawJsonText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-4 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
            />

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setJsonInputModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 text-slate-300 hover:text-white"
              >
                Bekor qilish
              </button>
              <button
                onClick={handleImportJson}
                className="px-6 py-2 rounded-xl text-xs font-black bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition"
              >
                Yuklash va Qo'llash
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
