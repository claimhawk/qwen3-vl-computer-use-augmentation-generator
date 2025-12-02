# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Utility functions for CUDAG framework."""

from __future__ import annotations

import os
import sys


def check_script_invocation() -> None:
    """Check if generator was invoked from shell script, print warning if not.

    Generators should be run via ./scripts/generate.sh to ensure the full
    pipeline (generate + upload + preprocess) is executed. Running generator.py
    directly will skip upload and preprocessing.

    The shell script should set CUDAG_FROM_SCRIPT=1 before calling the generator.
    """
    if os.environ.get("CUDAG_FROM_SCRIPT") != "1":
        print("")
        print("*" * 60)
        print("*" + " " * 58 + "*")
        print("*" + "  WARNING: Running generator.py directly!".center(56) + "  *")
        print("*" + " " * 58 + "*")
        print("*" + "  Use ./scripts/generate.sh for the full pipeline:".center(56) + "  *")
        print("*" + "  - Dataset generation".center(56) + "  *")
        print("*" + "  - Upload to Modal".center(56) + "  *")
        print("*" + "  - Preprocessing".center(56) + "  *")
        print("*" + " " * 58 + "*")
        print("*" + "  Run: ./scripts/generate.sh".center(56) + "  *")
        print("*" + "  Or:  ./scripts/generate.sh --dry  (no upload)".center(56) + "  *")
        print("*" + " " * 58 + "*")
        print("*" * 60)
        print("")
        sys.stderr.flush()
        sys.stdout.flush()
