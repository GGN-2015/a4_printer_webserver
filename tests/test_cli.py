from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from a4_printer_webserver.__main__ import build_parser

PRINTER_UUID = "8fd0d51f-12c8-5b50-a2f1-4f64641ae77c"


class CommandLineTests(unittest.TestCase):
    def test_auto_delete_accepts_a_positive_number_of_days(self) -> None:
        args = build_parser().parse_args(
            [
                "--uuid",
                PRINTER_UUID,
                "--password",
                "secret",
                "--auto-delete",
                "7",
            ]
        )

        self.assertEqual(args.auto_delete, 7)

    def test_auto_delete_is_disabled_by_default(self) -> None:
        args = build_parser().parse_args(
            ["--uuid", PRINTER_UUID, "--password", "secret"]
        )

        self.assertIsNone(args.auto_delete)

    def test_auto_delete_rejects_zero(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "--uuid",
                    PRINTER_UUID,
                    "--password",
                    "secret",
                    "--auto-delete",
                    "0",
                ]
            )
