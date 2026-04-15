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
    text = re.sub(r'(AUTHORIZATION: basic )[^\s"]+', r'\1[REDACTED]', text)
    text = re.sub(r'gh[pousr]_[A-Za-z0-9_]+', '[REDACTED_GITHUB_TOKEN]', text)
    text = re.sub(
        r"(github_token\s*[\"']?\s*[:=]\s*[\"'])([^\"']+)([\"'])",
        r'\1[REDACTED]\3',
        text,
    )
    return text


def run_cmd(args: list[str], cwd: Path, ctx: PublishContext, env: dict[str, str] | None = None) -> str:
    ctx.commands.append(redact_sensitive(" ".join(args)))
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(args, cwd=str(cwd), env=merged_env, capture_output=True, text=True)
    if proc.returncode != 0:
        stdout = redact_sensitive(proc.stdout)
        stderr = redact_sensitive(proc.stderr)
        cmd = redact_sensitive(" ".join(args))
        raise RuntimeError(f"command_failed: {cmd}\nstdout:\n{stdout}\nstderr:\n{stderr}")
    return proc.stdout.strip()


def gh_authenticated(cwd: Path, ctx: PublishContext) -> bool:
    if not tool_exists('gh'):
        return False
    try:
        run_cmd(['gh', 'auth', 'status'], cwd, ctx)
        return True
    except Exception:
        return False


def git_ready(cwd: Path, ctx: PublishContext) -> bool:
    if not tool_exists('git'):
        raise RuntimeError('git が見つかりません。Git をインストールしてください。')
    return True


