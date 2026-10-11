/* TryJob Pitch Day sayti: ikonkalar, animatsiyalar, galereya, demo-video va AI yordamchi. */

// ---------- SOZLAMALAR (shu yerni tahrirlang) ----------
const CONFIG = {
  // YouTube havolasi yoki video ID (masalan "https://youtu.be/XXXX"). Bo'sh bo'lsa — mp4 fayl yoki namuna.
  youtube: "",
  // Yoki saytdagi fayl (assets/ papkasiga nisbatan): "demo.mp4"
  videoFile: "demo.mp4",
  // AI chatbot (DeepSeek) manzili. Bo'sh bo'lsa — shu saytning /api/chat (Vercel'da).
  // Ishlamasa, yordamchi tayyor savol-javob namunalari bilan javob beradi.
  chatApi: "",
  // Ishlayotgan prototip manzili (bo'lsa)
  prototype: "https://guli.b-code.uz/",
  repo: "https://github.com/Baxrom0311/train",
  // photo: "assets/img/team/guli.webp" kabi — rasm qo'yilsa avatar o'rniga chiqadi
  team: [
    {
      name: "Guli Salayeva",
      role: "Asoschi · Team Lead · Biznes-analitik",
      exp: "3+ yil",
      colors: ["#8b7bff", "#c25cf0"],
      photo: "",
      did: ["Mahsulot strategiyasi va B2B2C model", "Ssenariy kontenti va baholash rubrikalari", "Universitet va kompaniyalar bilan hamkorlik"],
      skills: ["Product", "Biznes-tahlil", "Jamoa boshqaruvi"],
      links: {},
    },
    {
      name: "Muhayyo Normatova",
      role: "Backend · AI/ML Engineer",
      exp: "4+ yil",
      colors: ["#6d7bff", "#2ed3e6"],
      photo: "",
      did: ["FastAPI va ssenariy dvigateli", "AI baho, AI mentor va RAG", "Kod sandbox va xavfsizlik"],
      skills: ["Python", "FastAPI", "LLM", "PostgreSQL"],
      links: {},
    },
    {
      name: "Sarvara Eshchanova",
      role: "Frontend · UI/UX dizayner",
      exp: "4+ yil",
      colors: ["#2ed3e6", "#34d399"],
      photo: "",
      did: ["Liquid glass dizayn tizimi", "Ish stoli, hisobot va sertifikat", "PWA va mobil tajriba"],
      skills: ["React", "TypeScript", "Figma", "UX"],
      links: {},
    },
  ],
};

// ---------- ikonkalar ----------
const ICONS = {
  arrow: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  briefcase: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  grad: '<path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  bot: '<rect x="3" y="8" width="18" height="12" rx="3"/><path d="M12 8V4H8M2 14h1M21 14h1M15 13v2M9 13v2"/>',
  sparkles: '<path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/><path d="M19 3v4M17 5h4"/>',
  award: '<circle cx="12" cy="8" r="6"/><path d="M15.5 13.5 17 22l-5-3-5 3 1.5-8.5"/>',
  send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/>',
  userx: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 8 5 5M22 8l-5 5"/>',
  doc: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M10 13a2 2 0 1 1 3 1.7c-.6.4-1 .8-1 1.3M12 19h.01"/>',
  hourglass: '<path d="M5 22h14M5 2h14M17 22v-4.2a2 2 0 0 0-.6-1.4L12 12l-4.4 4.4a2 2 0 0 0-.6 1.4V22M7 2v4.2a2 2 0 0 0 .6 1.4L12 12l4.4-4.4a2 2 0 0 0 .6-1.4V2"/>',
  monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
  layers: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
  github: '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
  linkedin: '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>',
  telegram: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
  play: '<path d="M7 4v16l13-8z" fill="currentColor" stroke="none"/>',
  msg: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  code: '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
  chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 6-6"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  rocket: '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.9A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2z"/><path d="M9 12H4s.6-3 2-4c1.6-1.1 5 0 5 0M12 15v5s3-.6 4-2c1.1-1.6 0-5 0-5"/>',
  bulb: '<path d="M9 18h6M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/>',
  flask: '<path d="M9 3h6M10 3v6L4 20a1 1 0 0 0 .9 1.5h14.2A1 1 0 0 0 20 20l-6-11V3"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  db: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10a7 7 0 0 1-14 0M12 17v5"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  ext: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  phone: '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/>',
  terminal: '<path d="m4 17 6-6-6-6M12 19h8"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
};
(function injectSprite() {
  const sym = Object.entries(ICONS)
    .map(([k, p]) => `<symbol id="i-${k}" viewBox="0 0 24 24">${p}</symbol>`)
    .join("");
  const div = document.createElement("div");
  div.style.display = "none";
  div.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg">${sym}</svg>`;
  document.body.prepend(div);
})();
const ASSETS = new URL("./", document.currentScript.src).href;
const IMG = ASSETS + "img/";
const icon = (k) => `<svg class="ico"><use href="#i-${k}"/></svg>`;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// ---------- kun / tun ----------
const themeBtn = $("#theme-btn");
if (themeBtn)
  themeBtn.addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("tj-theme", t); } catch (e) {}
  });

