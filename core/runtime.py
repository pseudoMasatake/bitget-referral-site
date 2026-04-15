from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from .publisher import publish_to_github, write_error_report
from .settings import load_settings, save_settings, validate_settings
from .site_builder import build_site


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def run_pipeline(project_root: Path, settings: dict, publish: bool) -> dict:
    result: dict = {'build': None, 'publish': None, 'warnings': []}
    save_settings(project_root, settings)
    result['warnings'] = validate_settings(settings)
    build_state = build_site(project_root, settings)
    result['build'] = build_state

    if publish and settings.get('github', {}).get('publish_enabled', True):
        publish_state = publish_to_github(project_root, settings)
        settings['github']['github_username'] = publish_state['owner']
        save_settings(project_root, settings)
        result['publish'] = publish_state

    append_jsonl(project_root / 'data' / 'logs' / 'execution_log.jsonl', {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'publish_requested': publish,
        'published': bool(result['publish']),
        'warnings': result['warnings'],
        'site_url': (result['publish'] or {}).get('site_url') or build_state.get('site_url'),
        'page_count': build_state.get('page_count'),
    })
    return result