def github_api(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8')
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as e:
        body = redact_sensitive(e.read().decode('utf-8', errors='replace'))
        raise RuntimeError(f'github_api_failed: {method} {url} / status={e.code} / body={body}') from e
    except URLError as e:
        raise RuntimeError(f'github_api_network_error: {method} {url} / {e}') from e


def ensure_git_repo(project_root: Path, ctx: PublishContext) -> None:
    git_ready(project_root, ctx)
    if not (project_root / '.git').exists():
        run_cmd(['git', 'init'], project_root, ctx)
    try:
        run_cmd(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'], project_root, ctx)
    except Exception:
        pass
    try:
        run_cmd(['git', 'config', 'user.name'], project_root, ctx)
    except Exception:
        run_cmd(['git', 'config', 'user.name', 'bitget-bot'], project_root, ctx)
    try:
        run_cmd(['git', 'config', 'user.email'], project_root, ctx)
    except Exception:
        run_cmd(['git', 'config', 'user.email', 'bot@example.invalid'], project_root, ctx)


def reset_local_git_history(project_root: Path, ctx: PublishContext) -> None:
    git_dir = project_root / '.git'
    if git_dir.exists():
        shutil.rmtree(git_dir)
    ensure_git_repo(project_root, ctx)
    ctx.notes.append('local_git_history_reset')


def ensure_remote(project_root: Path, owner: str, repo_name: str, token: str | None, ctx: PublishContext) -> None:
    del token
    remote_url = f'https://github.com/{owner}/{repo_name}.git'
    try:
        current = run_cmd(['git', 'remote', 'get-url', 'origin'], project_root, ctx)
        if current != remote_url:
            run_cmd(['git', 'remote', 'set-url', 'origin', remote_url], project_root, ctx)
    except Exception:
        run_cmd(['git', 'remote', 'add', 'origin', remote_url], project_root, ctx)


def create_repo_with_gh(project_root: Path, repo_name: str, ctx: PublishContext) -> tuple[str, str]:
    owner = run_cmd(['gh', 'api', 'user', '--jq', '.login'], project_root, ctx).strip()
    try:
        run_cmd(['gh', 'repo', 'view', f'{owner}/{repo_name}'], project_root, ctx)
        ctx.notes.append('existing_repo_used_via_gh')
    except Exception:
        run_cmd(['gh', 'repo', 'create', repo_name, '--public', '--source', '.', '--remote', 'origin', '--push'], project_root, ctx)
        ctx.notes.append('repo_created_via_gh')
    return owner, repo_name


def create_repo_with_token(project_root: Path, owner: str, repo_name: str, token: str, ctx: PublishContext) -> tuple[str, str]:
    del project_root
    try:
        github_api('GET', f'https://api.github.com/repos/{owner}/{repo_name}', token)
        ctx.notes.append('existing_repo_used_via_token')
    except Exception:
        github_api('POST', 'https://api.github.com/user/repos', token, {'name': repo_name, 'private': False, 'auto_init': False})
        ctx.notes.append('repo_created_via_token')
    return owner, repo_name


def enable_pages_with_gh(project_root: Path, owner: str, repo_name: str, ctx: PublishContext) -> None:
    try:
        run_cmd([
            'gh', 'api', f'repos/{owner}/{repo_name}/pages', '-X', 'POST',
            '-H', 'Accept: application/vnd.github+json',
            '-f', 'source[branch]=main', '-f', 'source[path]=/docs'
        ], project_root, ctx)
        ctx.notes.append('pages_enabled_via_gh')
    except Exception as e:
        if '409' in str(e) or 'already_exists' in str(e):
            ctx.notes.append('pages_already_enabled_via_gh')
        else:
            run_cmd([
                'gh', 'api', f'repos/{owner}/{repo_name}/pages', '-X', 'PUT',
                '-H', 'Accept: application/vnd.github+json',
                '-f', 'source[branch]=main', '-f', 'source[path]=/docs'
            ], project_root, ctx)
            ctx.notes.append('pages_updated_via_gh')


def enable_pages_with_token(owner: str, repo_name: str, token: str, ctx: PublishContext) -> None:
    try:
        github_api('POST', f'https://api.github.com/repos/{owner}/{repo_name}/pages', token, {'source': {'branch': 'main', 'path': '/docs'}})
        ctx.notes.append('pages_enabled_via_token')
    except Exception as e:
        lowered = str(e).lower()
        if 'status=409' in str(e) or 'built from source' in lowered or 'already exists' in lowered:
            github_api('PUT', f'https://api.github.com/repos/{owner}/{repo_name}/pages', token, {'source': {'branch': 'main', 'path': '/docs'}})
            ctx.notes.append('pages_updated_via_token')
        else:
            raise


def commit_all(project_root: Path, ctx: PublishContext) -> None:
    run_cmd(['git', 'add', '-A'], project_root, ctx)
    status = run_cmd(['git', 'status', '--porcelain'], project_root, ctx)
    if status.strip():
        run_cmd(['git', 'commit', '-m', f'auto build {datetime.now().isoformat(timespec="seconds")}'], project_root, ctx)
        ctx.notes.append('commit_created')
    else:
        ctx.notes.append('no_changes_to_commit')


def push_with_gh(project_root: Path, ctx: PublishContext) -> None:
    run_cmd(['git', 'push', '-u', 'origin', 'main'], project_root, ctx)


def push_with_token(project_root: Path, owner: str, repo_name: str, token: str, ctx: PublishContext) -> None:
    auth = base64.b64encode(f'x-access-token:{token}'.encode('utf-8')).decode('ascii')
    run_cmd([
        'git', '-c', f'http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}',
        'push', '-u', f'https://github.com/{owner}/{repo_name}.git', 'main'
    ], project_root, ctx)


def maybe_recover_from_push_protection(
    project_root: Path,
    settings: dict[str, Any],
    owner: str,
    repo_name: str,
    token: str,
    ctx: PublishContext,
    exc: Exception,
) -> bool:
    message = str(exc)
    if 'GH013' not in message or 'Push cannot contain secrets' not in message:
        return False
    settings.setdefault('github', {})['github_token'] = token
    save_settings(project_root, settings)
    reset_local_git_history(project_root, ctx)
    ensure_remote(project_root, owner, repo_name, token, ctx)
    commit_all(project_root, ctx)
    push_with_token(project_root, owner, repo_name, token, ctx)
    ctx.notes.append('recovered_after_push_protection')
    return True


def publish_to_github(project_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    ctx = PublishContext()
    ensure_git_repo(project_root, ctx)
    repo_name = infer_repo_name(settings)
    github_settings = settings.get('github', {})
    token = (github_settings.get('github_token') or '').strip()
    owner = (github_settings.get('github_username') or '').strip()

    if gh_authenticated(project_root, ctx):
        owner, repo_name = create_repo_with_gh(project_root, repo_name, ctx)
        settings['github']['github_username'] = owner
        save_settings(project_root, settings)
        ensure_remote(project_root, owner, repo_name, None, ctx)
        commit_all(project_root, ctx)
        push_with_gh(project_root, ctx)
        enable_pages_with_gh(project_root, owner, repo_name, ctx)
    else:
        if not owner or not token:
            raise RuntimeError('GitHub へ自動公開するには、gh auth login 済みか、GUIで GitHub ユーザー名と token の入力が必要です。')
        owner, repo_name = create_repo_with_token(project_root, owner, repo_name, token, ctx)
        ensure_remote(project_root, owner, repo_name, token, ctx)
        commit_all(project_root, ctx)
        try:
            push_with_token(project_root, owner, repo_name, token, ctx)
        except Exception as exc:
            if not maybe_recover_from_push_protection(project_root, settings, owner, repo_name, token, ctx, exc):
                raise
        enable_pages_with_token(owner, repo_name, token, ctx)

    site_url = f'https://{owner}.github.io/{repo_name}' if repo_name.lower() != f'{owner.lower()}.github.io' else f'https://{owner}.github.io'
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
