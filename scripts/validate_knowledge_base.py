from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXPECTED_FILES = [
    "01_references.xlsx",
    "02_standards.xlsx",
    "03_criteria.xlsx",
    "04_requirements.xlsx",
    "05_evidence_types.xlsx",
    "06_evidence_mapping.xlsx",
    "07_evaluation_rules.xlsx",
    "08_recommendations.xlsx",
    "09_relationships.xlsx",
    "10_metadata.xlsx",
    "11_scoring_policy.xlsx",
]

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "knowledge_base" / "source"
MANIFEST = ROOT / "knowledge_base" / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    missing = [name for name in EXPECTED_FILES if not (SOURCE / name).is_file()]
    if missing:
        print("Knowledge-base validation failed. Missing approved files:")
        for name in missing:
            print(f"- {name}")
        print("Add the original approved workbooks; do not generate substitute records.")
        return 1

    files = [
        {
            "name": name,
            "sha256": sha256(SOURCE / name),
            "size_bytes": (SOURCE / name).stat().st_size,
        }
        for name in EXPECTED_FILES
    ]
    MANIFEST.write_text(
        json.dumps(
            {
                "knowledge_base_name": "Exam Quality Knowledge Base",
                "version": "1.0",
                "status": "validated-file-presence-and-hashes",
                "files": files,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Validated {len(files)} files. Wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
