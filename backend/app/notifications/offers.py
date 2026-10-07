"""Talent Hunt takliflaridan bildirishnoma (CONTRACT.md §15.2). Chaqiruvchi commit qiladi."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OfferResponse, OrgType
from app.models.talent import TalentOffer
from app.models.user import User
from app.notifications.kinds import Kind
from app.notifications.service import notify


async def offer_received(db: AsyncSession, offer: TalentOffer, company_name: str, now: datetime) -> None:
    await notify(
        db, offer.candidate_user_id, Kind.OFFER_RECEIVED,
        {"offer_id": str(offer.id), "company": company_name, "position": offer.position_title},
        link="/offers", key=f"offer:{offer.id}", at=now,
    )


async def offer_responded(db: AsyncSession, offer: TalentOffer, candidate_name: str, now: datetime) -> None:
    """Kompaniyaning barcha faol xodimlariga — kim yuborgani saqlanmaydi (§10.2)."""
    staff = (await db.execute(
        select(User.id).where(
            User.org_type == OrgType.COMPANY, User.org_id == offer.company_id, User.is_active.is_(True),
        )
    )).scalars().all()
    params = {
        "offer_id": str(offer.id), "candidate": candidate_name, "position": offer.position_title,
        "accepted": offer.response == OfferResponse.ACCEPTED,
    }
    for user_id in staff:
        await notify(db, user_id, Kind.OFFER_RESPONDED, params, link="/talents/offers", key=f"offer:{offer.id}:response", at=now)
