import logging

from bot.client import StatisticsBot
from bot.config import Settings


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    StatisticsBot(settings).run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
