from __future__ import annotations

import argparse
import os
import sys

if __package__ is None or __package__ == "":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings import load_settings
from app.workflows.pipeline import BASE_EXPERT_VIEW, run_revision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Word revision agent")
    parser.add_argument("--input", required=True, help="Input .docx path")
    parser.add_argument("--output", required=True, help="Output .docx path")
    parser.add_argument("--intent", required=True, help="User intent")
    parser.add_argument("--expert", default=BASE_EXPERT_VIEW, help="Expert view")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint (repeatable)")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve interrupts")
    parser.add_argument("--model", default=None, help="Model override, e.g. openai:deepseek-chat")
    parser.add_argument("--revision-engine", default=None, help="Revision engine: win32com|auto|python-docx")
    parser.add_argument(
        "--strip-existing-comments",
        action="store_true",
        help="Remove existing Word comments before processing",
    )
    parser.add_argument(
        "--allow-expansion",
        action="store_true",
        help="Allow expanding or supplementing content when intent requires it",
    )
    parser.add_argument(
        "--expansion-level",
        default=None,
        help="Expansion level: none|light|heavy (auto enables expansion when set)",
    )
    parser.add_argument(
        "--allow-web-search",
        action="store_true",
        help="Allow internet_search tool for expansion or verification",
    )
    parser.add_argument(
        "--memory-scope",
        default=None,
        help="Review memory scope: off|run|session|document (default: document)",
    )
    parser.add_argument(
        "--inline-context",
        default=None,
        help="Inline context lines: none|boundary|all (default: boundary)",
    )
    parser.add_argument(
        "--chunk-context",
        type=int,
        default=None,
        help="Cross-chunk context paragraphs (default: 2, 0 disables CTX_ONLY blocks)",
    )
    parser.add_argument(
        "--context-max-chars",
        type=int,
        default=None,
        help="Truncate CTX_* reference paragraphs to N chars (default: 1200, 0 disables truncation)",
    )
    parser.add_argument(
        "--extract-tables",
        action="store_true",
        help="Extract table elements (cells/merges/images) into *.tables.json (Win32 Word preferred; python-docx fallback)",
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        help="Extract embedded doc images into *.images.json and *_images directory",
    )
    parser.add_argument(
        "--table-image-understanding",
        action="store_true",
        help="Analyze exported table images via image-understanding agent (requires APIYI_API_KEY)",
    )
    parser.add_argument(
        "--table-image-prompt",
        default=None,
        help="Prompt for table image understanding (default: 描述分析这张图)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    if args.model:
        settings.model = args.model
    if args.revision_engine:
        settings.revision_engine = args.revision_engine
    if args.auto_approve:
        settings.auto_approve = True
    if args.strip_existing_comments:
        os.environ["STRIP_EXISTING_COMMENTS"] = "true"
    if args.allow_web_search:
        os.environ["ENABLE_WEB_SEARCH"] = "true"
    if args.memory_scope:
        os.environ["REVIEW_MEMORY_SCOPE"] = args.memory_scope
    if args.inline_context:
        os.environ["REVIEW_INLINE_CONTEXT"] = args.inline_context
    if args.chunk_context is not None:
        os.environ["REVIEW_CHUNK_CONTEXT"] = str(int(args.chunk_context))
    if args.context_max_chars is not None:
        os.environ["REVIEW_CONTEXT_MAX_CHARS"] = str(int(args.context_max_chars))
    if args.extract_tables or args.table_image_understanding:
        os.environ["EXTRACT_TABLE_ELEMENTS"] = "true"
    if args.extract_images:
        os.environ["EXTRACT_DOCX_IMAGES"] = "true"
    if args.table_image_understanding:
        os.environ["TABLE_IMAGE_UNDERSTANDING"] = "true"
    if args.table_image_prompt:
        os.environ["TABLE_IMAGE_PROMPT"] = args.table_image_prompt

    result = run_revision(
        settings=settings,
        input_path=args.input,
        output_path=args.output,
        intent=args.intent,
        expert_view=args.expert,
        constraints=args.constraint,
        allow_expansion=args.allow_expansion,
        expansion_level=args.expansion_level,
        allow_web_search=args.allow_web_search,
    )
    if result.get("messages"):
        last = result["messages"][-1]
        content = getattr(last, "content", None)
        print(content if content is not None else str(last))


if __name__ == "__main__":
    main()
