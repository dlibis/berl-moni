"""Run the pipeline on ONE letter (URL or local PDF path) and render its summary PDF.

    uv run python -m bot.entrypoints.run_url <url-or-pdf-path>
    uv run python -m bot.entrypoints.run_url <url-or-pdf-path> --to me@example.com   # also email it

Extracts the single letter and writes its summary PDF to files/outputs/<slug>_summary.pdf,
then prints the path. Handy for eyeballing one letter end-to-end without waiting on the
whole Knesset feed. Renders even when the letter is not master-relevant, so you always
see a file (with only its budget table: an irrelevant letter's fields are never read). Run from the repo root (output paths are relative to it).
"""
import argparse
import sys

from bot import bootstrap
from bot.adapters.summary_pdf.renderer import SummaryPdfRenderer
from bot.domain.slug import letter_slug
from bot.entrypoints.main import OUTPUT_DIR
from bot.service_layer import services
from bot.service_layer.unit_of_work import UnitOfWork


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract one letter and render its summary PDF.")
    parser.add_argument("source", help="letter URL or local PDF path")
    parser.add_argument("--to", action="append", metavar="EMAIL",
                        help="also email the summary PDF to this address (repeatable)")
    return parser.parse_args(argv)


def run(source: str):
    """Extract one letter and render its summary PDF; return (summary path, extraction)."""
    with UnitOfWork() as uow:
        programs = uow.programs()
    result = bootstrap.extractor(programs).extract(source)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{letter_slug(source)}_summary.pdf"
    return SummaryPdfRenderer().render(result, path, result.named_matches(programs)), result


def main(argv=None) -> int:
    args = parse_args(argv)
    bootstrap.setup()
    path, result = run(args.source)
    print(f"relevant={result.relevant}  master-matches={len(result.matched_codes)}  "
          f"coalition={result.fields.coalition_funds!r}")
    print("summary PDF:", path)
    if not args.to:
        return 0
    with UnitOfWork() as uow:
        code = services.send_test_message(uow, bootstrap.ports(), args.to, [(path.name, path.read_bytes())])
    print(f"emailed to {len(args.to)} recipient(s)" if code == 0 else "send failed (see the log above)")
    return code


if __name__ == "__main__":
    sys.exit(main())
