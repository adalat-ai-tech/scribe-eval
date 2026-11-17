#!/usr/bin/env python3
"""Thin wrapper around the packaged ``scribe-batch`` command.

The CLI itself lives in ``scribe.batch_cli`` and is installed as
``scribe-batch``. This script only supplies repository defaults so the
demo runs from any cwd with no arguments: the bundled sample input
(``examples/predictions.jsonl``) and an output directory beside it
(``examples/output/``). Every ``scribe-batch`` flag is accepted.
"""

import sys
from pathlib import Path

from scribe.batch_cli import main

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    sys.exit(
        main(
            default_input=str(script_dir / "predictions.jsonl"),
            default_output=str(script_dir / "output"),
        )
    )
