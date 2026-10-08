"""
Zaxira savollar va suhbat shablonlari (CONTRACT.md §24.2).

LLM ishlamasa yoki yaroqsiz reja qaytarsa savollar shu yerdan olinadi —
suhbat AI'siz ham to'liq o'tadi. Tanlov suhbat `id`si bilan aniqlanadi
(bir xil suhbat — bir xil savollar).
"""
from __future__ import annotations

import random

INTRO = {
    "uz": [
        "O'zingiz haqingizda qisqacha gapirib bering: nimani o'rgandingiz va nega aynan «{position}» lavozimini tanladingiz?",
        "«{position}» lavozimiga qiziqishingiz qayerdan paydo bo'ldi va bizda birinchi yilda nimani o'rganishni xohlaysiz?",
    ],
    "ru": [
        "Расскажите кратко о себе: чему вы учились и почему выбрали именно позицию «{position}»?",
        "Откуда появился интерес к позиции «{position}» и чему вы хотите научиться у нас в первый год?",
    ],
    "en": [
        "Tell me briefly about yourself: what have you studied, and why did you choose the «{position}» role?",
        "Where does your interest in the «{position}» role come from, and what do you want to learn here in your first year?",
    ],
}

BEHAVIORAL = {
    "communication": {
        "uz": [
            "Murakkab narsani mavzudan uzoq odamga tushuntirishga to'g'ri kelgan holatni aytib bering. Qanday tushuntirdingiz va u tushunganini qanday bildingiz?",
            "Jamoadoshingiz yoki o'qituvchingiz bilan fikringiz to'g'ri kelmagan holatni eslang. Nima qildingiz va qanday kelishdingiz?",
        ],
        "ru": [
            "Расскажите о ситуации, когда нужно было объяснить сложную вещь человеку не из темы. Как вы объясняли и как поняли, что он понял?",
            "Вспомните случай, когда вы не сошлись во мнениях с коллегой или преподавателем. Что вы сделали и к чему пришли?",
        ],
        "en": [
            "Tell me about a time you had to explain something complex to someone outside the topic. How did you do it, and how did you know they understood?",
            "Recall a time you disagreed with a teammate or a teacher. What did you do, and how was it resolved?",
        ],
    },
    "prioritization": {
        "uz": [
            "Bir vaqtda bir nechta muhim ish tushib qolgan holatni aytib bering. Qaysi birini birinchi qildingiz va nega?",
            "Hamma narsani o'z vaqtida qilib bo'lmasligini tushungan paytingizni eslang. Nimadan voz kechdingiz va buni kimga qanday aytdingiz?",
        ],
        "ru": [
            "Расскажите о ситуации, когда одновременно навалилось несколько важных задач. Что вы сделали первым и почему?",
            "Вспомните момент, когда стало ясно, что всё вовремя не успеть. От чего вы отказались и как сообщили об этом?",
        ],
        "en": [
            "Tell me about a time several important tasks landed at once. What did you do first, and why?",
            "Recall a moment when you realised you couldn't finish everything on time. What did you drop, and how did you communicate it?",
        ],
    },
    "time_management": {
        "uz": [
            "Qattiq muddatli loyiha yoki topshiriqni qanday rejalashtirganingizni aniq misolda aytib bering. Muddatga ulgurdingizmi?",
            "Muddatni o'tkazib yuborgan yoki unga zo'rg'a ulgurgan holatingizni eslang. Sababi nima edi va keyin nimani o'zgartirdingiz?",
        ],
        "ru": [
            "На конкретном примере расскажите, как вы планировали проект или задание с жёстким сроком. Успели?",
            "Вспомните случай, когда вы сорвали срок или едва успели. В чём была причина и что вы потом изменили?",
        ],
        "en": [
            "Using a concrete example, how did you plan a project or assignment with a hard deadline? Did you make it?",
            "Recall a time you missed a deadline or barely made it. What caused it, and what did you change afterwards?",
        ],
    },
    "stress_handling": {
        "uz": [
            "Ishda yoki o'qishda kutilmaganda hammasi buzilib ketgan, bosim katta bo'lgan holatni aytib bering. O'zingizni qanday tutdingiz va nima qildingiz?",
            "Sizga keskin yoki adolatsiz tanqid qilingan holatni eslang. Qanday javob berdingiz?",
        ],
        "ru": [
            "Расскажите о ситуации, когда всё неожиданно пошло не так и давление было большим. Как вы себя вели и что сделали?",
            "Вспомните случай, когда вас резко или несправедливо раскритиковали. Как вы отреагировали?",
        ],
        "en": [
            "Tell me about a time things unexpectedly went wrong and the pressure was high. How did you handle yourself, and what did you do?",
            "Recall a time you received harsh or unfair criticism. How did you respond?",
        ],
    },
    "initiative": {
        "uz": [
            "Sizdan hech kim so'ramagan, lekin o'zingiz boshlab qilgan biror ishni aytib bering. Nimadan boshladingiz va natija nima bo'ldi?",
            "Biror jarayon noqulay yoki samarasiz ekanini sezgan holatni eslang. Uni yaxshilash uchun nima qildingiz?",
        ],
        "ru": [
            "Расскажите о деле, которое вас никто не просил делать, но вы начали сами. С чего начали и каким был результат?",
            "Вспомните, когда вы заметили, что какой-то процесс неудобен или неэффективен. Что вы сделали, чтобы его улучшить?",
        ],
        "en": [
            "Tell me about something nobody asked you to do, but you started on your own. How did you begin, and what was the result?",
            "Recall noticing that a process was awkward or inefficient. What did you do to improve it?",
        ],
    },
    "technical": {
        "uz": [
            "O'zingiz qilgan eng murakkab o'quv yoki shaxsiy loyihangizni aytib bering. Qaysi qismi qiyin bo'ldi va uni qanday hal qildingiz?",
            "Yangi vosita yoki texnologiyani qisqa vaqtda o'rganishga to'g'ri kelgan holatni aytib bering. Qanday o'rgandingiz?",
        ],
        "ru": [
            "Расскажите о самом сложном учебном или личном проекте. Какая часть далась труднее всего и как вы её решили?",
            "Расскажите о случае, когда пришлось быстро освоить новый инструмент или технологию. Как вы учились?",
        ],
        "en": [
            "Tell me about the most complex study or personal project you've done. Which part was hardest, and how did you solve it?",
            "Tell me about a time you had to learn a new tool or technology quickly. How did you go about it?",
        ],
    },
}

