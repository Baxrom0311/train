"""
Ssenariy muharriri API (CONTRACT.md §16, Modul 9) — `manage_simulations`.

Ta'rif har doim §9.3 sxemasi bilan tekshiriladi; xatolar `{path, message}`
ko'rinishida qaytadi, muharrir ularni tegishli maydonga bog'laydi.
Versiyalash `scenario/importer.py`da (§16.1).

Admin faqat platforma ssenariylarini ko'radi; kompaniya ssenariylari (§26)
shu yordamchilar bilan `api/company_scenarios.py`da, egasi bo'yicha ajratilgan.
"""
import uuid
from datetime import datetime
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.database import get_db
from app.models.enums import NodeType, ScenarioVersionStatus, Sector
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.user import User
from app.scenario.importer import publish_version, save_draft
from app.scenario.schema import ScenarioDefinition, scenario_warnings

router = APIRouter(prefix="/api/v1/admin/scenarios", tags=["scenario-admin"])

Admin = Annotated[User, Depends(require_permission("manage_simulations"))]
YAML_MAX = 500_000   # ~ eng katta haftalik ssenariydan 10 barobar ko'p


class VersionInfo(BaseModel):
    version: int
    status: ScenarioVersionStatus
    created_at: datetime
    published_at: datetime | None


class ScenarioAdminOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    sector: Sector
    company_name: str
    duration_days: int
    is_active: bool
    runs: int
    versions: list[VersionInfo]


class FieldError(BaseModel):
    path: list[str | int]
    message: str


class Summary(BaseModel):
    days: int
    nodes: int
    graded: int
    personas: int
    documents: int
    mentor: bool


class ValidationOut(BaseModel):
    ok: bool
    errors: list[FieldError]
    warnings: list[str]
    summary: Summary | None


class DefinitionIn(BaseModel):
    definition: dict[str, Any]


class VersionOut(VersionInfo):
    scenario_id: uuid.UUID
    definition: dict[str, Any]
    warnings: list[str]


class YamlIn(BaseModel):
    text: str = Field(max_length=YAML_MAX)


class YamlOut(BaseModel):
    definition: dict[str, Any] | None
    errors: list[FieldError]


class YamlText(BaseModel):
    text: str


class ActiveIn(BaseModel):
    is_active: bool


# ── Yordamchilar ────────────────────────────────────────────────────


def _errors(exc: ValidationError) -> list[FieldError]:
    out = []
    for e in exc.errors():
        message = e["msg"].removeprefix("Value error, ")
        out.append(FieldError(path=list(e["loc"]), message=message))
    return out


def parse_definition(definition: dict) -> ScenarioDefinition:
    try:
        return ScenarioDefinition.model_validate(definition)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"errors": [e.model_dump() for e in _errors(exc)]},
        ) from exc


def _summary(defn: ScenarioDefinition) -> Summary:
    return Summary(
        days=defn.duration_days,
        nodes=len(defn.nodes),
        graded=sum(n.is_graded and n.type != NodeType.DAY_END for n in defn.nodes),
        personas=len(defn.personas),
        documents=len(defn.documents),
        mentor=defn.mentor is not None,
    )


def _info(v: ScenarioVersion) -> VersionInfo:
    return VersionInfo(version=v.version, status=v.status, created_at=v.created_at, published_at=v.published_at)


def version_out(v: ScenarioVersion) -> VersionOut:
    defn = ScenarioDefinition.model_validate(v.definition)
    return VersionOut(**_info(v).model_dump(), scenario_id=v.scenario_id, definition=v.definition,
                      warnings=scenario_warnings(defn))


async def owned_scenario(db: AsyncSession, scenario_id: uuid.UUID, owner: uuid.UUID | None) -> Scenario:
    """Egasi mos kelmasa — "yo'q" (admin kompaniya ssenariysini, kompaniya boshqasinikini ko'rmaydi)."""
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None or scenario.owner_company_id != owner:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


async def owned_version(db: AsyncSession, scenario_id: uuid.UUID, number: int, owner: uuid.UUID | None) -> ScenarioVersion:
    await owned_scenario(db, scenario_id, owner)
    v = (await db.execute(
        select(ScenarioVersion).where(ScenarioVersion.scenario_id == scenario_id, ScenarioVersion.version == number)
    )).scalars().first()
    if v is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return v


