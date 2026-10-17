"""Check the Resend key and sending domain, then send one test email from the Neon from_address.

    uv run python -m bot.entrypoints.send_test_mail                      # send to the mailing list
    uv run python -m bot.entrypoints.send_test_mail --to me@example.com  # send only to this address
    uv run python -m bot.entrypoints.send_test_mail --check              # only verify RESEND_API_KEY and berl.site

Needs RESEND_API_KEY in .env and settings.from_address / reply_to_address in Neon. Run from the repo root.
"""
import argparse
import sys

from bot import bootstrap
from bot.adapters.resend.domains import domain_problem
from bot.service_layer import services
from bot.service_layer.unit_of_work import UnitOfWork


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test email through Resend.")
    parser.add_argument("--check", action="store_true", help="only verify the key and the domain")
    parser.add_argument("--to", action="append", metavar="EMAIL",
                        help="send to this address instead of the mailing list (repeatable)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    bootstrap.setup()
    problem = domain_problem(services.SENDER_DOMAIN)
    if problem:
        print(problem)
        return 1
    print(f"Resend key OK, {services.SENDER_DOMAIN} verified")
    if args.check:
        return 0
    with UnitOfWork() as uow:
        recipients = args.to or uow.mailing_list()
        if not recipients:
            print("mailing list is empty and no --to given")
            return 1
        print(f"sending test email to {len(recipients)} recipient(s)")
        return services.send_test_message(uow, bootstrap.ports(), recipients)


if __name__ == "__main__":
    sys.exit(main())
