import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

os.makedirs("/Users/baxrom/ish_full/train/frontend/public/assets", exist_ok=True)
ASSETS_DIR = "/Users/baxrom/ish_full/train/frontend/public/assets"

def get_font(size, bold=False):
    # Try system fonts on Mac
    font_paths = [
        "/System/Library/Fonts/SFProText-Bold.otf" if bold else "/System/Library/Fonts/SFProText-Regular.otf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_gradient_bg(width, height, color1, color2, angle=45):
    base = Image.new('RGBA', (width, height), color1)
    top = Image.new('RGBA', (width, height), color2)
    mask = Image.new('L', (width, height))
    draw = ImageDraw.Draw(mask)
    for y in range(height):
        for x in range(width):
            factor = (x / width * math.cos(math.radians(angle)) + y / height * math.sin(math.radians(angle)))
            factor = max(0, min(1, factor))
            mask.putpixel((x, y), int(255 * factor))
    return Image.composite(top, base, mask)

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

# 1. HERO 3D WORKSPACE PREVIEW
def generate_hero_workspace():
    w, h = 1200, 750
    img = create_gradient_bg(w, h, (10, 14, 26, 255), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    # Ambient glowing orbs
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((w - 500, -100, w + 100, 500), fill=(99, 102, 241, 45))
    glow_draw.ellipse((50, h - 350, 650, h + 250), fill=(16, 185, 129, 35))
    glow_draw.ellipse((w//2 - 200, h//2 - 200, w//2 + 200, h//2 + 200), fill=(59, 130, 246, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # Main Window (IDE & Simulation Suite)
    win_x1, win_y1, win_x2, win_y2 = 80, 70, w - 80, h - 70
    draw_rounded_rect(draw, (win_x1, win_y1, win_x2, win_y2), 24, fill=(15, 23, 42, 240), outline=(51, 65, 85, 255), width=2)
    
    # Window Header
    draw_rounded_rect(draw, (win_x1, win_y1, win_x2, win_y1 + 55), 24, fill=(30, 41, 59, 255))
    draw.rectangle((win_x1, win_y1 + 30, win_x2, win_y1 + 55), fill=(30, 41, 59, 255))
    
    # Window traffic lights
    draw.ellipse((win_x1 + 25, win_y1 + 20, win_x1 + 39, win_y1 + 34), fill=(239, 68, 68, 255))
    draw.ellipse((win_x1 + 47, win_y1 + 20, win_x1 + 61, win_y1 + 34), fill=(245, 158, 11, 255))
    draw.ellipse((win_x1 + 69, win_y1 + 20, win_x1 + 83, win_y1 + 34), fill=(16, 185, 129, 255))
    
    f_title = get_font(16, bold=True)
    f_code = get_font(15, bold=False)
    f_bold = get_font(15, bold=True)
    f_sm = get_font(13, bold=False)
    f_sm_bold = get_font(13, bold=True)

    draw.text((win_x1 + 110, win_y1 + 18), "TryJob Workspace — Uzum Bank: Fraud Detection Engine v2.4", fill=(226, 232, 240, 255), font=f_title)
    draw_rounded_rect(draw, (win_x2 - 190, win_y1 + 12, win_x2 - 20, win_y1 + 44), 8, fill=(16, 185, 129, 30), outline=(16, 185, 129, 120))
    draw.text((win_x2 - 175, win_y1 + 19), "● LIVE SIMULATION", fill=(52, 211, 153, 255), font=f_sm_bold)

    # Left Panel: Code & Task
    draw_rounded_rect(draw, (win_x1 + 20, win_y1 + 75, win_x1 + 620, win_y2 - 20), 16, fill=(10, 15, 30, 255), outline=(30, 41, 59, 255), width=1)
    
    # Code snippet lines
    code_lines = [
        ("import numpy as np", (148, 163, 184)),
        ("from uzum_security import TransactionRiskModel, AntiFraudAST", (148, 163, 184)),
        ("", (0,0,0)),
        ("def evaluate_transaction_risk(tx_stream: list) -> dict:", (56, 189, 248)),
        ("    # Anomaly detector on 240,000 live payments", (100, 116, 139)),
        ("    high_velocity = [t for t in tx_stream if t['velocity'] > 4.8]", (244, 114, 182)),
        ("    entropy_score = np.std([t['amount'] for t in tx_stream])", (250, 204, 21)),
        ("    ", (0,0,0)),
        ("    if entropy_score > 84.5 and len(high_velocity) >= 3:", (244, 114, 182)),
        ("        return {'verdict': 'BLOCKED_FRAUD', 'confidence': 0.994}", (52, 211, 153)),
        ("    return {'verdict': 'APPROVED', 'confidence': 0.981}", (52, 211, 153)),
        ("", (0,0,0)),
        ("# AST Sandbox Execution: PASSED [100% Accuracy]", (16, 185, 129))
    ]
    curr_y = win_y1 + 95
    for idx, (line, col) in enumerate(code_lines):
        draw.text((win_x1 + 40, curr_y), f"{idx+1:02d}", fill=(71, 85, 105), font=f_code)
        draw.text((win_x1 + 80, curr_y), line, fill=col, font=f_code)
        curr_y += 32

    # Right Panel Top: AI Mentor Review
    draw_rounded_rect(draw, (win_x1 + 645, win_y1 + 75, win_x2 - 20, win_y1 + 290), 16, fill=(30, 41, 59, 180), outline=(99, 102, 241, 100), width=1)
    draw_rounded_rect(draw, (win_x1 + 665, win_y1 + 95, win_x1 + 705, win_y1 + 135), 10, fill=(99, 102, 241, 255))
    draw.text((win_x1 + 673, win_y1 + 102), "AI", fill=(255, 255, 255), font=get_font(18, bold=True))
    draw.text((win_x1 + 720, win_y1 + 95), "AI Mentor & Lead Architect", fill=(241, 245, 249), font=f_bold)
    draw.text((win_x1 + 720, win_y1 + 118), "Kod analizi: 100/100 • O(N) Samaradorlik", fill=(52, 211, 153), font=f_sm)

    review_text = (
        "\"Ajoyib yechim! Vektorlashgan NumPy hisob-kitobi va\n"
        "AST xavfsizlik filtri orqali soxta tranzaksiyalar 12ms ichida\n"
        "aniqlandi. Ushbu natija Uzum Bank HR portaliga yuborildi!\""
    )
    draw.text((win_x1 + 665, win_y1 + 155), review_text, fill=(203, 213, 225), font=f_sm)

    # Metric badges inside review
    draw_rounded_rect(draw, (win_x1 + 665, win_y1 + 230, win_x1 + 780, win_y1 + 270), 8, fill=(15, 23, 42, 255), outline=(51, 65, 85, 255))
    draw.text((win_x1 + 678, win_y1 + 236), "Aniqlik", fill=(148, 163, 184), font=f_sm)
    draw.text((win_x1 + 678, win_y1 + 252), "99.4%", fill=(52, 211, 153), font=f_bold)

    draw_rounded_rect(draw, (win_x1 + 795, win_y1 + 230, win_x1 + 910, win_y1 + 270), 8, fill=(15, 23, 42, 255), outline=(51, 65, 85, 255))
    draw.text((win_x1 + 808, win_y1 + 236), "Kesh & Tezlik", fill=(148, 163, 184), font=f_sm)
    draw.text((win_x1 + 808, win_y1 + 252), "12 ms", fill=(56, 189, 248), font=f_bold)

    draw_rounded_rect(draw, (win_x1 + 925, win_y1 + 230, win_x2 - 35, win_y1 + 270), 8, fill=(15, 23, 42, 255), outline=(51, 65, 85, 255))
    draw.text((win_x1 + 938, win_y1 + 236), "ELO Reyting", fill=(148, 163, 184), font=f_sm)
    draw.text((win_x1 + 938, win_y1 + 252), "+145 pts", fill=(250, 204, 21), font=f_bold)

    # Right Panel Bottom: HR Offer Notification Card (Glassmorphic)
    draw_rounded_rect(draw, (win_x1 + 645, win_y1 + 310, win_x2 - 20, win_y2 - 20), 16, fill=(16, 185, 129, 25), outline=(16, 185, 129, 140), width=2)
    
    draw_rounded_rect(draw, (win_x1 + 665, win_y1 + 330, win_x1 + 715, win_y1 + 380), 12, fill=(16, 185, 129, 255))
    draw.text((win_x1 + 675, win_y1 + 342), "✓", fill=(255, 255, 255), font=get_font(24, bold=True))
    
    draw.text((win_x1 + 730, win_y1 + 330), "Yangi Ish Taklifi (Direct Offer)", fill=(52, 211, 153), font=get_font(17, bold=True))
    draw.text((win_x1 + 730, win_y1 + 355), "Uzum Bank Talent Acquisition jamoasidan", fill=(226, 232, 240), font=f_bold)

    offer_desc = (
        "Sizning simulyatsiyadagi algoritmingiz 99.4% natija ko'rsatdi.\n"
        "Rezyume so'ralmasdan to'g'ridan-to'g'ri 'Junior Fintech Engineer'\n"
        "lavozimiga suhbatga taklif qilindingiz!"
    )
    draw.text((win_x1 + 665, win_y1 + 395), offer_desc, fill=(203, 213, 225), font=f_sm)
    
    draw_rounded_rect(draw, (win_x1 + 665, win_y2 - 75, win_x2 - 40, win_y2 - 35), 10, fill=(16, 185, 129, 255))
    draw.text((win_x1 + 720, win_y2 - 63), "Taklifni Qabul Qilish & Sertifikatni Yuklash ➔", fill=(255, 255, 255), font=f_bold)

    img.save(os.path.join(ASSETS_DIR, "hero_3d_workspace.png"))
    print("Generated hero_3d_workspace.png")

# 2. PROBLEM VS SOLUTION CARDS
def generate_problem_visual():
    w, h = 600, 420
    img = create_gradient_bg(w, h, (30, 15, 20, 255), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    f_title = get_font(20, bold=True)
    f_bold = get_font(15, bold=True)
    f_sm = get_font(13, bold=False)

    # Header
    draw_rounded_rect(draw, (30, 30, 100, 60), 8, fill=(239, 68, 68, 40), outline=(239, 68, 68, 150))
    draw.text((42, 38), "ESKI YO'L", fill=(248, 113, 113), font=f_bold)
    draw.text((115, 36), "3 Yillik Tajriba To'sig'i (Tugallanmas Zanjir)", fill=(255, 255, 255), font=f_title)

    # Diagram nodes
    nodes = [
        ("4 Yillik Quruq Nazariya", "Universitetda faqat ma'ruza va kitoblar, real loyihalar yo'q", (71, 85, 105)),
        ("100+ Rezyume & CV Jo'natish", "HeadHunter, LinkedIn bo'yicha cheksiz bo'sh arizalar", (185, 28, 28)),
        ("«Tajribangiz Yo'q» Rad Javobi", "Ishga kirish uchun tajriba kerak, tajriba olish uchun esa ishga olishmaydi", (220, 38, 38))
    ]

    curr_y = 90
    for idx, (title, desc, color) in enumerate(nodes):
        draw_rounded_rect(draw, (30, curr_y, w - 30, curr_y + 80), 12, fill=(20, 24, 39, 255), outline=(60, 30, 40, 255), width=1)
        draw_rounded_rect(draw, (45, curr_y + 15, 85, curr_y + 55), 8, fill=color)
        draw.text((57, curr_y + 23), f"0{idx+1}", fill=(255, 255, 255), font=f_bold)
        draw.text((100, curr_y + 16), title, fill=(248, 113, 113), font=f_bold)
        draw.text((100, curr_y + 42), desc, fill=(148, 163, 184), font=f_sm)
        curr_y += 95

    # Bottom quote
    draw.text((45, curr_y + 15), "\"Tajriba bo'lmasa ish bermaymiz, ishlamasangiz qayerdan tajriba olasiz?\"", fill=(248, 113, 113), font=get_font(13, bold=True))

    img.save(os.path.join(ASSETS_DIR, "problem_barrier.png"))
    print("Generated problem_barrier.png")

def generate_solution_visual():
    w, h = 600, 420
    img = create_gradient_bg(w, h, (10, 35, 25, 255), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    f_title = get_font(20, bold=True)
    f_bold = get_font(15, bold=True)
    f_sm = get_font(13, bold=False)

    # Header
    draw_rounded_rect(draw, (30, 30, 110, 60), 8, fill=(16, 185, 129, 40), outline=(16, 185, 129, 150))
    draw.text((40, 38), "TRYJOB YO'LI", fill=(52, 211, 153), font=f_bold)
    draw.text((125, 36), "To'g'ridan-To'g'ri Natija & Kafolatlangan Ish", fill=(255, 255, 255), font=f_title)

    # Diagram nodes
    nodes = [
        ("Real Korporativ Keys & Vazifa", "Kapitalbank, Uzum, PwC kabi yetakchilarning haqiqiy muammolari", (16, 185, 129)),
        ("AI Mentor & AST Kod Baholash", "Real vaqt rejimida avtomatlashtirilgan mutaxassis tavsiyalari", (59, 130, 246)),
        ("QR Verifikatsiyalangan Sertifikat & Ish Taklifi", "HR portal orqali to'g'ridan-to'g'ri suhbat va rasmiy taklif", (245, 158, 11))
    ]

    curr_y = 90
    for idx, (title, desc, color) in enumerate(nodes):
        draw_rounded_rect(draw, (30, curr_y, w - 30, curr_y + 80), 12, fill=(20, 30, 45, 255), outline=(16, 185, 129, 80), width=1)
        draw_rounded_rect(draw, (45, curr_y + 15, 85, curr_y + 55), 8, fill=color)
        draw.text((57, curr_y + 23), f"0{idx+1}", fill=(255, 255, 255), font=f_bold)
        draw.text((100, curr_y + 16), title, fill=(52, 211, 153), font=f_bold)
        draw.text((100, curr_y + 42), desc, fill=(203, 213, 225), font=f_sm)
        curr_y += 95

    draw.text((45, curr_y + 15), "5 Soatlik Simulyatsiya = 6 Oylik Ish Tajribasi va Tasdiqlangan Natija", fill=(52, 211, 153), font=get_font(13, bold=True))

    img.save(os.path.join(ASSETS_DIR, "solution_tryjob.png"))
    print("Generated solution_tryjob.png")

# 3. VERIFIED GOLD CERTIFICATE PREVIEW
def generate_gold_certificate():
    w, h = 900, 600
    img = create_gradient_bg(w, h, (15, 23, 42, 255), (10, 15, 30, 255))
    draw = ImageDraw.Draw(img)

    # Golden border frame
    draw_rounded_rect(draw, (30, 30, w - 30, h - 30), 20, fill=(15, 20, 35, 255), outline=(217, 119, 6, 255), width=3)
    draw_rounded_rect(draw, (40, 40, w - 40, h - 40), 16, outline=(251, 191, 36, 160), width=1)

    # Glowing seal
    f_brand = get_font(28, bold=True)
    f_sub = get_font(14, bold=False)
    f_cert = get_font(32, bold=True)
    f_name = get_font(34, bold=True)
    f_body = get_font(15, bold=False)
    f_bold = get_font(15, bold=True)

    draw.text((70, 60), "TryJob", fill=(255, 255, 255), font=f_brand)
    draw.text((165, 60), "ACADEMY & HR VERIFIED", fill=(251, 191, 36), font=get_font(14, bold=True))

    draw.text((w // 2 - 220, 130), "SERTIFIKAT", fill=(251, 191, 36), font=f_cert)
    draw.text((w // 2 - 190, 180), "Ushbu hujjat tasdiqlaydiki,", fill=(148, 163, 184), font=f_sub)

    # Student name
    draw.text((w // 2 - 160, 215), "BAXROM ALIYEV", fill=(255, 255, 255), font=f_name)
    
    # Description
    desc = (
        "JPMorgan Chase & Uzum Bank hamkorligidagi 'Software Engineering & Quantitative Risk'\n"
        "kasbiy simulyatsiyasini 100/100 ball bilan muvaffaqiyatli tamomladi."
    )
    draw.text((w // 2 - 320, 280), desc, fill=(203, 213, 225), font=f_body)

    # QR Code placeholder box
    qr_x, qr_y = 70, h - 170
    draw_rounded_rect(draw, (qr_x, qr_y, qr_x + 90, qr_y + 90), 8, fill=(255, 255, 255))
    draw_rounded_rect(draw, (qr_x + 10, qr_y + 10, qr_x + 35, qr_y + 35), 4, fill=(0, 0, 0))
    draw_rounded_rect(draw, (qr_x + 55, qr_y + 10, qr_x + 80, qr_y + 35), 4, fill=(0, 0, 0))
    draw_rounded_rect(draw, (qr_x + 10, qr_y + 55, qr_x + 35, qr_y + 80), 4, fill=(0, 0, 0))
    draw.rectangle((qr_x + 45, qr_y + 45, qr_x + 65, qr_y + 65), fill=(0, 0, 0))

    draw.text((qr_x + 105, qr_y + 15), "Ommaviy QR Verifikatsiya", fill=(255, 255, 255), font=f_bold)
    draw.text((qr_x + 105, qr_y + 38), "ID: TJ-2026-9842-UZB", fill=(251, 191, 36), font=f_sub)
    draw.text((qr_x + 105, qr_y + 58), "HMAC-SHA256 Raqamli Imzo", fill=(148, 163, 184), font=f_sub)

    # Golden Stamp / Badge on the right
    seal_x, seal_y = w - 180, h - 150
    draw.ellipse((seal_x - 45, seal_y - 45, seal_x + 45, seal_y + 45), fill=(217, 119, 6, 255), outline=(251, 191, 36, 255), width=3)
    draw.text((seal_x - 30, seal_y - 20), "OFFICIAL\n  VERIFIED", fill=(255, 255, 255), font=get_font(11, bold=True))

    img.save(os.path.join(ASSETS_DIR, "certificate_gold_preview.png"))
    print("Generated certificate_gold_preview.png")

# 4. CASE CUP TROPHY & BANNER
def generate_case_cup_visual():
    w, h = 800, 480
    img = create_gradient_bg(w, h, (40, 25, 10, 255), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)

    f_badge = get_font(13, bold=True)
    f_h1 = get_font(28, bold=True)
    f_sub = get_font(15, bold=False)
    f_bold = get_font(16, bold=True)

    draw_rounded_rect(draw, (40, 40, 220, 70), 8, fill=(245, 158, 11, 40), outline=(245, 158, 11, 180))
    draw.text((55, 48), "🏆 MILLIY CHEMPIONAT", fill=(251, 191, 36), font=f_badge)

    draw.text((40, 85), "TryJob Milliy Case Cup 2026", fill=(255, 255, 255), font=f_h1)
    draw.text((40, 130), "O'zbekistonning eng iqtidorli talabalari va jamoalari uchun real biznes keyslar musobaqasi", fill=(203, 213, 225), font=f_sub)

    # Prize cards
    prizes = [
        ("1-O'rin", "50,000,000 UZS", "Kapitalbank Head Office'da Fast-Track Ish", (251, 191, 36)),
        ("2-O'rin", "30,000,000 UZS", "Uzum Fintech Amaliyot & Mac Studio", (203, 213, 225)),
        ("3-O'rin", "15,000,000 UZS", "PwC Consulting Mentorlik Dasturi", (205, 127, 50))
    ]

    curr_x = 40
    for title, reward, note, col in prizes:
        draw_rounded_rect(draw, (curr_x, 180, curr_x + 225, 360), 16, fill=(20, 26, 40, 255), outline=col, width=2)
        draw_rounded_rect(draw, (curr_x + 15, 195, curr_x + 95, 225), 6, fill=col)
        draw.text((curr_x + 25, 202), title, fill=(0, 0, 0), font=f_badge)
        
        draw.text((curr_x + 15, 245), reward, fill=(255, 255, 255), font=f_bold)
        draw.text((curr_x + 15, 280), note, fill=(148, 163, 184), font=get_font(12, bold=False))
        curr_x += 245

    # Bottom CTA
    draw_rounded_rect(draw, (40, 390, w - 40, 440), 10, fill=(245, 158, 11, 255))
    draw.text((w // 2 - 120, 405), "Ro'yxatdan O'tish va Ishtirok Etish ➔", fill=(0, 0, 0), font=f_bold)

    img.save(os.path.join(ASSETS_DIR, "case_cup_banner.png"))
    print("Generated case_cup_banner.png")

# 5. TALENT HUNT RECRUITER RADAR
def generate_talent_hunt_visual():
    w, h = 800, 480
    img = create_gradient_bg(w, h, (10, 20, 45, 255), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)

    f_badge = get_font(13, bold=True)
    f_h1 = get_font(26, bold=True)
    f_bold = get_font(15, bold=True)
    f_sm = get_font(13, bold=False)

    draw_rounded_rect(draw, (40, 40, 180, 70), 8, fill=(99, 102, 241, 40), outline=(99, 102, 241, 180))
    draw.text((55, 48), "🎯 AI TALENT RADAR", fill=(129, 140, 248), font=f_badge)

    draw.text((40, 85), "HR & Ish Beruvchilar Uchun Iqtidorlar Bazasi", fill=(255, 255, 255), font=f_h1)

    # Candidate Profiles Mockup
    candidates = [
        ("Azizbek R.", "Toshkent Axborot Texnologiyalari Universiteti", "Python, FastAPI, Docker, SQL", "98.8%", "1,850 ELO"),
        ("Madina T.", "Westminster Xalqaro Universiteti (WIUT)", "IFRS 16, Moliya Tahlili, Audit", "97.2%", "1,790 ELO"),
        ("Jasur K.", "Inha Universiteti Toshkent", "React, TypeScript, Redux, UI/UX", "96.5%", "1,740 ELO")
    ]

    curr_y = 135
    for name, uni, skills, score, elo in candidates:
        draw_rounded_rect(draw, (40, curr_y, w - 40, curr_y + 85), 12, fill=(20, 28, 48, 255), outline=(51, 65, 85, 255), width=1)
        
        # Avatar circle
        draw.ellipse((55, curr_y + 15, 105, curr_y + 65), fill=(99, 102, 241, 255))
        draw.text((70, curr_y + 25), name[:2], fill=(255, 255, 255), font=f_bold)
        
        draw.text((120, curr_y + 15), name, fill=(255, 255, 255), font=f_bold)
        draw.text((120, curr_y + 38), uni, fill=(148, 163, 184), font=f_sm)
        draw.text((120, curr_y + 58), f"Ko'nikmalar: {skills}", fill=(56, 189, 248), font=get_font(12, bold=False))

        # Right stats
        draw_rounded_rect(draw, (w - 230, curr_y + 20, w - 140, curr_y + 65), 8, fill=(16, 185, 129, 30), outline=(16, 185, 129, 120))
        draw.text((w - 215, curr_y + 26), "Match", fill=(148, 163, 184), font=get_font(11, bold=False))
        draw.text((w - 215, curr_y + 40), score, fill=(52, 211, 153), font=f_bold)

        draw_rounded_rect(draw, (w - 125, curr_y + 20, w - 55, curr_y + 65), 8, fill=(99, 102, 241, 255))
        draw.text((w - 112, curr_y + 32), "Offer ➔", fill=(255, 255, 255), font=f_bold)

        curr_y += 100

    img.save(os.path.join(ASSETS_DIR, "talent_hunt_radar.png"))
    print("Generated talent_hunt_radar.png")

# Run all generators
if __name__ == '__main__':
    generate_hero_workspace()
    generate_problem_visual()
    generate_solution_visual()
    generate_gold_certificate()
    generate_case_cup_visual()
    generate_talent_hunt_visual()
    print("All rich PNG visual assets successfully generated!")