class _BlockDumper(yaml.SafeDumper):
    """Ko'p qatorli matn `|` bloki bo'lib yoziladi — qo'lda tahrirlashga qulay."""


def _str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_BlockDumper.add_representer(str, _str)


def to_yaml(defn: ScenarioDefinition) -> str:
    # default qiymatlar yozilmaydi — fayl `content/`dagilar kabi ixcham
    data = defn.model_dump(mode="json", by_alias=True, exclude_defaults=True)
    return yaml.dump(data, Dumper=_BlockDumper, allow_unicode=True, sort_keys=False, width=100)


# ── Umumiy amallar (admin va kompaniya, §26.4) ──────────────────────


async def list_owned(db: AsyncSession, owner: uuid.UUID | None) -> list[ScenarioAdminOut]:
    scenarios = (await db.execute(
        select(Scenario).where(
            Scenario.owner_company_id.is_(None) if owner is None else Scenario.owner_company_id == owner,
        ).order_by(Scenario.title)
    )).scalars().all()
    ids = [s.id for s in scenarios]
    versions = (await db.execute(
        select(ScenarioVersion).where(ScenarioVersion.scenario_id.in_(ids)).order_by(ScenarioVersion.version.desc())
    )).scalars().all()
    runs = dict((await db.execute(
        select(ScenarioVersion.scenario_id, func.count(Run.id))
        .join(Run, Run.scenario_version_id == ScenarioVersion.id)
        .where(ScenarioVersion.scenario_id.in_(ids))
        .group_by(ScenarioVersion.scenario_id)
    )).all())
    by_scenario: dict[uuid.UUID, list[VersionInfo]] = {}
    for v in versions:
        by_scenario.setdefault(v.scenario_id, []).append(_info(v))
    return [
        ScenarioAdminOut(
            id=s.id, slug=s.slug, title=s.title, sector=s.sector, company_name=s.company_name,
            duration_days=s.duration_days, is_active=s.is_active, runs=runs.get(s.id, 0),
            versions=by_scenario.get(s.id, []),
        )
        for s in scenarios
    ]


def validation(defn_or_exc: ScenarioDefinition | ValidationError, extra: list[FieldError] = ()) -> ValidationOut:
    if isinstance(defn_or_exc, ValidationError):
        return ValidationOut(ok=False, errors=[*_errors(defn_or_exc), *extra], warnings=[], summary=None)
    if extra:
        return ValidationOut(ok=False, errors=list(extra), warnings=scenario_warnings(defn_or_exc),
                             summary=_summary(defn_or_exc))
    return ValidationOut(ok=True, errors=[], warnings=scenario_warnings(defn_or_exc), summary=_summary(defn_or_exc))


