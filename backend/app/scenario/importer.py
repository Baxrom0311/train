"""
Tekshirilgan ssenariyni DB'ga yozish (CONTRACT.md §9.3.1).

- `scenarios` — slug bo'yicha topiladi yoki yaratiladi, katalog maydonlari
  oxirgi import bilan yangilanadi.
- `scenario_versions` — har import yangi `draft` versiya. Oxirgi versiya
  bilan bir xil ta'rif qayta import qilinsa, yangi versiya ochilmaydi.
- `publish_version` — versiyani o'zgarmas qiladi; avvalgi `published`
  versiyalar `archived` bo'ladi (ularga bog'langan Run'lar ishlashda davom etadi).

Hujjatlar shu yerda bo'laklanadi (`rag.build_chunks`); embedding'lar fon
job'ida to'ldiriladi (`rag.embed_pending_chunks`), import tashqi API'ga bog'liq emas.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScenarioVersionStatus
from app.models.scenario import Scenario, ScenarioDocument, ScenarioVersion
from app.scenario.rag import build_chunks
from app.scenario.schema import ScenarioDefinition


def dump_definition(defn: ScenarioDefinition) -> dict:
    """JSONB uchun: `from` kaliti YAML'dagidek saqlanadi."""
    return defn.model_dump(mode="json", by_alias=True)


async def import_scenario(db: AsyncSession, defn: ScenarioDefinition) -> tuple[ScenarioVersion, bool]:
    """`(versiya, yangi_yaratildimi)` qaytaradi. Commit chaqiruvchida."""
    definition = dump_definition(defn)

    scenario = (await db.execute(select(Scenario).where(Scenario.slug == defn.slug))).scalars().first()
    if scenario is None:
        scenario = Scenario(slug=defn.slug)
        db.add(scenario)
    scenario.title = defn.title
    scenario.sector = defn.sector
    scenario.company_name = defn.company_name
    scenario.difficulty = defn.difficulty
    scenario.duration_days = defn.duration_days
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
    return version, True


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
    await db.flush()
