# TryJob — Pitch Day sayti

Statik sayt (build yo'q): `index.html` — pitch, `demo/` — demo-video sahifasi,
`api/v1/project.json` — ochiq loyiha ma'lumoti, `api/chat.js` — AI yordamchi (Vercel funksiyasi).

Sozlash — `assets/app.js` boshidagi `CONFIG`: YouTube havolasi (`youtube`), jamoa (`team`),
prototip manzili (`prototype`), AI chat manzili (`chatApi`).

Joylash:
- **Vercel** (AI chatbot bilan): repo'ni import qiling, Root Directory — `pitch`, Environment Variables'ga
  `DEEPSEEK_API_KEY` qo'shing. `/api/chat` DeepSeek'ga so'rov yuboradi, kalit brauzerga chiqmaydi.
- **GitHub Pages**: `pitch/` mazmunini `gh-pages` branch ildiziga qo'ying. Chatbot bu holda
  `CONFIG.chatApi` (masalan Vercel'dagi funksiya) orqali yoki tayyor savol-javoblar bilan ishlaydi.

Lokal ko'rish: `python3 -m http.server -d pitch 8000`.
