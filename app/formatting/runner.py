from __future__ import annotations

import argparse
import sys

from app.formatting.profiles import _apply_format_profile_inprocess, resolve_profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a formatting profile to a DOCX via Word automation.")
    parser.add_argument("--docx_path", required=True, help="Path to the .docx file (will be modified in place).")
    parser.add_argument("--root_dir", required=True, help="Project root dir (used to locate templates/resources).")
    parser.add_argument("--profile", required=True, help="Format profile key (e.g. zhengda_cup).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    profile = resolve_profile(args.profile)
    _apply_format_profile_inprocess(docx_path=args.docx_path, root_dir=args.root_dir, profile=profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