// ---------- jamoa ----------
const avatar = (m, i) => {
  if (m.photo) return `<img src="${m.photo}" alt="${m.name}">`;
  const [a, b] = m.colors;
  return `<svg viewBox="0 0 88 88" aria-hidden="true">
    <defs><linearGradient id="av${i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>
    <rect width="88" height="88" fill="url(#av${i})"/>
    <path d="M44 17c-13 0-20 9-20 22v20c0 6-2 10-5 13h50c-3-3-5-7-5-13V39c0-13-7-22-20-22z" fill="#1b1640" opacity=".55"/>
    <path d="M12 88c2-14 15-22 32-22s30 8 32 22z" fill="#fff" opacity=".95"/>
    <rect x="38" y="52" width="12" height="14" rx="5" fill="#fff"/>
    <ellipse cx="44" cy="41" rx="13" ry="15" fill="#fff"/>
    <path d="M30 40c1-11 7-17 15-17 9 0 14 6 14 14-9 0-17-3-22-9-1 5-3 9-7 12z" fill="#1b1640" opacity=".7"/>
  </svg>`;
};
const teamEl = $("#team");
if (teamEl) {
  teamEl.innerHTML = CONFIG.team
    .map(
      (m, i) => `
    <div class="member glass rv d${i % 4}">
      <div class="avatar" style="--a:${m.colors[0]};--b:${m.colors[1]}">${avatar(m, i)}<span class="exp">${m.exp}</span></div>
      <h3>${m.name}</h3>
      <div class="role">${m.role}</div>
      <ul class="did">${m.did.map((d) => `<li>${icon("check")}${d}</li>`).join("")}</ul>
      <div class="tags">${m.skills.map((s) => `<span>${s}</span>`).join("")}</div>
      ${Object.keys(m.links).length ? `<div class="links">${Object.entries(m.links)
        .map(([k, u]) => `<a href="${u}" target="_blank" rel="noopener" aria-label="${k}">${icon(k)}</a>`)
        .join("")}</div>` : ""}
    </div>`
    )
    .join("");
}

// ---------- paydo bo'lish + raqamlar ----------
const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      $$("[data-count]", e.target).forEach(countUp);
      io.unobserve(e.target);
    });
  },
  { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
);
$$(".rv, .road").forEach((el) => io.observe(el));

function countUp(el) {
  const end = +el.dataset.count;
  const suf = el.dataset.suffix || "";
  const t0 = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - t0) / 1200);
    el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))) + suf;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---------- navbar faol havola ----------
