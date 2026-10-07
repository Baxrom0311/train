"""
Tekshirilgan ssenariyni DB'ga yozish (CONTRACT.md §9.3.1).

- `scenarios` — slug bo'yicha topiladi yoki yaratiladi, katalog maydonlari
  oxirgi import bilan yangilanadi.
- `scenario_versions` — har import yangi `draft` versiya. Oxirgi versiya
  bilan bir xil ta'rif qayta import qilinsa, yangi versiya ochilmaydi.
- `save_draft` — muharrir (§16.1): oxirgi versiya `draft` bo'lsa o'sha
  joyida yangilanadi, aks holda `import_scenario` kabi yangi qoralama.
- `publish_version` — versiyani o'zgarmas qiladi; avvalgi `published`
  versiyalar `archived` bo'ladi (ularga bog'langan Run'lar ishlashda davom etadi).

Hujjatlar shu yerda bo'laklanadi (`rag.build_chunks`); embedding'lar fon
job'ida to'ldiriladi (`rag.embed_pending_chunks`), import tashqi API'ga bog'liq emas.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScenarioVersionStatus
from app.models.scenario import Scenario, ScenarioDocument, ScenarioVersion
from app.scenario.rag import build_chunks
from app.scenario.engine import forget_definition
from app.scenario.schema import ScenarioDefinition


def dump_definition(defn: ScenarioDefinition) -> dict:
    """JSONB uchun: `from` kaliti YAML'dagidek saqlanadi."""
    return defn.model_dump(mode="json", by_alias=True)


async def import_scenario(
    db: AsyncSession, defn: ScenarioDefinition, *, update_catalog: bool = True,
) -> tuple[ScenarioVersion, bool]:
    """`(versiya, yangi_yaratildimi)` qaytaradi. Commit chaqiruvchida."""
    definition = dump_definition(defn)

    scenario = (await db.execute(select(Scenario).where(Scenario.slug == defn.slug))).scalars().first()
    if scenario is None:
        scenario = Scenario(slug=defn.slug)
        db.add(scenario)
        update_catalog = True   # yangi qator — maydonlar baribir kerak
    if update_catalog:
        _update_catalog(scenario, defn)
    await db.flush()

    latest = (
        await db.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.scenario_id == scenario.id)
            .order_by(ScenarioVersion.version.desc())
            .limit(1)
        )
    ).scalars().first()
    if latest is not None and latest.definition == definition:
        return latest, False

    version = ScenarioVersion(
        scenario_id=scenario.id,
        version=(latest.version + 1) if latest else 1,
        status=ScenarioVersionStatus.DRAFT,
        definition=definition,
    )
    db.add(version)
    await db.flush()
    await _write_documents(db, version, defn)
    return version, True


async def save_draft(db: AsyncSession, defn: ScenarioDefinition) -> ScenarioVersion:
    """
    Muharrirdan saqlash (§16.1). Commit chaqiruvchida. Katalog maydonlari
    (sarlavha, soha...) qoralamada emas, nashrda yangilanadi.
    """
    scenario = (await db.execute(select(Scenario).where(Scenario.slug == defn.slug))).scalars().first()
    latest = None
    if scenario is not None:
        latest = (await db.execute(
            select(ScenarioVersion).where(ScenarioVersion.scenario_id == scenario.id)
            .order_by(ScenarioVersion.version.desc()).limit(1).with_for_update()
        )).scalars().first()
    if latest is None or latest.status != ScenarioVersionStatus.DRAFT:
        version, _ = await import_scenario(db, defn, update_catalog=False)
        return version

    definition = dump_definition(defn)
    if latest.definition != definition:
        latest.definition = definition
        latest.created_at = datetime.now(timezone.utc)
        forget_definition(latest.id)
        # bo'laklar hujjat bilan birga o'chadi (ON DELETE CASCADE)
        await db.execute(delete(ScenarioDocument).where(ScenarioDocument.scenario_version_id == latest.id))
        await db.flush()
        await _write_documents(db, latest, defn)
    return latest


def _update_catalog(scenario: Scenario, defn: ScenarioDefinition) -> None:
    scenario.title = defn.title
    scenario.sector = defn.sector
    scenario.company_name = defn.company_name
    scenario.difficulty = defn.difficulty
    scenario.duration_days = defn.duration_days


async def _write_documents(db: AsyncSession, version: ScenarioVersion, defn: ScenarioDefinition) -> None:
    for doc in defn.documents:
        db.add(ScenarioDocument(
            scenario_version_id=version.id,
            key=doc.key,
            title=doc.title,
            content=doc.content,
            visible_to_personas=[p.key for p in defn.personas if doc.key in p.knows],
        ))
    await db.flush()
    await build_chunks(db, version.id)


async def publish_version(db: AsyncSession, version: ScenarioVersion) -> None:
    """Commit chaqiruvchida."""
    if version.status == ScenarioVersionStatus.PUBLISHED:
        return
    if version.status == ScenarioVersionStatus.ARCHIVED:
        raise ValueError("arxivlangan versiyani qayta e'lon qilib bo'lmaydi — yangi versiya import qiling")
    previous = (
        await db.execute(
            select(ScenarioVersion).where(
                ScenarioVersion.scenario_id == version.scenario_id,
                ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED,
            )
        )
    ).scalars().all()
    for old in previous:
        old.status = ScenarioVersionStatus.ARCHIVED
    version.status = ScenarioVersionStatus.PUBLISHED
    version.published_at = datetime.now(timezone.utc)
    # katalog nashr qilingan ta'rifni ko'rsatadi (qoralama sarlavhasini emas)
    scenario = await db.get(Scenario, version.scenario_id)
    _update_catalog(scenario, ScenarioDefinition.model_validate(version.definition))
    await db.flush()
