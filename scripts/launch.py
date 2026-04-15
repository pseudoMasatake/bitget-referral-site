from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.gui import launch_gui
from core.runtime import run_pipeline
from core.settings import load_settings, startup_needs_gui


def main() -> None:
    publish = '--publish' in sys.argv
    settings = load_settings(PROJECT_ROOT)
    if startup_needs_gui(settings):
        launch_gui(PROJECT_ROOT)
        return
    result = run_pipeline(PROJECT_ROOT, settings, publish=publish)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
