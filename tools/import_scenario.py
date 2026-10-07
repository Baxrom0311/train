#!/usr/bin/env python3
"""
Ssenariy YAML'larini tekshirish (CONTRACT.md §9.3.1).

Hozircha faqat validatsiya: Pydantic sxemasi (sikl yo'qligi, mavjud
bo'lmagan node/personaj/hujjatga havola yo'qligi, vaqtlar ish bo'laklari
ichida, har kunda bitta `day_end`) + ogohlantirishlar. `scenario_versions`ga
`draft` sifatida yozish modellar va migratsiya qo'shilgach (P3) shu
skriptga qo'shiladi.

Ishlatish (backend/ papkasidan, `.env` bilan):

    python ../tools/import_scenario.py content/scenarios/*.yaml

Chiqish kodi: 0 — hammasi to'g'ri, 1 — kamida bitta fayl xato.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

import yaml  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.scenario.schema import ScenarioDefinition, scenario_warnings  # noqa: E402


def check_file(path: Path) -> bool:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        defn = ScenarioDefinition.model_validate(data)
    except (OSError, yaml.YAMLError) as exc:
        print(f"XATO  {path}: {exc}")
        return False
    except ValidationError as exc:
        print(f"XATO  {path}:")
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(ildiz)"
            print(f"      {loc}: {err['msg']}")
        return False

    if path.stem != defn.slug:
        print(f"XATO  {path}: fayl nomi slug bilan bir xil bo'lishi kerak ({defn.slug}.yaml)")
        return False
    print(f"OK    {path}: {defn.slug} — {len(defn.nodes)} node, {defn.duration_days} kun")
    for warning in scenario_warnings(defn):
        print(f"      ogohlantirish: {warning}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Ssenariy YAML'larini tekshirish (§9.3)")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    results = [check_file(p) for p in args.files]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
