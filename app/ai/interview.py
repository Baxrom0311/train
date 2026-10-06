from typing import Dict, Any, List
from app.ai.personas import get_mentor_persona
from app.ai.guardrail import inspect_prompt_safety

INTERVIEW_QUESTIONS = {
    "finance": [
        "Mijozning kredit qobiliyatini baholashda DTI (qarz yuklamasi) ko'rsatkichidan tashqari yana qanday muhim omillarga e'tibor berish kerak?",
        "Agar mijozning daromadi yetarli bo'lsa-yu, lekin kredit tarixi (KATM skoring) past bo'lsa, qanday qaror qabul qilgan bo'lardingiz?",
        "O'zbekiston Markaziy Banki tomonidan joriy qilingan makroprudensial cheklovlar haqida nimalarni bilasiz?"
    ],
    "engineering": [
        "FastAPI yoki REST API yozishda SQL Injection va XSS xatarlaridan qanday himoyalanish mumkin?",
        "Tizimda tranzaksiyalar xavfsizligi va ACID tamoyillarini qanday ta'minlaysiz?",
        "Ishlab chiqarishda (Production) yuz bergan to'lov xatosini (Payment Bug) tezkor aniqlash va tuzatish tartibi qanday bo'lishi kerak?"
    ],
    "legal": [
        "Yetkazib berish shartnomasida fors-major va jarima sanksiyalari bandlari qanday to'g'ri shakllantirilishi lozim?",
        "Didox yoki elektron hisob-faktura tizimida yuridik xatolik aniqlanganda qanday tuzatish hujjatlari rasmiylashtiriladi?"
    ]
}

class AIInterviewEngine:
    @classmethod
    def evaluate_interview_answer(
        cls,
        category: str,
        question: str,
        user_answer: str,
        mentor_persona_key: str = "lead_engineer"
    ) -> Dict[str, Any]:
        """
        Talabaning ish suhbatidagi javobini STARR uslubida tahlil qilish.
        """
        is_safe, err = inspect_prompt_safety(user_answer)
        if not is_safe:
            return {
                "score": 0.0,
                "passed": False,
                "feedback": err,
                "starr_breakdown": {
                    "situation": 0, "action": 0, "result": 0, "clarity": 0
                }
            }

        persona = get_mentor_persona(mentor_persona_key)
        ans_len = len(user_answer.strip())

        # STARR tahlil ballari
        if ans_len < 40:
            score = 35.0
            starr = {"situation": 10, "action": 10, "result": 5, "clarity": 10}
            feedback = "Javobingiz juda qisqa. Real intervyuda har bir fikrni amaliy misollar bilan isbotlash talab etiladi."
        elif ans_len < 150:
            score = 70.0
            starr = {"situation": 20, "action": 25, "result": 15, "clarity": 10}
            feedback = "Yaxshi javob! Asosiy tushunchalar to'g'ri ifodalangan, lekin natija va shaxsiy tajriba qismini ko'proq yoritsangiz bo'ladi."
        else:
            score = 90.0
            starr = {"situation": 25, "action": 25, "result": 20, "clarity": 20}
            feedback = f"Ajoyib va professional javob! {persona['company_tone']} talablariga to'liq mos keladi."

        return {
            "interviewer_name": persona["name"],
            "interviewer_role": persona["role"],
            "question": question,
            "score": score,
            "passed": score >= 60.0,
            "feedback": feedback,
            "starr_breakdown": starr,
            "recommendations": [
                "Fikringizni 'Muammo -> Yechim -> Natija' ketma-ketligida bayon qiling.",
                "O'zbekiston me'yoriy hujjatlari va texnik atamalardan to'g'ri foydalaning."
            ]
        }