SITUATIONAL = {
    "IT": {
        "uz": "Ishga tushirilgandan bir soat o'tib mijozlar to'lov o'tmayapti deb yozishni boshladi. Siz navbatchisiz. Birinchi 30 daqiqada nima qilasiz?",
        "ru": "Через час после релиза клиенты начали писать, что платежи не проходят. Вы дежурный. Что вы делаете в первые 30 минут?",
        "en": "An hour after a release, customers start reporting that payments fail. You're on call. What do you do in the first 30 minutes?",
    },
    "Banking": {
        "uz": "Mijoz kredit arizasini topshirdi, lekin daromad hujjatlaridagi summa anketadagidan ancha kam. Qanday yo'l tutasiz?",
        "ru": "Клиент подал заявку на кредит, но доход в документах заметно меньше, чем в анкете. Как вы поступите?",
        "en": "A client applied for a loan, but the income in their documents is noticeably lower than on the form. How do you proceed?",
    },
    "Marketing": {
        "uz": "Reklama kampaniyasi ikki haftadan beri ishlayapti, ko'rishlar ko'p, lekin sotuv deyarli yo'q. Nimani tekshirasiz va nimani o'zgartirasiz?",
        "ru": "Рекламная кампания идёт две недели: просмотров много, а продаж почти нет. Что вы проверите и что измените?",
        "en": "An ad campaign has run for two weeks: lots of views, almost no sales. What do you check, and what do you change?",
    },
    "Data": {
        "uz": "Rahbar ertalabki hisobotdagi kunlik sotuv kechagidan 40% tushib ketganini ko'rib, sababini so'ramoqda. Qanday tekshirasiz?",
        "ru": "Руководитель видит в утреннем отчёте, что дневные продажи упали на 40%, и спрашивает почему. Как вы будете проверять?",
        "en": "Your manager sees a 40% drop in daily sales in the morning report and asks why. How do you investigate?",
    },
    "HR": {
        "uz": "Bo'lim rahbari bir hafta ichida uchta nomzod topishni so'radi, lekin vakansiyaga deyarli ariza kelmayapti. Nima qilasiz?",
        "ru": "Руководитель отдела просит найти трёх кандидатов за неделю, а откликов на вакансию почти нет. Что вы сделаете?",
        "en": "A department head wants three candidates within a week, but the vacancy gets almost no applications. What do you do?",
    },
}

GREETING = {
    "uz": "Assalomu alaykum! Men {company} kompaniyasining HR mutaxassisiman. Bugun «{position}» lavozimi bo'yicha qisqa suhbat o'tkazamiz: {total} ta savol. Javoblaringizda aniq misollar keltirsangiz yaxshi bo'ladi.",
    "ru": "Здравствуйте! Я HR-специалист компании {company}. Сегодня проведём короткое собеседование на позицию «{position}»: {total} вопросов. Старайтесь отвечать на конкретных примерах.",
    "en": "Hello! I'm an HR specialist at {company}. Today we'll have a short interview for the «{position}» role: {total} questions. Concrete examples in your answers will help a lot.",
}

CLOSING = {
    "uz": "Rahmat, savollarim shu edi. Javoblaringizni ko'rib chiqib, har biri bo'yicha fikr-mulohaza tayyorlayman.",
    "ru": "Спасибо, это все мои вопросы. Я посмотрю ваши ответы и подготовлю отзыв по каждому.",
    "en": "Thank you, those are all my questions. I'll review your answers and prepare feedback on each one.",
}


def fallback_questions(slots, *, sector: str, position: str, lang: str, seed: str) -> list[str]:
    """`slots` — `ai.interviewer.Slot` ro'yxati; har kompetensiya ichida savollar takrorlanmaydi."""
    rng = random.Random(seed)
    used: dict[str, list[str]] = {}
    out = []
    for slot in slots:
        if slot.kind == "intro":
            out.append(rng.choice(INTRO[lang]).format(position=position))
        elif slot.kind == "situational":
            out.append(SITUATIONAL[sector][lang])
        else:
            pool = used.setdefault(slot.competency, rng.sample(BEHAVIORAL[slot.competency][lang], 2))
            out.append(pool.pop(0) if pool else rng.choice(BEHAVIORAL[slot.competency][lang]))
    return out
