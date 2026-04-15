from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.gui import launch_gui
from core.publisher import write_error_report
from core.runtime import run_pipeline
from core.settings import load_settings, startup_needs_gui


def main() -> None:
    settings = load_settings(PROJECT_ROOT)
    force_gui = '--gui' in sys.argv
    if force_gui or startup_needs_gui(settings):
        launch_gui(PROJECT_ROOT)
        return

    try:
        result = run_pipeline(PROJECT_ROOT, settings, publish=True)
        print('OK')
        print(f"site_url={ (result.get('publish') or {}).get('site_url') or (result.get('build') or {}).get('site_url') }")
        print(f"review_bundle={PROJECT_ROOT / 'data' / 'state' / 'review_bundle.zip'}")
    except Exception as exc:
        report = write_error_report(PROJECT_ROOT, step='entrypoint_auto_run', exc=exc, settings=settings)
        launch_gui(PROJECT_ROOT, initial_error=report)


if __name__ == '__main__':
    main()