const navLinks = $$(".nav-links a[href^='#']");
if (navLinks.length) {
  const secIo = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting)
          navLinks.forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
      });
    },
    { rootMargin: "-45% 0px -50% 0px" }
  );
  navLinks.forEach((a) => {
    const s = $(a.getAttribute("href"));
    if (s) secIo.observe(s);
  });
}

// ---------- galereya ----------
const SHOTS = {
  desk: ["Ish stoli", "kiruvchi xatlar, vazifa, AI baho va mentor chati"],
  report: ["AI hisobot", "kompetensiyalar, kuchli tomonlar, rivojlanish"],
  cert: ["Sertifikat", "TJ-kod, QR va ochiq tekshiruv"],
  talents: ["Kompaniya", "nomzodlar real natijalar bo'yicha"],
  team: ["Jamoaviy ish", "bir ssenariyda bir nechta talaba"],
  university: ["Universitet", "talabalar natijalari bir oynada"],
};
const shot = $("#shot");
$$(".tab[data-shot]").forEach((b) =>
  b.addEventListener("click", () => {
    $$(".tab[data-shot]").forEach((x) => x.classList.toggle("on", x === b));
    const k = b.dataset.shot;
    shot.style.opacity = 0;
    setTimeout(() => {
      shot.onload = () => (shot.style.opacity = 1);
      shot.src = `${IMG}${k}.webp`;
      $("#shot-cap").innerHTML = `<b>${SHOTS[k][0]}</b> — ${SHOTS[k][1]}`;
    }, 200);
  })
);
// oldindan yuklash (faqat galereya bor sahifada)
if (shot)
  Object.keys(SHOTS).forEach((k) => {
    const i = new Image();
    i.src = `${IMG}${k}.webp`;
  });

