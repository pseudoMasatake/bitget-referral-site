from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .settings import infer_repo_name, save_settings


@dataclass
class PublishContext:
    commands: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def redact_sensitive(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'(AUTHORIZATION: basic )[^\s\"]+', r'\1[REDACTED]', text)
    text = re.sub(r'gh[pousr]_[A-Za-z0-9_]+', '[REDACTED_GITHUB_TOKEN]', text)
    text = re.sub(
        r"(github_token\s*[\"']?\s*[:=]\s*[\"'])([^\"']+)([\"'])",
        r'\1[REDACTED]\3',
        text,
    )
    return text


def run_cmd(args: list[str], cwd: Path, ctx: PublishContext, env: dict[str, str] | None = None) -> str:
    ctx.commands.append(redact_sensitive(' '.join(args)))
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(args, cwd=str(cwd), env=merged_env, capture_output=True, text=True)
    if proc.returncode != 0:
        stdout = redact_sensitive(proc.stdout)
        stderr = redact_sensitive(proc.stderr)
        cmd = redact_sensitive(' '.join(args))
        raise RuntimeError(f'command_failed: {cmd}\nstdout:\n{stdout}\nstderr:\n{stderr}')
    return proc.stdout.strip()


def gh_authenticated(cwd: Path, ctx: PublishContext) -> bool:
    if not tool_exists('gh'):
        return False
    try:
        run_cmd(['gh', 'auth', 'status'], cwd, ctx)
        return True
    except Exception:
        return False


def github_api(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | list[Any] | None:
    data = None
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'bitget-referral-bot',
    }
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode('utf-8')
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as e:
        body = redact_sensitive(e.read().decode('utf-8', errors='replace'))
        raise RuntimeError(f'github_api_failed: {method} {url} / status={e.code} / body={body}') from e
    except URLError as e:
        raise RuntimeError(f'github_api_network_error: {method} {url} / {e}') from e


def github_get_authenticated_user(token: str) -> str:
    data = github_api('GET', 'https://api.github.com/user', token)
    if not isinstance(data, dict) or not data.get('login'):
        raise RuntimeError('GitHub API からユーザー名を取得できませんでした。token を確認してください。')
    return str(data['login'])


def create_or_get_repo(owner: str, repo_name: str, token: str, ctx: PublishContext) -> tuple[str, str]:
    try:
        github_api('GET', f'https://api.github.com/repos/{owner}/{repo_name}', token)
        ctx.notes.append('existing_repo_used_via_api')
    except Exception:
        github_api('POST', 'https://api.github.com/user/repos', token, {
            'name': repo_name,
            'private': False,
            'auto_init': True,
            'has_issues': False,
            'has_projects': False,
            'has_wiki': False,
        })
        ctx.notes.append('repo_created_via_api')
    return owner, repo_name


def repo_file_candidates(project_root: Path) -> list[Path]:
    include_roots = [
        'PROJECT_INSTRUCTIONS.md',
        'README.md',
        'SETUP_3MIN.md',
        'start_local_windows.bat',
        'start_local_unix.sh',
        'config',
        'core',
        'docs',
        'scripts',
    ]
    skip_names = {'.git', '__pycache__', '.DS_Store'}
    skip_suffixes = {'.pyc'}
    skip_relative = {
        'config/.local_secrets.json',
        'data/state/setup_error_report.txt',
    }
    out: list[Path] = []
    for item in include_roots:
        start = project_root / item
        if not start.exists():
            continue
        if start.is_file():
            rel = start.relative_to(project_root).as_posix()
            if rel not in skip_relative:
                out.append(start)
            continue
        for path in start.rglob('*'):
            if path.is_dir():
                continue
            rel = path.relative_to(project_root).as_posix()
            if any(part in skip_names for part in path.parts):
                continue
            if path.suffix in skip_suffixes:
                continue
            if rel in skip_relative:
                continue
            out.append(path)
    return sorted(out)


def get_remote_sha(owner: str, repo_name: str, token: str, rel: str) -> str | None:
    try:
        data = github_api('GET', f'https://api.github.com/repos/{owner}/{repo_name}/contents/{rel}', token)
    except Exception as e:
        if 'status=404' in str(e):
            return None
        raise
    if isinstance(data, dict):
        sha = data.get('sha')
        return str(sha) if sha else None
    return None


