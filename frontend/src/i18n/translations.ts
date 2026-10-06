export type Language = 'uz' | 'ru' | 'en';

export const translations = {
  uz: {
    // Nav
    nav_simulations: 'Simulyatsiyalar',
    nav_case_cup: 'Case Cup',
    nav_talent_hunt: 'Talent Hunt',
    nav_university: 'Universitet',
    nav_create_simulation: 'Simulyatsiya Yaratish',

    // Hero
    hero_title_1: 'Rezyumeni unuting.',
    hero_title_2: 'Mahoratingizni ko\'rsating.',
    hero_desc: 'Ishga kirmasdan turib yetakchi kompaniyalarning real vazifalarini bajaring, tajriba to\'plang va to\'g\'ridan-to\'g\'ri ish taklifini oling.',
    hero_btn_start: 'Simulyatsiyani Boshlash',
    hero_btn_companies: 'Kompaniyalar Uchun',
    hero_offer_sent: 'Taklif yuborildi',
    hero_offer_desc: '92% Natija asosida to\'g\'ridan-to\'g\'ri chaqiruv',
    hero_badge_live: 'Real Ish Tajribasi',
    hero_badge_partner: 'Top Korporativ Keyslar',

    // Stats Bar
    landing_stats_students: '5,000+ Talaba',
    landing_stats_students_sub: 'Amaliyotni muvaffaqiyatli yakunlagan',
    landing_stats_partners: '24+ Kompaniya',
    landing_stats_partners_sub: 'Yetakchi mahalliy va global brendlar',
    landing_stats_rate: '94% Natija',
    landing_stats_rate_sub: 'Sertifikat olganlarga to\'g\'ridan-to\'g\'ri taklif',
    landing_stats_free: '100% Bepul',
    landing_stats_free_sub: 'Barcha talaba va mutaxassislar uchun',
    landing_company_logos_title: 'O\'ZBEKISTON VA GLOBAL BOZOR YETAKCHILARI BILAN HAMKORLIKDA',

    // Featured Simulations on Landing
    landing_featured_badge: 'Tavsiya etilgan',
    landing_featured_title: 'Ommabop Simulyatsiyalar',
    landing_featured_sub: 'Karyerangizni yetakchi brendlarning eng talabgir amaliy topshiriqlari bilan boshlang',
    landing_featured_view_all: 'Barcha Simulyatsiyalarni Ko\'rish',

    // Problem Section
    problem_tag: 'Asosiy Muammo va Yechim',
    problem_title: 'Karyerangizdagi 3 yillik to\'siqni yengamiz',
    problem_quote: '"Ishga kirish uchun tajriba kerak, tajriba to\'plash uchun esa ishga olishmaydi."',
    old_way_title: 'Eski Yo\'l (Tugallanmas Aylanma)',
    old_way_desc: '4 yil faqat quruq nazariya ➔ 100+ ta bo\'sh rezyume jo\'natish ➔ "Tajribangiz yo\'q" degan rad javoblari.',
    tryjob_way_title: 'TryJob Yechimi (To\'g\'ridan-to\'g\'ri Natija)',
    tryjob_way_desc: '5 soatlik amaliy simulyatsiya ➔ Korxonaning real vazifasini bajarish ➔ Isbotlangan portfolio va to\'g\'ridan-to\'g\'ri ish taklifi.',

    // How it works
    steps_tag: 'Oddiy va Aniq Jarayon',
    steps_title: 'TryJob qanday ishlaydi?',
    step_1_title: 'Kompaniya keysini tanlaysiz',
    step_1_desc: 'Kapitalbank, Uzum, PwC yoki JPMorgan kabi yetakchi brendlarning soha simulyatsiyasini tanlaysiz.',
    step_2_title: 'Real vazifani bajarasiz',
    step_2_desc: 'Nazariya emas — haqiqiy ma\'lumotlar tahlili, hujjat auditi va kodlarni yechib, AI mentordan tahlil olasiz.',
    step_3_title: 'Ish taklifini olasiz',
    step_3_desc: 'Bajargan ishingiz HR portalida ko\'rinadi va ish beruvchilar sizni to\'g\'ridan-to\'g\'ri suhbatga chaqiradi.',
    ai_realtime_review: 'Real-vaqt AI Taqrizi',
    ai_automated: '100% Avtomatlashgan',

    // Value Section
    value_tag: 'Aniq Natija',
    value_title: 'Barcha ishtirokchilar uchun kafolatlangan qiymat',
    
    val_student_title: 'Talabalarga',
    val_student_sub: 'Rezyumesiz, amaliy isbot bilan ishga kirish',
    val_student_free: '100% Bepul',
    val_student_stat: 'Rezyumeda 0 yil tajriba o\'rniga — 2 ta rasmiy korporativ keys',

    val_company_title: 'Kompaniyalarga (HR)',
    val_company_sub: 'CV saralamasdan, tayyor kadrlarni topish',
    val_company_tag: 'HR Portali',
    val_company_top_nominee: 'Top Nomzod',
    val_company_action: 'Taklif',
    val_company_stat: '100 ta bo\'sh rezyume o\'rniga — faqat amalda 85%+ olgan kadrlar',

    val_edu_title: 'Universitetlarga',
    val_edu_sub: 'Amaliyot va ishga joylashish nazorati',
    val_edu_tag: 'OTM Monitoringi',
    val_edu_rate: 'UrDU Amaliyot Dinamikasi',
    val_edu_pdf: 'PDF Hisobot',
    val_edu_stat: 'Qog\'ozdagi formal amaliyotlar o\'rniga — 100% raqamli monitoring',

    // CTA
    cta_title_1: 'Karyerangizni bugunoq',
    cta_title_2: 'amaliy tajriba bilan boshlang.',
    cta_desc: 'Hech qanday to\'lov yo\'q. Faqat siz, real korporativ vazifalar va sizni kutayotgan ish beruvchilar.',
    cta_btn: 'Hoziroq Boshlash — Bepul',
    cta_badge_1: '100% Bepul Kirish',
    cta_badge_2: 'Rasmiy Sertifikat',
    cta_badge_3: 'Ish Beruvchilar Nazorati',

    // Catalog Page
    cat_all_programs: 'Barcha Dasturlar',
    cat_title: 'Ish Simulyatsiyalari Katalogi',
    cat_desc: 'O\'zingizni qiziqtirgan sohani tanlang va 100% bepul amaliy loyihalarda qatnashib, rezyumengiz uchun tasdiqlangan tajribaga ega bo\'ling.',
    cat_search_placeholder: 'Simulyatsiya, kompaniya yoki soha bo\'yicha qidirish...',
    cat_filter_all: 'Barchasi',
    cat_filter_eng: 'Dasturiy Muhandislik',
    cat_filter_fin: 'Bank & Moliya',
    cat_filter_data: 'Biznes Tahlil & Data',
    cat_filter_legal: 'Huquq & Audit',
    cat_filter_cyber: 'Kiberxavfsizlik & AI',
    cat_diff_all: 'Barcha darajalar',
    cat_diff_junior: 'Junior (Boshlang\'ich)',
    cat_diff_middle: 'Middle (O\'rta)',
    cat_diff_senior: 'Senior (Ilg\'or)',
    cat_hours_suffix: 'soat',
    cat_tasks_suffix: 'ta vazifa',
    cat_start_btn: 'Simulyatsiyani Boshlash',
    cat_verified_partner: 'Tasdiqlangan Hamkor',
    cat_learning_outcomes: 'O\'rganiladigan bilimlar:',
    cat_creator_tag: 'Kompaniyalar & Mualliflar',
    cat_creator_desc: 'O\'z kompaniyangiz uchun yangi keys va amaliy simulyatsiya yaratmoqchimisiz?',
    cat_creator_btn: 'Simulyatsiya Konstruktori',
    cat_no_results: 'So\'rovingiz bo\'yicha simulyatsiyalar topilmadi.',
    cat_reset_filters: 'Filtrlarni tozalash',
    cat_showing_results: 'ta simulyatsiya ko\'rsatilmoqda',

    // Footer
    footer_desc: 'Talabalarga ishga kirmasdan turib real kompaniyalar ish tajribasini beruvchi, portfoliosini kuchaytiruvchi va rasmiy sertifikat taqdim etuvchi virtual amaliyot platformasi.',
    footer_simulations: 'Simulyatsiyalar',
    footer_cat_1: 'Dasturiy Muhandislik & Kiberxavfsizlik',
    footer_cat_2: 'Bank & Moliyaviy Tahlil',
    footer_cat_3: 'Biznes Tahlil & Konsalting',
    footer_cat_4: 'Yuridik & Hujjatlar Auditi',
    footer_partners: 'Xalqaro Hamkorlar',
    footer_security_title: 'Xavfsizlik & Standartlar',
    footer_security_badge: '100% Rasmiy Tasdiqlangan Sertifikat',
    footer_security_desc: 'Barcha berilgan sertifikatlar ommaviy QR-kod orqali ish beruvchilar tomonidan darhol tekshiriladi.',
    footer_rights: 'Barcha huquqlar himoyalangan.',
    footer_made_in: 'Toshkentda tayyorlangan'
  },

  ru: {
    // Nav
    nav_simulations: 'Симуляции',
    nav_case_cup: 'Case Cup',
    nav_talent_hunt: 'Talent Hunt',
    nav_university: 'Университет',
    nav_create_simulation: 'Создать симуляцию',

    // Hero
    hero_title_1: 'Забудьте о резюме.',
    hero_title_2: 'Покажите ваши навыки.',
    hero_desc: 'Выполняйте реальные задачи ведущих компаний без трудоустройства, набирайтесь опыта и получайте прямые офферы на работу.',
    hero_btn_start: 'Начать симуляцию',
    hero_btn_companies: 'Для компаний',
    hero_offer_sent: 'Оффер отправлен',
    hero_offer_desc: 'Прямое приглашение на основе 92% результата',
    hero_badge_live: 'Реальный опыт работы',
    hero_badge_partner: 'Топ кейсы компаний',

    // Stats Bar
    landing_stats_students: '5,000+ Студентов',
    landing_stats_students_sub: 'Успешно завершили практику',
    landing_stats_partners: '24+ Компании',
    landing_stats_partners_sub: 'Ведущие работодатели нанимают здесь',
    landing_stats_rate: '94% Результат',
    landing_stats_rate_sub: 'Получают оффер после сертификации',
    landing_stats_free: '100% Бесплатно',
    landing_stats_free_sub: 'Для всех студентов и кандидатов',
    landing_company_logos_title: 'В ПАРТНЕРСТВЕ С ВЕДУЩИМИ КОМПАНИЯМИ УЗБЕКИСТАНА И МИРА',

    // Featured Simulations on Landing
    landing_featured_badge: 'Рекомендуемые',
    landing_featured_title: 'Популярные симуляции',
    landing_featured_sub: 'Начните карьеру с реальных практических задач от лучших работодателей',
    landing_featured_view_all: 'Смотреть все симуляции',

    // Problem Section
    problem_tag: 'Главная проблема и решение',
    problem_title: 'Преодолейте 3-летний барьер в карьере',
    problem_quote: '«Чтобы устроиться на работу нужен опыт, а чтобы получить опыт — не берут на работу.»',
    old_way_title: 'Старый путь (Замкнутый круг)',
    old_way_desc: '4 года сухой теории ➔ 100+ отправленных пустых резюме ➔ Отказы «У вас нет опыта».',
    tryjob_way_title: 'Решение TryJob (Прямой результат)',
    tryjob_way_desc: '5 часов практической симуляции ➔ Реальные корпоративные задачи ➔ Доказанное портфолио и прямой оффер.',

    // How it works
    steps_tag: 'Простой и понятный процесс',
    steps_title: 'Как работает TryJob?',
    step_1_title: 'Выберите кейс компании',
    step_1_desc: 'Выберите отраслевую симуляцию от ведущих брендов: Kapitalbank, Uzum, PwC, JPMorgan и др.',
    step_2_title: 'Выполните реальную задачу',
    step_2_desc: 'Никакой теории — анализируйте реальные данные, проверяйте документы, пишите код и получайте оценку от AI-ментора.',
    step_3_title: 'Получите предложение о работе',
    step_3_desc: 'Ваши результаты видны в HR-портале, и работодатели приглашают вас на работу напрямую.',
    ai_realtime_review: 'AI-ревью в реальном времени',
    ai_automated: '100% Автоматизировано',

    // Value Section
    value_tag: 'Гарантированная ценность',
    value_title: 'Четкая выгода для каждого участника',
    
    val_student_title: 'Студентам',
    val_student_sub: 'Трудоустройство без резюме с реальным доказательством навыков',
    val_student_free: '100% Бесплатно',
    val_student_stat: 'Вместо 0 лет опыта в резюме — 2 подтвержденных корпоративных кейса',

    val_company_title: 'Компаниям (HR)',
    val_company_sub: 'Поиск готовых кадров без ручного скрининга CV',
    val_company_tag: 'HR Портал',
    val_company_top_nominee: 'Топ кандидат',
    val_company_action: 'Оффер',
    val_company_stat: 'Вместо 100 пустых резюме — только кандидаты с 85%+ практики',

    val_edu_title: 'Университетам',
    val_edu_sub: 'Контроль практики и содействие трудоустройству',
    val_edu_tag: 'Мониторинг вуза',
    val_edu_rate: 'Динамика практики вуза',
    val_edu_pdf: 'PDF Отчет',
    val_edu_stat: 'Вместо бумажных формальных практик — 100% цифровой мониторинг',

    // CTA
    cta_title_1: 'Начните вашу карьеру',
    cta_title_2: 'с реальным практическим опытом уже сегодня.',
    cta_desc: 'Никаких оплат. Только вы, реальные бизнес-задачи и работодатели, которые ждут вас.',
    cta_btn: 'Начать сейчас — Бесплатно',
    cta_badge_1: '100% Бесплатный доступ',
    cta_badge_2: 'Официальный сертификат',
    cta_badge_3: 'Прямой контакт с HR',

    // Catalog Page
    cat_all_programs: 'Все программы',
    cat_title: 'Каталог рабочих симуляций',
    cat_desc: 'Выберите интересующую сферу и участвуйте в 100% бесплатных практических проектах, получая подтвержденный опыт для резюме.',
    cat_search_placeholder: 'Поиск симуляций, компаний или навыков...',
    cat_filter_all: 'Все',
    cat_filter_eng: 'Разработка ПО',
    cat_filter_fin: 'Банки и финансы',
    cat_filter_data: 'Бизнес-анализ и Data',
    cat_filter_legal: 'Право и аудит',
    cat_filter_cyber: 'Кибербезопасность & AI',
    cat_diff_all: 'Все уровни',
    cat_diff_junior: 'Junior (Начальный)',
    cat_diff_middle: 'Middle (Средний)',
    cat_diff_senior: 'Senior (Продвинутый)',
    cat_hours_suffix: 'ч.',
    cat_tasks_suffix: 'заданий',
    cat_start_btn: 'Начать симуляцию',
    cat_verified_partner: 'Верифицированный партнер',
    cat_learning_outcomes: 'Приобретаемые навыки:',
    cat_creator_tag: 'Компаниям и авторам',
    cat_creator_desc: 'Хотите создать кейс и практическую симуляцию для вашей компании?',
    cat_creator_btn: 'Конструктор симуляций',
    cat_no_results: 'По вашему запросу симуляций не найдено.',
    cat_reset_filters: 'Сбросить фильтры',
    cat_showing_results: 'симуляций найдено',

    // Footer
    footer_desc: 'Платформа виртуальных стажировок, дающая студентам реальный корпоративный опыт, сильное портфолио и официальный сертификат до трудоустройства.',
    footer_simulations: 'Симуляции',
    footer_cat_1: 'Инженерия и кибербезопасность',
    footer_cat_2: 'Банки и финансовый анализ',
    footer_cat_3: 'Бизнес-анализ и консалтинг',
    footer_cat_4: 'Юридический аудит документов',
    footer_partners: 'Международные партнеры',
    footer_security_title: 'Безопасность и стандарты',
    footer_security_badge: '100% Подтвержденный сертификат',
    footer_security_desc: 'Все выданные сертификаты мгновенно проверяются работодателями через публичный QR-код.',
    footer_rights: 'Все права защищены.',
    footer_made_in: 'Сделано в Ташкенте'
  },

  en: {
    // Nav
    nav_simulations: 'Simulations',
    nav_case_cup: 'Case Cup',
    nav_talent_hunt: 'Talent Hunt',
    nav_university: 'University',
    nav_create_simulation: 'Create Simulation',

    // Hero
    hero_title_1: 'Forget the resume.',
    hero_title_2: 'Showcase your skills.',
    hero_desc: 'Solve real tasks from top companies before getting hired, gain proven corporate experience, and get direct job offers.',
    hero_btn_start: 'Start Simulation',
    hero_btn_companies: 'For Employers',
    hero_offer_sent: 'Offer Sent',
    hero_offer_desc: 'Direct hiring invitation based on 92% score',
    hero_badge_live: 'Real Work Experience',
    hero_badge_partner: 'Top Corporate Cases',

    // Stats Bar
    landing_stats_students: '5,000+ Students',
    landing_stats_students_sub: 'Completed simulated internships',
    landing_stats_partners: '24+ Companies',
    landing_stats_partners_sub: 'Top enterprises hiring directly',
    landing_stats_rate: '94% Outcome',
    landing_stats_rate_sub: 'Direct interview offers after certificate',
    landing_stats_free: '100% Free',
    landing_stats_free_sub: 'Open for all students & applicants',
    landing_company_logos_title: 'IN COLLABORATION WITH INDUSTRY LEADERS IN UZBEKISTAN & GLOBALLY',

    // Featured Simulations on Landing
    landing_featured_badge: 'Featured',
    landing_featured_title: 'Popular Simulations',
    landing_featured_sub: 'Launch your career by tackling actual corporate challenges from top employers',
    landing_featured_view_all: 'Explore All Simulations',

    // Problem Section
    problem_tag: 'The Core Challenge & Solution',
    problem_title: 'Break through the 3-year experience gap',
    problem_quote: '"You need experience to get a job, but you need a job to get experience."',
    old_way_title: 'The Old Way (The Endless Loop)',
    old_way_desc: '4 years of dry theory ➔ 100+ rejected blank resumes ➔ "No experience" rejections.',
    tryjob_way_title: 'The TryJob Way (Direct Outcome)',
    tryjob_way_desc: '5-hour practical simulation ➔ Real corporate tasks solved ➔ Verified portfolio & direct job offers.',

    // How it works
    steps_tag: 'Simple & Transparent Process',
    steps_title: 'How does TryJob work?',
    step_1_title: 'Choose a Company Case',
    step_1_desc: 'Select industry simulations from leaders like Kapitalbank, Uzum, PwC, and JPMorgan.',
    step_2_title: 'Complete the Real Task',
    step_2_desc: 'Zero fluff — analyze live data, audit compliance docs, write clean code, and receive instant AI feedback.',
    step_3_title: 'Get Hired Directly',
    step_3_desc: 'Your verified scores appear on the recruiter talent board, skipping resume filters.',
    ai_realtime_review: 'Real-time AI Review',
    ai_automated: '100% Automated',

    // Value Section
    value_tag: 'Guaranteed Value',
    value_title: 'Proven outcomes for all stakeholders',
    
    val_student_title: 'For Students',
    val_student_sub: 'Get hired without resumes through proven work samples',
    val_student_free: '100% Free',
    val_student_stat: 'Instead of 0 years experience — 2 verified corporate deliverables',

    val_company_title: 'For Employers (HR)',
    val_company_sub: 'Hire job-ready talent without screening hundreds of resumes',
    val_company_tag: 'HR Portal',
    val_company_top_nominee: 'Top Candidate',
    val_company_action: 'Offer',
    val_company_stat: 'Instead of 100 blank resumes — only talent scoring 85%+ on real tasks',

    val_edu_title: 'For Universities',
    val_edu_sub: 'Streamline internship monitoring and employment rate',
    val_edu_tag: 'Higher Ed Portal',
    val_edu_rate: 'University Internship Progress',
    val_edu_pdf: 'PDF Report',
    val_edu_stat: 'Replace paper bureaucracy with 100% verified digital monitoring',

    // CTA
    cta_title_1: 'Launch your career',
    cta_title_2: 'with real work experience today.',
    cta_desc: 'Completely free. Just you, real enterprise challenges, and recruiters waiting to hire you.',
    cta_btn: 'Get Started — It\'s Free',
    cta_badge_1: '100% Free Access',
    cta_badge_2: 'Verified Credentials',
    cta_badge_3: 'Direct Employer Access',

    // Catalog Page
    cat_all_programs: 'All Programs',
    cat_title: 'Work Simulations Catalog',
    cat_desc: 'Choose your field of interest and complete 100% free practical projects to gain verified experience for your resume.',
    cat_search_placeholder: 'Search simulations, companies, or skills...',
    cat_filter_all: 'All',
    cat_filter_eng: 'Software Engineering',
    cat_filter_fin: 'Banking & Finance',
    cat_filter_data: 'Business Analytics & Data',
    cat_filter_legal: 'Legal & Audit',
    cat_filter_cyber: 'Cybersecurity & AI',
    cat_diff_all: 'All Levels',
    cat_diff_junior: 'Junior (Beginner)',
    cat_diff_middle: 'Middle (Intermediate)',
    cat_diff_senior: 'Senior (Advanced)',
    cat_hours_suffix: 'hrs',
    cat_tasks_suffix: 'tasks',
    cat_start_btn: 'Start Simulation',
    cat_verified_partner: 'Verified Partner',
    cat_learning_outcomes: 'Key Learning Outcomes:',
    cat_creator_tag: 'Companies & Creators',
    cat_creator_desc: 'Want to create a custom case and practical simulation for your company?',
    cat_creator_btn: 'Simulation Builder',
    cat_no_results: 'No simulations found matching your criteria.',
    cat_reset_filters: 'Reset Filters',
    cat_showing_results: 'simulations displayed',

    // Footer
    footer_desc: 'Virtual work experience platform empowering students with real corporate skills, verified portfolios, and official certifications before getting hired.',
    footer_simulations: 'Simulations',
    footer_cat_1: 'Software Engineering & Cybersecurity',
    footer_cat_2: 'Banking & Financial Analysis',
    footer_cat_3: 'Business Analytics & Consulting',
    footer_cat_4: 'Legal Audit & Document Compliance',
    footer_partners: 'Global Partners',
    footer_security_title: 'Security & Standards',
    footer_security_badge: '100% Officially Verified Certificate',
    footer_security_desc: 'All issued certificates can be instantly verified by employers via public QR verification.',
    footer_rights: 'All rights reserved.',
    footer_made_in: 'Built in Tashkent'
  }
};
