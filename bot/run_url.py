"""Run the pipeline on ONE letter (URL or local PDF path) and render its summary PDF.

    uv run python bot/run_url.py <url-or-pdf-path>
    uv run python bot/run_url.py <url-or-pdf-path> --to me@example.com   # also email it

Extracts the single letter and writes its summary PDF to files/outputs/<slug>_summary.pdf,
then prints the path. Handy for eyeballing one letter end-to-end without waiting on the
whole Knesset feed. Renders even when the letter is not master-relevant, so you always
see a file. Run from the repo root (output paths are relative to it).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent
from common.config_manager import ConfigManager
from common.db import load_programs
from main import OUTPUT_DIR, render_summary
from notifier import ResendError
from send_test_mail import send_test
from utils_function import _slug


def run(source: str):
    """Extract one letter and render its summary PDF; return (rendered, result)."""
    master_programs = load_programs()
    extractor = agent.Agent(
        master_programs,
        api_key=ConfigManager.get_api_key(),
        model=ConfigManager.get_model_name(),
        provider=ConfigManager.get_model_provider(),
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = extractor.extract(source)
    relevant_programs = {
        code: master_programs.get(code, "") for code in sorted(result.matched_codes)
    }
    rendered = render_summary(result, _slug(source), OUTPUT_DIR, relevant_programs)
    return rendered, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract one letter and render its summary PDF.")
    parser.add_argument("source", help="letter URL or local PDF path")
    parser.add_argument("--to", action="append", metavar="EMAIL",
                        help="also email the summary PDF to this address (repeatable)")
    args = parser.parse_args()
    rendered, result = run(args.source)
    print(f"relevant={result.relevant}  master-matches={len(result.matched_codes)}  "
          f"coalition={result.fields.coalition_funds!r}")
    print("summary PDF:", rendered[0] if rendered else "(none rendered)")
    if args.to and rendered:
        path, name = rendered
        with open(path, "rb") as f:
            pdf = f.read()
        try:
            send_test(args.to, [(f"{name}.pdf", pdf)])
            print(f"emailed to {len(args.to)} recipient(s)")
        except ResendError as e:
            print(f"send failed: {e}")
    elif args.to:
        print("(nothing sent)")
