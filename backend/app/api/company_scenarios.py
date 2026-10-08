"""
Kompaniya ssenariylari — CONTRACT.md §26 (Modul 9).

Kompaniya (`manage_company_scenarios` + tasdiqlangan kompaniya) §16 muharriri
bilan o'zining shaxsiy ssenariysini yaratadi va nashr qiladi. Ssenariy
katalogda ko'rinmaydi — faqat arizachiga sinov topshirig'i sifatida (§26.2).

Admin muharriri bilan bir xil amallar (`scenario_admin.py`), farqi:
egasi — kompaniya, `company_name` — kompaniya nomi, ko'pi bilan 5 kun va 20 ta ssenariy.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scenario_admin import (
    ActiveIn, DefinitionIn, FieldError, ScenarioAdminOut, ValidationOut, VersionOut, YamlIn, YamlOut, YamlText,
    create_owned, definition_yaml, draft_owned, list_owned, owned_version, parse_definition, parse_yaml_text,
    publish_owned, set_active_owned, to_yaml, validation, version_out,
)
from app.api.talent_hunt import company_of
from app.core.deps import require_permission
from app.database import get_db
from app.models.billing import Company
from app.models.scenario import Scenario
from app.models.user import User
from app.scenario.schema import ScenarioDefinition

router = APIRouter(prefix="/api/v1/company/scenarios", tags=["company-scenarios"])

MAX_DAYS = 5
MAX_SCENARIOS = 20


async def scenario_company(
    current_user: Annotated[User, Depends(require_permission("manage_company_scenarios"))],
    db: AsyncSession = Depends(get_db),
) -> Company:
    return await company_of(db, current_user)


Owner = Annotated[Company, Depends(scenario_company)]


def _own_name(definition: dict, company: Company) -> dict:
    """§26.1: ssenariydagi kompaniya — shu kompaniyaning o'zi (muharrirdagi qiymat e'tiborsiz)."""
    return {**definition, "company_name": company.name[:120]}


def _limits(defn: ScenarioDefinition) -> list[FieldError]:
    if defn.duration_days > MAX_DAYS:
        return [FieldError(path=["duration_days"], message=f"Kompaniya ssenariysi ko'pi bilan {MAX_DAYS} kunlik bo'ladi")]
    return []


def _check(defn: ScenarioDefinition) -> None:
    errors = _limits(defn)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": [e.model_dump() for e in errors]})


def _definition(body: DefinitionIn, company: Company) -> ScenarioDefinition:
    defn = parse_definition(_own_name(body.definition, company))
    _check(defn)
    return defn


@router.get("", response_model=list[ScenarioAdminOut])
async def list_company_scenarios(company: Owner, db: AsyncSession = Depends(get_db)):
    return await list_owned(db, company.id)


@router.post("/validate", response_model=ValidationOut)
async def validate(body: DefinitionIn, company: Owner):
    try:
        defn = ScenarioDefinition.model_validate(_own_name(body.definition, company))
    except ValidationError as exc:
        return validation(exc)
    return validation(defn, _limits(defn))


@router.post("/yaml", response_model=YamlOut)
async def parse_yaml(body: YamlIn, company: Owner):
    return parse_yaml_text(body.text)


@router.post("/to-yaml", response_model=YamlText)
async def definition_to_yaml(body: DefinitionIn, company: Owner):
    return definition_yaml(body.definition)


@router.post("", response_model=VersionOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(body: DefinitionIn, company: Owner, db: AsyncSession = Depends(get_db)):
    defn = _definition(body, company)
    # kompaniya qatori qulflanadi — parallel yaratishda ham limit buzilmaydi
    await db.execute(select(Company.id).where(Company.id == company.id).with_for_update())
    count = await db.scalar(select(func.count()).select_from(Scenario).where(Scenario.owner_company_id == company.id))
    if count >= MAX_SCENARIOS:
        raise HTTPException(status_code=409, detail=f"A company can have at most {MAX_SCENARIOS} scenarios")
    return await create_owned(db, defn, company.id)


@router.get("/{scenario_id}/versions/{number}", response_model=VersionOut)
async def get_version(scenario_id: uuid.UUID, number: int, company: Owner, db: AsyncSession = Depends(get_db)):
    return version_out(await owned_version(db, scenario_id, number, company.id))


@router.get("/{scenario_id}/versions/{number}/yaml")
async def export_yaml(scenario_id: uuid.UUID, number: int, company: Owner, db: AsyncSession = Depends(get_db)):
    v = await owned_version(db, scenario_id, number, company.id)
    defn = ScenarioDefinition.model_validate(v.definition)
    return Response(
        content=to_yaml(defn), media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{defn.slug}.yaml"'},
    )


@router.put("/{scenario_id}/draft", response_model=VersionOut)
async def put_draft(scenario_id: uuid.UUID, body: DefinitionIn, company: Owner, db: AsyncSession = Depends(get_db)):
    return await draft_owned(db, scenario_id, _definition(body, company), company.id)


@router.post("/{scenario_id}/versions/{number}/publish", response_model=VersionOut)
async def publish(scenario_id: uuid.UUID, number: int, company: Owner, db: AsyncSession = Depends(get_db)):
    return await publish_owned(db, scenario_id, number, company.id, check=_check)


@router.patch("/{scenario_id}", response_model=ScenarioAdminOut)
async def set_active(scenario_id: uuid.UUID, body: ActiveIn, company: Owner, db: AsyncSession = Depends(get_db)):
    return await set_active_owned(db, scenario_id, body.is_active, company.id)
