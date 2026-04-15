from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV = os.environ.copy()
ENV["BITGET_BOT_TEST_MODE"] = "1"

def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=ENV, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    print(proc.stdout.strip())


def main() -> None:
    run([sys.executable, '-m', 'py_compile', *[str(p.relative_to(PROJECT_ROOT)) for p in PROJECT_ROOT.rglob('*.py')]])
    run([sys.executable, 'scripts/entrypoint.py', '--gui'])
    run([sys.executable, 'scripts/launch.py'])
    run([sys.executable, 'scripts/launch.py', '--local-only'])
    print('SELFTEST_OK')


if __name__ == '__main__':
    main()
