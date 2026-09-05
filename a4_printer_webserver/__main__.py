"""Run the web server with ``python -m a4_printer_webserver``."""

from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

from .app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve a password-protected web interface for one A4 printer."
    )
    parser.add_argument(
        "--uuid",
        required=True,
        type=_printer_uuid,
        help="UUID reported by a4-printer-interface for the target printer",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="password required to access the website",
    )
    parser.add_argument("--title", default="Printer Website", help="website title")
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on")
    parser.add_argument("--port", default=5000, type=int, help="TCP port to listen on")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("printer_data"),
        help="directory used for uploaded files and queue history",
    )
    parser.add_argument(
        "--max-upload-mb",
        default=100,
        type=_positive_integer,
        help="maximum size of one uploaded file in MiB",
    )
    parser.add_argument(
        "--auto-delete",
        metavar="DAYS",
        type=_positive_integer,
        help="delete submitted document files after this many days",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.password:
        raise SystemExit("--password cannot be empty")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = create_app(
        printer_uuid=args.uuid,
        password=args.password,
        title=args.title,
        data_dir=args.data_dir,
        max_upload_mb=args.max_upload_mb,
        auto_delete_days=args.auto_delete,
    )
    service = app.extensions["printer_service"]
    try:
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    finally:
        service.stop()


def _printer_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise argparse.ArgumentTypeError("must be a valid UUID") from None


def _positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


if __name__ == "__main__":
    main()
