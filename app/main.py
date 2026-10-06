import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, get_db
from app.seed_data import seed_database
from app.api import (
    auth,
    simulations,
    submissions,
    certificates,
    tools,
    case_cups,
    talent_hunt,
    university_portal,
    billing
)
from app.models import Simulation, Certificate

# Bazani yaratish va boshlang'ich ma'lumotlarni yuklash (SQLite lokal/test muhiti uchun)
if "sqlite" in str(engine.url):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_database(db)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="O'zbekiston talabalari uchun amaliy ish simulyatsiyalari, Case Cup milliy chempionatlari va AI Talent Hunt platformasi"
)

# CORS sozlamalari (Production xavfsizlik standarti)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Papkalar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ── API Routerlarini ulash ──────────────────────────────────────────────────
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(simulations.router, prefix=settings.API_V1_STR)
app.include_router(submissions.router, prefix=settings.API_V1_STR)
app.include_router(certificates.router, prefix=settings.API_V1_STR)
app.include_router(tools.router, prefix=settings.API_V1_STR)
app.include_router(case_cups.router, prefix=settings.API_V1_STR)
app.include_router(talent_hunt.router, prefix=settings.API_V1_STR)
app.include_router(university_portal.router, prefix=settings.API_V1_STR)
app.include_router(billing.router, prefix=settings.API_V1_STR)

# ── Web UI Frontend Sahifalari ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, db: Session = Depends(get_db)):
    sims = db.query(Simulation).filter(Simulation.is_published == True).all()
    return templates.TemplateResponse(request=request, name="index.html", context={"simulations": sims})

@app.get("/simulations", response_class=HTMLResponse)
async def simulations_page(request: Request, db: Session = Depends(get_db)):
    sims = db.query(Simulation).filter(Simulation.is_published == True).all()
    return templates.TemplateResponse(request=request, name="simulations.html", context={"simulations": sims})

@app.get("/simulations/{slug}/workspace", response_class=HTMLResponse)
async def workspace_page(request: Request, slug: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    return templates.TemplateResponse(request=request, name="workspace.html", context={"simulation": sim})

@app.get("/verify/{cert_uuid}", response_class=HTMLResponse)
async def verify_page(request: Request, cert_uuid: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.cert_uuid == cert_uuid).first()
    return templates.TemplateResponse(request=request, name="verify.html", context={"cert_uuid": cert_uuid, "cert": cert})

@app.get("/api/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}
