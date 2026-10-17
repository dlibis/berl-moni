"""Entry point: the `send` job. Parses the flags, wires the app (bot.bootstrap) and runs one use
case from bot.service_layer.services; the job itself (spec steps 1-12) is services.send_job.

    uv run python -m bot.entrypoints.main                       # the send job (GitHub Actions)
    uv run python -m bot.entrypoints.main --to me@example.com   # local test: pending PDFs to this address only
    uv run python -m bot.entrypoints.main --no-email            # local: render PDFs to files/outputs/, write nothing to Neon
    uv run python -m bot.entrypoints.main --mark-seen           # T7: record every current feed URL as sent, scan nothing

Everything but secrets lives in Neon (programs, mailing list, schedule, addresses, limits);
the model (MODEL_NAME, MODEL_PROVIDER, its key) and RESEND_API_KEY come from the environment.
"""
import argparse
import sys
from pathlib import Path

from bot import bootstrap
from bot.service_layer import services
from bot.service_layer.unit_of_work import UnitOfWork
from common.config import require

OUTPUT_DIR = Path("./files/outputs/")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the budget-letter send job.")
    parser.add_argument(
        "--to", metavar="EMAIL",
        help="local test: send the pending PDFs to this address only (logged as kind 'test')")
    parser.add_argument(
        "--no-email", action="store_true",
        help="local: render the summary PDFs to files/outputs/, write nothing to Neon, send nothing")
    parser.add_argument(
        "--mark-seen", action="store_true",
        help="record every current feed URL as sent without scanning (T7)")
    args = parser.parse_args(argv)
    if sum(map(bool, (args.to, args.no_email, args.mark_seen))) > 1:
        parser.error("--to, --no-email and --mark-seen are mutually exclusive")
    return args


def main(argv=None, ports: services.Ports | None = None) -> int:
    """`ports` replaces the real feed / model / renderer / Resend (tests pass fakes)."""
    args = parse_args(argv)
    bootstrap.setup()
    require("check" if args.mark_seen else "test_send" if args.to else "render" if args.no_email else "send")
    ports = ports or bootstrap.ports()
    with UnitOfWork() as uow:
        if args.no_email:
            return services.render_all(uow, ports, OUTPUT_DIR)
        if args.mark_seen:
            return services.mark_seen(uow, ports)
        if args.to:
            return services.send_pending_test(uow, ports, args.to)
        return services.send_job(uow, ports)


if __name__ == "__main__":
    sys.exit(main())
