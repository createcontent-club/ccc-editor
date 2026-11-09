"""Ulazna tačka koju poziva wrapper `ccc` (Mac i Windows/Git Bash).

Radni folder stiže kao ARGUMENT (`--home <putanja>`), ne kroz promenljivu okruženja: Git Bash na Windows-u
pretvara Unix putanje u Windows putanje samo u argumentima programa.
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
if len(args) >= 2 and args[0] == "--home":
    os.environ["CCC_HOME"] = os.path.abspath(os.path.expanduser(args[1]))
    args = args[2:]
sys.path.insert(0, here)
os.environ["PYTHONPATH"] = here + os.pathsep + os.environ.get("PYTHONPATH", "")  # za pod-procese (ccc.face)

from ccc.__main__ import main  # noqa: E402

main(args)
