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

from ccc.__main__ import EXIT_CRASH, main  # noqa: E402

try:
    main(args)
except (SystemExit, KeyboardInterrupt):
    raise
except Exception as err:  # noqa: BLE001
    # Neočekivana greška = bag u engine-u: kratka poruka umesto traceback-a (QA 0.8.0, P1-31); detalji u logu za podršku.
    import time
    import traceback
    log_dir = os.path.join(os.environ.get("CCC_HOME") or os.path.dirname(here), "logs")
    log = None
    try:
        os.makedirs(log_dir, exist_ok=True)
        log = os.path.join(log_dir, time.strftime("crash-%Y%m%d-%H%M%S.log"))
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("ccc " + " ".join(args) + "\n\n" + traceback.format_exc())
    except OSError:
        log = None
    msg = str(err).strip().splitlines()[0][:200] if str(err).strip() else ""
    print(f"CCC_CRASH: {type(err).__name__}{': ' + msg if msg else ''} — engine error (not your mistake)."
          + (f" Details: {log}" if log else ""), file=sys.stderr)
    sys.exit(EXIT_CRASH)