def put_repo_file(owner: str, repo_name: str, token: str, rel: str, content: bytes, ctx: PublishContext) -> None:
    sha = get_remote_sha(owner, repo_name, token, rel)
    payload: dict[str, Any] = {
        'message': f'update {rel}',
        'content': base64.b64encode(content).decode('ascii'),
        'branch': 'main',
    }
    if sha:
        payload['sha'] = sha
    github_api('PUT', f'https://api.github.com/repos/{owner}/{repo_name}/contents/{rel}', token, payload)
    ctx.notes.append(f'uploaded:{rel}')


def sync_repo_via_contents_api(project_root: Path, owner: str, repo_name: str, token: str, ctx: PublishContext) -> None:
    files = repo_file_candidates(project_root)
    for path in files:
        rel = path.relative_to(project_root).as_posix()
        put_repo_file(owner, repo_name, token, rel, path.read_bytes(), ctx)
    ctx.notes.append(f'uploaded_count:{len(files)}')


def enable_pages_with_token(owner: str, repo_name: str, token: str, ctx: PublishContext) -> None:
    payload = {'source': {'branch': 'main', 'path': '/docs'}}
    try:
        github_api('POST', f'https://api.github.com/repos/{owner}/{repo_name}/pages', token, payload)
        ctx.notes.append('pages_enabled_via_api')
    except Exception as e:
        lowered = str(e).lower()
        if 'status=409' in str(e) or 'already exists' in lowered or 'built from source' in lowered:
            github_api('PUT', f'https://api.github.com/repos/{owner}/{repo_name}/pages', token, payload)
            ctx.notes.append('pages_updated_via_api')
        else:
            raise
    try:
        github_api('POST', f'https://api.github.com/repos/{owner}/{repo_name}/pages/builds', token, {})
        ctx.notes.append('pages_build_requested')
    except Exception:
        ctx.notes.append('pages_build_request_skipped')


def poll_pages_url(owner: str, repo_name: str, token: str, ctx: PublishContext) -> str:
    fallback = f'https://{owner}.github.io/{repo_name}' if repo_name.lower() != f'{owner.lower()}.github.io' else f'https://{owner}.github.io'
    for _ in range(20):
        try:
            data = github_api('GET', f'https://api.github.com/repos/{owner}/{repo_name}/pages', token)
            if isinstance(data, dict):
                html_url = str(data.get('html_url') or '').strip()
                status = str(data.get('status') or '').lower()
                if status:
                    ctx.notes.append(f'pages_status:{status}')
                if html_url:
                    return html_url.rstrip('/')
        except Exception:
            pass
        time.sleep(3)
    return fallback


def publish_to_github(project_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    ctx = PublishContext()
    repo_name = infer_repo_name(settings)
    github_settings = settings.get('github', {})
    token = str(github_settings.get('github_token') or '').strip()
    owner = str(github_settings.get('github_username') or '').strip()

    if not token:
        raise RuntimeError('GitHub へ自動公開するには GUI に GitHub token の入力が必要です。')

    if not owner:
        owner = github_get_authenticated_user(token)
        settings.setdefault('github', {})['github_username'] = owner
        save_settings(project_root, settings)
        ctx.notes.append('github_username_inferred_from_token')

    owner, repo_name = create_or_get_repo(owner, repo_name, token, ctx)
    sync_repo_via_contents_api(project_root, owner, repo_name, token, ctx)
    enable_pages_with_token(owner, repo_name, token, ctx)
    site_url = poll_pages_url(owner, repo_name, token, ctx)

    return {
        'owner': owner,
        'repo_name': repo_name,
        'site_url': site_url,
        'commands': ctx.commands,
        'notes': ctx.notes,
    }


def write_error_report(project_root: Path, *, step: str, exc: BaseException, settings: dict[str, Any], extra: dict[str, Any] | None = None) -> str:
    report_path = project_root / 'data' / 'state' / 'setup_error_report.txt'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'step': step,
        'python': sys.version,
        'cwd': str(project_root),
        'error_type': type(exc).__name__,
        'error_message': redact_sensitive(str(exc)),
        'settings_summary': {
            'referral_ready': 'REPLACE_ME' not in settings.get('bitget_referral_url', ''),
            'publish_enabled': settings.get('github', {}).get('publish_enabled', True),
            'repo_name': settings.get('github', {}).get('repo_name', ''),
            'github_username': settings.get('github', {}).get('github_username', ''),
            'has_github_token': bool(settings.get('github', {}).get('github_token', '')),
        },
        'extra': extra or {},
        'traceback': redact_sensitive(traceback.format_exc()),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    report_path.write_text(text + '\n', encoding='utf-8')
    return text
