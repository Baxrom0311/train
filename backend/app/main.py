import pkgutil
import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import api
from app.config import settings

app = FastAPI(title="TryJob API")

# Aniq ro'yxatdagi originlar + credentials (cookie/Authorization header).
# "*" bilan allow_credentials=True birga ISHLATILMAYDI (xavfsizlik).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-router discovery: app/api/ papkasidagi barcha router'larni topib ulaydi.
#
# Qoida (barcha api/*.py lar uchun):
#   - Agar router.prefix allaqachon "/api/v1" bilan boshlansa -> prefix qo'shmasdan include.
#   - Aks holda -> "/api/v1" prefix bilan include.
#
# Bu ikki xil yozilgan router'larni (prefix bor/yo'q) bir xil natijaga keltiradi.

for module_info in pkgutil.iter_modules(api.__path__):
    module = importlib.import_module(f"app.api.{module_info.name}")
    for attr_name in ("router", "users_router"):
        r = getattr(module, attr_name, None)
        if r is None:
            continue
        if r.prefix.startswith("/api/v1"):
            app.include_router(r)
        else:
            app.include_router(r, prefix="/api/v1")
