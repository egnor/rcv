#!/usr/bin/env python3

import os
import re
from pathlib import Path
from subprocess import check_call
from typing import List


def run(*args):
    print(f"\n=== {args[0]} ===")
    check_call(args)


os.chdir(str(Path(__file__).resolve().parent))
run("python3", "-m", "pip", "install", "-e", ".[dev]")

source_dirs = ["nb_to_ea"]
run("black", "-l", "80", *source_dirs)
run("isort", "--profile", "black", *source_dirs)
run("mypy", "--namespace-packages", "--explicit-package-bases", *source_dirs)