def parse_yaml_text(text: str) -> YamlOut:
    """YAML → ta'rif. Sxema xatolari bo'lsa ham (muharrirda tuzatish uchun) ta'rif qaytadi."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" ({mark.line + 1}-qator)" if mark else ""
        return YamlOut(definition=None, errors=[FieldError(path=[], message=f"YAML o'qilmadi{where}: {getattr(exc, 'problem', exc)}")])
    if not isinstance(data, dict):
        return YamlOut(definition=None, errors=[FieldError(path=[], message="YAML ildizi obyekt (kalit: qiymat) bo'lishi kerak")])
    try:
        defn = ScenarioDefinition.model_validate(data)
    except ValidationError as exc:
        return YamlOut(definition=data, errors=_errors(exc))
    # to'liq shakl (default'lar bilan) — muharrir formasi barcha maydonlarni ko'radi
    return YamlOut(definition=defn.model_dump(mode="json", by_alias=True), errors=[])


def definition_yaml(definition: dict[str, Any]) -> YamlText:
    """Muharrir holati → YAML (saqlanmagan bo'lsa ham). Noto'g'ri ta'rif — xom holicha, tuzatish uchun."""
    try:
        return YamlText(text=to_yaml(ScenarioDefinition.model_validate(definition)))
    except ValidationError:
        return YamlText(text=yaml.dump(definition, Dumper=_BlockDumper, allow_unicode=True, sort_keys=False, width=100))


async def create_owned(db: AsyncSession, defn: ScenarioDefinition, owner: uuid.UUID | None) -> VersionOut:
    if await db.scalar(select(Scenario.id).where(Scenario.slug == defn.slug)):
        raise HTTPException(status_code=409, detail="Slug already taken")
    version = await save_draft(db, defn, owner_company_id=owner)
    await db.commit()
    return version_out(version)


async def draft_owned(db: AsyncSession, scenario_id: uuid.UUID, defn: ScenarioDefinition, owner: uuid.UUID | None) -> VersionOut:
    scenario = await owned_scenario(db, scenario_id, owner)
    if defn.slug != scenario.slug:
        raise HTTPException(status_code=422, detail={"errors": [
            FieldError(path=["slug"], message="Mavjud ssenariyning slug'i o'zgarmaydi").model_dump()]})
    version = await save_draft(db, defn, owner_company_id=owner)
    await db.commit()
    return version_out(version)


async def publish_owned(db: AsyncSession, scenario_id: uuid.UUID, number: int, owner: uuid.UUID | None,
                        check=lambda defn: None) -> VersionOut:
    v = await owned_version(db, scenario_id, number, owner)
    if v.status == ScenarioVersionStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived version cannot be published again")
    check(parse_definition(v.definition))   # eski sxema bilan saqlangan bo'lsa — 422, nashr qilinmaydi
    await publish_version(db, v)
    await db.commit()
    return version_out(v)


async def set_active_owned(db: AsyncSession, scenario_id: uuid.UUID, is_active: bool, owner: uuid.UUID | None) -> ScenarioAdminOut:
    scenario = await owned_scenario(db, scenario_id, owner)
    scenario.is_active = is_active
    await db.commit()
    return next(s for s in await list_owned(db, owner) if s.id == scenario_id)


# ── Endpointlar ─────────────────────────────────────────────────────


@router.get("", response_model=list[ScenarioAdminOut])
async def list_scenarios(admin: Admin, db: AsyncSession = Depends(get_db)):
    return await list_owned(db, None)


@router.post("/validate", response_model=ValidationOut)
async def validate(body: DefinitionIn, admin: Admin):
    try:
        return validation(ScenarioDefinition.model_validate(body.definition))
    except ValidationError as exc:
        return validation(exc)


@router.post("/yaml", response_model=YamlOut)
async def parse_yaml(body: YamlIn, admin: Admin):
    return parse_yaml_text(body.text)


@router.post("/to-yaml", response_model=YamlText)
async def definition_to_yaml(body: DefinitionIn, admin: Admin):
    return definition_yaml(body.definition)


@router.post("", response_model=VersionOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(body: DefinitionIn, admin: Admin, db: AsyncSession = Depends(get_db)):
    return await create_owned(db, parse_definition(body.definition), None)


@router.get("/{scenario_id}/versions/{number}", response_model=VersionOut)
async def get_version(scenario_id: uuid.UUID, number: int, admin: Admin, db: AsyncSession = Depends(get_db)):
    return version_out(await owned_version(db, scenario_id, number, None))


@router.get("/{scenario_id}/versions/{number}/yaml")
async def export_yaml(scenario_id: uuid.UUID, number: int, admin: Admin, db: AsyncSession = Depends(get_db)):
    v = await owned_version(db, scenario_id, number, None)
    defn = ScenarioDefinition.model_validate(v.definition)
    return Response(
        content=to_yaml(defn), media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{defn.slug}.yaml"'},
    )


@router.put("/{scenario_id}/draft", response_model=VersionOut)
async def put_draft(scenario_id: uuid.UUID, body: DefinitionIn, admin: Admin, db: AsyncSession = Depends(get_db)):
    return await draft_owned(db, scenario_id, parse_definition(body.definition), None)


@router.post("/{scenario_id}/versions/{number}/publish", response_model=VersionOut)
async def publish(scenario_id: uuid.UUID, number: int, admin: Admin, db: AsyncSession = Depends(get_db)):
    return await publish_owned(db, scenario_id, number, None)


@router.patch("/{scenario_id}", response_model=ScenarioAdminOut)
async def set_active(scenario_id: uuid.UUID, body: ActiveIn, admin: Admin, db: AsyncSession = Depends(get_db)):
    return await set_active_owned(db, scenario_id, body.is_active, None)
