"""Command-line foundation for the Mobility Control Tower."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mobility-control-tower")
    parser.add_argument("--version", action="version", version="mobility-control-tower 0.1.0")
    return parser


def main() -> int:
    build_parser().parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
