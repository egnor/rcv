#!/usr/bin/env python3

import os
import re
from pathlib import Path
from subprocess import check_call
from typing import List

os.chdir(str(Path(__file__).resolve().parent))


def run(*args):
    print(f"\n=== {args[0]} ===")
    check_call(args)


run("black", "-l", "80", ".")
run("isort", "--profile", "black", ".")
run("mypy", "--namespace-packages", "--explicit-package-bases", ".")
