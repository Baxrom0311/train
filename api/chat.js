// TryJob Pitch sayti — AI yordamchi (DeepSeek). Vercel serverless funksiyasi: POST /api/chat
// Kalit faqat muhit o'zgaruvchisidan: DEEPSEEK_API_KEY (Vercel → Settings → Environment Variables).

const SYSTEM = `Sen TryJob loyihasining AI yordamchisisan (Pitch Day 3.0 sayti).
Faqat o'zbek tilida (lotin), qisqa javob ber: 1–3 jumla, ortiqcha so'zsiz. Loyihadan tashqari mavzularda muloyimlik bilan TryJob'ga qaytar.
Faktlar:
- TryJob — O'zbekiston talabalari uchun AI baholaydigan virtual ish simulyatsiyalari platformasi (The Forage'ning mahalliy, chuqurroq varianti).
- Talaba real vaqtdagi "ish kuni/haftasi"dan o'tadi (Toshkent vaqti, 09:00–18:00): hamkasblar xat yozadi, vazifa, dedlayn, kutilmagan vaziyat va qarorlar.
- LLM har javobni rubrika bo'yicha 0–100 baholaydi; AI mentor izoh, eslatma va yordam beradi. Kod vazifalari tarmoqsiz sandbox'da yashirin testlar bilan tekshiriladi.
- Natija: hisobot, kompetensiyalar, TJ-XXXX-XXXX kodli QR sertifikat, ochiq portfolio, avtomatik CV (uz/ru/en).
- Kompaniya: nomzodlarni Run natijalari bo'yicha ko'radi, vakansiya e'lon qiladi, sinov topshirig'i yuboradi, suhbat bosqichlari va ishga olish voronkasi.
- Universitet: o'z talabalarining natijalari portali. AI suhbat mashqi, jamoaviy Run, bildirishnomalar, PWA (telefonga o'rnatiladi).
- 5 soha: IT, Bank, Marketing, Data, HR; 6 ssenariy; 28+ modul kodda tayyor. Ssenariy muharriri bilan yangi ssenariy tez qo'shiladi.
- Model B2B2C: talaba bepul, kompaniya va universitet to'laydi (invoice orqali).
- Stack: React + TypeScript, FastAPI, PostgreSQL + pgvector (RAG), Redis + arq, LLM, Docker + Caddy.
- Bosqich: Idea va Prototype bajarildi, hozir MVP (noyabr 2026 — pilot universitetlar), Launch — 2027 1-chorak.
- Ssenariylardagi kompaniyalar to'qima (fictional). Manba kodi: github.com/Baxrom0311/train.`;

const hits = new Map(); // oddiy IP limit: daqiqasiga 8 ta so'rov

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST kerak" });

  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) return res.status(503).json({ error: "AI sozlanmagan" });

  const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0] || "anon";
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < 60_000);
  if (recent.length >= 8) return res.status(429).json({ error: "Biroz kuting" });
  hits.set(ip, [...recent, now]);

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }
  const history = Array.isArray(body?.messages) ? body.messages : [];
  const messages = history
    .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 600) }));
  if (!messages.length || messages[messages.length - 1].role !== "user")
    return res.status(400).json({ error: "Savol yo'q" });

  try {
    const r = await fetch("https://api.deepseek.com/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model: process.env.DEEPSEEK_MODEL || "deepseek-chat",
        messages: [{ role: "system", content: SYSTEM }, ...messages],
        max_tokens: 300,
        temperature: 0.5,
      }),
    });
    if (!r.ok) return res.status(502).json({ error: "AI javob bermadi" });
    const data = await r.json();
    const reply = data?.choices?.[0]?.message?.content?.trim();
    if (!reply) return res.status(502).json({ error: "Bo'sh javob" });
    return res.status(200).json({ reply });
  } catch {
    return res.status(502).json({ error: "AI bilan aloqa yo'q" });
  }
};
