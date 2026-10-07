#!/usr/bin/env python3
"""
Ssenariy YAML'larini tekshirish va import qilish (CONTRACT.md §9.3.1).

Validatsiya: Pydantic sxemasi (sikl yo'qligi, mavjud bo'lmagan
node/personaj/hujjatga havola yo'qligi, vaqtlar ish bo'laklari ichida,
har kunda bitta `day_end`) + ogohlantirishlar.

Ishlatish (backend/ papkasidan, `.env` bilan):

    python ../tools/import_scenario.py content/scenarios/*.yaml            # faqat tekshirish
    python ../tools/import_scenario.py --write content/scenarios/x.yaml    # draft versiya
    python ../tools/import_scenario.py --publish content/scenarios/x.yaml  # draft + e'lon

Biror fayl xato bo'lsa, hech narsa yozilmaydi.
Chiqish kodi: 0 — hammasi to'g'ri, 1 — kamida bitta fayl xato.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

import yaml  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.scenario.schema import ScenarioDefinition, scenario_warnings  # noqa: E402


def check_file(path: Path) -> ScenarioDefinition | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        defn = ScenarioDefinition.model_validate(data)
    except (OSError, yaml.YAMLError) as exc:
        print(f"XATO  {path}: {exc}")
        return None
    except ValidationError as exc:
        print(f"XATO  {path}:")
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(ildiz)"
            print(f"      {loc}: {err['msg']}")
        return None

    if path.stem != defn.slug:
        print(f"XATO  {path}: fayl nomi slug bilan bir xil bo'lishi kerak ({defn.slug}.yaml)")
        return None
    print(f"OK    {path}: {defn.slug} — {len(defn.nodes)} node, {defn.duration_days} kun")
    for warning in scenario_warnings(defn):
        print(f"      ogohlantirish: {warning}")
    return defn


async def write_all(defns: list[ScenarioDefinition], publish: bool) -> None:
    from app.database import AsyncSessionLocal
    from app.scenario.importer import import_scenario, publish_version

    async with AsyncSessionLocal() as db:
        for defn in defns:
            version, created = await import_scenario(db, defn)
            state = "yangi versiya" if created else "o'zgarmagan"
            if publish:
                await publish_version(db, version)
            print(f"DB    {defn.slug} v{version.version}: {state}, status={version.status.value}")
        await db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ssenariy YAML'larini tekshirish va import qilish (§9.3)")
    parser.add_argument("files", nargs="+", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="draft versiya sifatida DB'ga yozish")
    mode.add_argument("--publish", action="store_true", help="yozish va e'lon qilish")
    args = parser.parse_args()

    defns = [check_file(p) for p in args.files]
    if not all(defns):
        return 1
    if args.write or args.publish:
        asyncio.run(write_all(defns, publish=args.publish))
    return 0


if __name__ == "__main__":
    sys.exit(main())