// ---------- demo-video ----------
function ytId(s) {
  if (!s) return "";
  const m = s.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? m[1] : /^[\w-]{11}$/.test(s) ? s : "";
}
const vid = $("#vid");
function playVideo(start = 0) {
  if (!vid) return;
  const id = ytId(CONFIG.youtube);
  if (id) {
    vid.innerHTML = `<iframe src="https://www.youtube.com/embed/${id}?autoplay=1&rel=0&start=${start}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="TryJob demo"></iframe>`;
  } else if (CONFIG.videoFile) {
    let v = $("video", vid);
    if (!v) {
      const src = new URL(CONFIG.videoFile, ASSETS).href;
      vid.innerHTML = `<video src="${src}" controls playsinline></video>`;
      v = $("video", vid);
    }
    v.currentTime = start;
    v.play().catch(() => {});
  }
}
if (vid) {
  const ready = ytId(CONFIG.youtube) || CONFIG.videoFile;
  if (!ready) $(".soon", vid).hidden = false;
  $(".poster", vid).addEventListener("click", () => playVideo(0));
  $$(".chapters li").forEach((li) =>
    li.addEventListener("click", () => {
      const t = li.querySelector("time").textContent;
      if (!t.includes(":")) return; // vaqt belgilari video kelganda qo'yiladi
      const [m, s] = t.split(":").map(Number);
      playVideo(m * 60 + s);
      vid.scrollIntoView({ behavior: "smooth", block: "center" });
    })
  );
}
const protoEl = $("#proto-live");
if (protoEl && CONFIG.prototype) {
  protoEl.href = CONFIG.prototype;
  protoEl.querySelector("small").textContent = CONFIG.prototype.replace(/^https?:\/\//, "");
  protoEl.hidden = false;
}

// ---------- AI yordamchi (savol-javob namunalari) ----------
const QA = [
  { k: ["nima", "tryjob", "haqida", "loyiha"], q: "TryJob nima?", a: "TryJob — virtual ish simulyatsiyasi. Talaba real vaqtda «ish kuni»dan o'tadi: hamkasblar xat yozadi, vazifa va dedlayn keladi. AI har javobni baholaydi, mentor izoh beradi." },
  { k: ["kim", "uchun", "talaba", "foydalan"], q: "Kimlar uchun?", a: "Uch tomon uchun: talaba (bepul tajriba va sertifikat), kompaniya (isbotlangan nomzodlar), universitet (talabalar natijasi bir oynada)." },
  { k: ["pul", "narx", "to'lov", "bepul", "daromad", "biznes", "model"], q: "Qanday pul topadi?", a: "B2B2C: talaba uchun bepul. Kompaniya nomzod qidirish va vakansiya uchun, universitet portal uchun to'laydi (invoice orqali)." },
  { k: ["ai", "baho", "sun'iy", "llm", "intellekt"], q: "AI nima qiladi?", a: "LLM javobni rubrika bo'yicha baholaydi (0–100), mentor sifatida izoh va eslatma yozadi, AI suhbat mashqini o'tkazadi. Kod vazifalari esa yashirin testlar bilan sandbox'da tekshiriladi." },
  { k: ["soha", "ssenariy", "yo'nalish"], q: "Qaysi sohalar bor?", a: "Hozir 5 soha: IT, Bank, Marketing, Data va HR. Ssenariy muharriri orqali yangilari tez qo'shiladi." },
  { k: ["sertifikat", "tekshir", "qr"], q: "Sertifikat ishonchlimi?", a: "Ha. Har sertifikatda TJ-XXXX-XXXX kodi va QR bor — istalgan kishi ochiq sahifada tekshira oladi." },
  { k: ["forage", "farq", "raqobat", "kurs"], q: "Kurslardan farqi?", a: "Kurs — video va test. TryJob — real ish kuni: vaqt bosimi, kutilmagan vaziyatlar, hamkasblar bilan muloqot. Natija — kompaniya ko'radigan isbot." },
  { k: ["texnolog", "stack", "react", "fastapi"], q: "Qaysi texnologiyalar?", a: "React + TypeScript, FastAPI, PostgreSQL + pgvector, Redis + arq, LLM, Docker. PWA — telefonga o'rnatiladi." },
  { k: ["bosqich", "holat", "mvp", "qachon", "reja"], q: "Hozir qaysi bosqichda?", a: "Prototip tayyor, MVP bosqichidamiz: noyabrda pilot universitetlar, 2027-yil boshida ochiq ishga tushirish." },
  { k: ["jamoa", "kim qildi", "asoschi"], q: "Jamoa kim?", a: "3 mutaxassis: Guli Salayeva — asoschi, team lead va biznes-analitik; Muhayyo Normatova — backend va AI/ML muhandis; Sarvara Eshchanova — frontend va UI/UX dizayner." },
];
const AI_SYSTEM = `Sen TryJob loyihasining AI yordamchisisan (Pitch Day 3.0 sayti). Faqat o'zbek tilida (lotin), qisqa javob ber: 1–3 jumla. Loyihadan tashqari mavzularda muloyimlik bilan TryJob'ga qaytar.
Faktlar: ${QA.map((x) => x.a).join(" ")} Ssenariylardagi kompaniyalar to'qima. Manba kodi: github.com/Baxrom0311/train.`;
const SUGG = ["TryJob nima?", "AI nima qiladi?", "Qanday pul topadi?", "Kurslardan farqi?"];

function answer(text) {
  const t = text.toLowerCase().replace(/[‘’ʻʼ`]/g, "'");
  let best = null, score = 0;
  QA.forEach((x) => {
    const s = x.k.reduce((n, k) => n + (t.includes(k) ? 1 : 0), 0) + (t === x.q.toLowerCase() ? 5 : 0);
    if (s > score) { score = s; best = x; }
  });
  return best ? best.a : "Bu savolga hozircha javobim yo'q. Quyidagilardan birini so'rab ko'ring yoki demo-videoni ko'ring 🙂";
}

(function bot() {
  const wrap = document.createElement("div");
  wrap.innerHTML = `
    <button class="bot-fab" aria-label="AI yordamchi">${icon("msg")}</button>
    <div class="bot glass" role="dialog" aria-label="TryJob AI yordamchi">
      <div class="bot-head">
        <span class="logo-mark">T</span>
        <div><b>TryJob AI</b><small>● onlayn</small></div>
        <button aria-label="Yopish">${icon("x")}</button>
      </div>
      <div class="bot-body"></div>
      <div class="sugg"></div>
      <form class="bot-form"><input placeholder="Savol yozing…" aria-label="Savol"><button aria-label="Yuborish">${icon("send")}</button></form>
    </div>`;
  document.body.append(wrap);
  const panel = $(".bot", wrap), body = $(".bot-body", wrap), sugg = $(".sugg", wrap), input = $("input", wrap);
  const add = (cls, text) => {
    const m = document.createElement("div");
    m.className = "msg " + cls;
    m.textContent = text;
    body.append(m);
    body.scrollTop = body.scrollHeight;
    return m;
  };
  const renderSugg = () => {
    sugg.innerHTML = SUGG.map((s) => `<button type="button">${s}</button>`).join("");
    $$("button", sugg).forEach((b) => b.addEventListener("click", () => ask(b.textContent)));
  };
  const history = [];
  const api = CONFIG.chatApi || new URL("../api/chat", document.currentScript.src).href;
  // Kalit faqat nashr nusxasida (assets/ai-key.js, gh-pages) bo'ladi — bo'lsa, DeepSeek'ga to'g'ridan-to'g'ri
  const dsKey = window.TJ_AI ? atob(String(window.TJ_AI).split("").reverse().join("")) : "";
  let aiOff = false;
  const callAI = async (signal) => {
    if (dsKey && !CONFIG.chatApi) {
      const r = await fetch("https://api.deepseek.com/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${dsKey}` },
        body: JSON.stringify({
          model: "deepseek-chat",
          messages: [{ role: "system", content: AI_SYSTEM }, ...history.slice(-8)],
          max_tokens: 300,
          temperature: 0.5,
        }),
        signal,
      });
      if (!r.ok) return { reply: "", off: r.status === 401 || r.status === 402 };
      const d = await r.json();
      return { reply: d?.choices?.[0]?.message?.content?.trim() || "" };
    }
    const r = await fetch(api, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
      signal,
    });
    if (r.ok) return { reply: (await r.json()).reply || "" };
    return { reply: "", off: [404, 405, 501, 503].includes(r.status) };
  };
  const ask = async (q) => {
    q = q.trim();
    if (!q) return;
    add("me", q);
    history.push({ role: "user", content: q });
    const ty = document.createElement("div");
    ty.className = "msg ai typing";
    ty.innerHTML = "<i></i><i></i><i></i>";
    body.append(ty);
    body.scrollTop = body.scrollHeight;
    let reply = "";
    if (!aiOff) {
      try {
        const ctl = new AbortController();
        const timer = setTimeout(() => ctl.abort(), 20000);
        const res = await callAI(ctl.signal);
        clearTimeout(timer);
        reply = res.reply;
        if (res.off) aiOff = true;
      } catch {
        /* tarmoq xatosi — namunaviy javob */
      }
    }
    if (!reply) {
      await new Promise((r) => setTimeout(r, 500));
      reply = answer(q);
    }
    ty.remove();
    add("ai", reply);
    history.push({ role: "assistant", content: reply });
  };
  let greeted = false;
  $(".bot-fab", wrap).addEventListener("click", () => {
    panel.classList.toggle("open");
    if (!greeted) { greeted = true; add("ai", "Salom! Men TryJob yordamchisiman. Loyiha haqida so'rang 👇"); renderSugg(); }
    if (panel.classList.contains("open")) input.focus({ preventScroll: true });
  });
  $(".bot-head button", wrap).addEventListener("click", () => panel.classList.remove("open"));
  $(".bot-form", wrap).addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); input.value = ""; });
})();
