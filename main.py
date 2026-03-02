import logging

from bootstrap.launcher import launch


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    launch()


if __name__ == "__main__":
    main()
