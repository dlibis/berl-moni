"""Entry point: the worker. Parses the flags, wires the app (bot.bootstrap) and runs the use cases from
bot.service_layer; with no flag it drains the analysis queue, then runs services.send_job (spec steps 1-12).

    uv run python -m bot.entrypoints.main                       # drain + the send job (GitHub Actions)
    uv run python -m bot.entrypoints.main --to me@example.com   # local test: unsent letters to this address only
    uv run python -m bot.entrypoints.main --no-email            # local: render PDFs to files/outputs/, write nothing to Neon

Everything but secrets lives in Neon (programs, mailing list, schedule, addresses, limits);
the model (MODEL_NAME, MODEL_PROVIDER, its key) and RESEND_API_KEY come from the environment.
"""
import argparse
import sys
from pathlib import Path

from bot import bootstrap
from bot.service_layer import services
from bot.service_layer.analysis import drain_queue
from bot.service_layer.unit_of_work import UnitOfWork
from common.config import require

OUTPUT_DIR = Path("./files/outputs/")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the budget-letter send job.")
    parser.add_argument(
        "--to", metavar="EMAIL",
        help="local test: send the unsent analyzed letters to this address only (logged as kind 'test')")
    parser.add_argument(
        "--no-email", action="store_true",
        help="local: render the summary PDFs to files/outputs/, write nothing to Neon, send nothing")
    args = parser.parse_args(argv)
    if args.to and args.no_email:
        parser.error("--to and --no-email are mutually exclusive")
    return args


def main(argv=None, ports: services.Ports | None = None) -> int:
    """`ports` replaces the real feed / model / renderer / Resend (tests pass fakes)."""
    args = parse_args(argv)
    bootstrap.setup()
    require("test_send" if args.to else "render" if args.no_email else "send")
    ports = ports or bootstrap.ports()
    with UnitOfWork() as uow:
        if args.no_email:
            return services.render_all(uow, ports, OUTPUT_DIR)
        if args.to:
            return services.send_pending_test(uow, ports, args.to)
        drained = drain_queue(uow, ports.extractor, bootstrap.model_name())  # every run, due or not
        code = services.send_job(uow, ports)
        return 1 if drained.failed else code


if __name__ == "__main__":
    sys.exit(main())
