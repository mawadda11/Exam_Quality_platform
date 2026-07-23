from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_SOURCE = ROOT / "knowledge_base" / "source"
DEFAULT_MANIFEST = ROOT / "knowledge_base" / "manifest.json"

# The shared validation/normalization/manifest logic lives in the backend
# app package (app.services.knowledge_base) so this script and the backend
# (and, from M8 onward, the rule engine) share one implementation rather
# than duplicating it here.
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.knowledge_base.manifest import build_manifest, write_manifest  # noqa: E402
from app.services.knowledge_base.models import KnowledgeBaseValidationError  # noqa: E402
from app.services.knowledge_base.normalizer import normalize_all  # noqa: E402
from app.services.knowledge_base.schemas import ALL_WORKBOOK_SCHEMAS  # noqa: E402
from app.services.knowledge_base.validator import load_and_validate  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and normalize the Exam Quality knowledge base.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Directory containing the 11 approved workbooks (default: knowledge_base/source).",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Where to write the generated manifest.json (default: knowledge_base/manifest.json).",
    )
    parser.add_argument(
        "--no-write-manifest",
        action="store_true",
        help="Validate only; do not write the manifest file (useful for test fixtures).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    source_dir = args.source_dir

    missing = [s.filename for s in ALL_WORKBOOK_SCHEMAS if not (source_dir / s.filename).is_file()]
    if missing:
        print("Knowledge-base validation failed. Missing approved files:")
        for name in missing:
            print(f"- {name}")
        print("Add the original approved workbooks; do not generate substitute records.")
        return 1

    try:
        raw_workbooks = load_and_validate(source_dir)
    except KnowledgeBaseValidationError as exc:
        print(f"Knowledge-base validation failed with {len(exc.issues)} issue(s):")
        for issue in exc.issues:
            print(f"- {issue.format()}")
        return 1

    records = normalize_all(raw_workbooks)
    manifest = build_manifest(source_dir, raw_workbooks, records, validation_status="valid")

    print(f"Validated and normalized {len(records)} records across {len(raw_workbooks)} workbooks.")

    if not args.no_write_manifest:
        write_manifest(manifest, args.manifest_path)
        try:
            shown_path = args.manifest_path.relative_to(ROOT)
        except ValueError:
            shown_path = args.manifest_path
        print(f"Wrote {shown_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
