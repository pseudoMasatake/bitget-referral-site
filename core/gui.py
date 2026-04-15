from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from .publisher import tool_exists, gh_authenticated, write_error_report
from .runtime import run_pipeline
from .settings import infer_repo_name, load_settings, load_local_secrets, referral_ready, save_settings, validate_settings


class App(tk.Tk):
    def __init__(self, project_root: Path, initial_error: str = "") -> None:
        super().__init__()
        self.project_root = project_root
        self.title('Bitget 自動公開セットアップ')
        self.geometry('980x760')
        self.minsize(900, 700)
        self.settings = load_settings(project_root)
        self._build_vars()
        self._build_ui()
        self.refresh_status(initial_error=initial_error)

    def _build_vars(self) -> None:
        github = self.settings.get('github', {})
        self.referral_var = tk.StringVar(value=self.settings.get('bitget_referral_url', ''))
        self.publish_var = tk.BooleanVar(value=github.get('publish_enabled', True))
        self.repo_var = tk.StringVar(value=github.get('repo_name', ''))
        self.username_var = tk.StringVar(value=github.get('github_username', ''))
        self.token_var = tk.StringVar(value=load_local_secrets(self.project_root).get('github', {}).get('github_token', ''))
        self.notes_var = tk.StringVar(value=self.settings.get('optional', {}).get('notes_for_chatgpt', ''))
        self.status_var = tk.StringVar(value='')

    def _build_ui(self) -> None:
        pad = {'padx': 12, 'pady': 8}
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)

        title = ttk.Label(frame, text='Bitget 自動公開セットアップ', font=('Segoe UI', 18, 'bold'))
        title.pack(anchor='w', **pad)

        sub = ttk.Label(frame, text='初回だけGUIで設定。GitHub token はローカル専用で保存し、公開用ファイルには含めません。')
        sub.pack(anchor='w', **pad)

        box = ttk.LabelFrame(frame, text='必須')
        box.pack(fill='x', padx=12, pady=6)
        ttk.Label(box, text='Bitget 招待リンク').grid(row=0, column=0, sticky='w', padx=10, pady=8)
        ttk.Entry(box, textvariable=self.referral_var).grid(row=0, column=1, sticky='ew', padx=10, pady=8)
        box.columnconfigure(1, weight=1)

        gh_box = ttk.LabelFrame(frame, text='GitHub 公開')
        gh_box.pack(fill='x', padx=12, pady=6)
        ttk.Checkbutton(gh_box, text='GitHub に公開する', variable=self.publish_var).grid(row=0, column=0, sticky='w', padx=10, pady=6)
        ttk.Label(gh_box, text='repo 名（空なら自動で bitget-referral-site）').grid(row=1, column=0, sticky='w', padx=10, pady=6)
        ttk.Entry(gh_box, textvariable=self.repo_var).grid(row=1, column=1, sticky='ew', padx=10, pady=6)
        ttk.Label(gh_box, text='GitHub ユーザー名（gh 未ログイン時だけ）').grid(row=2, column=0, sticky='w', padx=10, pady=6)
        ttk.Entry(gh_box, textvariable=self.username_var).grid(row=2, column=1, sticky='ew', padx=10, pady=6)
        ttk.Label(gh_box, text='GitHub token（gh 未ログイン時だけ）').grid(row=3, column=0, sticky='w', padx=10, pady=6)
        ttk.Entry(gh_box, textvariable=self.token_var, show='*').grid(row=3, column=1, sticky='ew', padx=10, pady=6)
        gh_box.columnconfigure(1, weight=1)

        helper = ttk.Frame(frame)
        helper.pack(fill='x', padx=12, pady=6)
        ttk.Button(helper, text='GitHub token ページを開く', command=self.open_token_page).pack(side='left', padx=6)
        ttk.Button(helper, text='設定だけ保存', command=self.save_only).pack(side='left', padx=6)
        ttk.Button(helper, text='保存して公開まで実行', command=self.run_full).pack(side='left', padx=6)
        ttk.Button(helper, text='ローカル生成だけ実行', command=self.run_local_only).pack(side='left', padx=6)
        ttk.Button(helper, text='エラーをコピー', command=self.copy_error).pack(side='left', padx=6)

        status_box = ttk.LabelFrame(frame, text='状態')
        status_box.pack(fill='x', padx=12, pady=6)
        self.status_label = ttk.Label(status_box, textvariable=self.status_var, justify='left')
        self.status_label.pack(anchor='w', padx=10, pady=10)

        ttk.Label(frame, text='結果 / エラー').pack(anchor='w', padx=12, pady=(10, 0))
        self.output = tk.Text(frame, height=20, wrap='word')
        self.output.pack(fill='both', expand=True, padx=12, pady=8)

    def open_token_page(self) -> None:
        webbrowser.open('https://github.com/settings/tokens')

    def current_settings(self) -> dict:
        data = load_settings(self.project_root)
        data['bitget_referral_url'] = self.referral_var.get().strip()
        data['github']['publish_enabled'] = bool(self.publish_var.get())
        data['github']['repo_name'] = self.repo_var.get().strip()
        data['github']['github_username'] = self.username_var.get().strip()
        data['github']['github_token'] = self.token_var.get().strip()
        data['optional']['notes_for_chatgpt'] = self.notes_var.get().strip()
        return data

    def refresh_status(self, initial_error: str = '') -> None:
        ctx = []
        ctx.append(f"python: OK")
        ctx.append(f"git: {'OK' if tool_exists('git') else 'MISSING'}")
        ctx.append(f"gh: {'LOGGED_IN' if gh_authenticated(self.project_root, __import__('core.publisher', fromlist=['PublishContext']).PublishContext()) else ('FOUND' if tool_exists('gh') else 'MISSING')}")
        ctx.append(f"referral_ready: {'YES' if referral_ready(self.current_settings()) else 'NO'}")
        ctx.append(f"repo_name: {infer_repo_name(self.current_settings())}")
        warnings = validate_settings(self.current_settings())
        ctx.append(f"warnings: {len(warnings)}")
        self.status_var.set('\n'.join(ctx))
        if initial_error:
            self.output.delete('1.0', 'end')
            self.output.insert('1.0', initial_error)

    def save_only(self) -> None:
        settings = self.current_settings()
        save_settings(self.project_root, settings)
        self.output.delete('1.0', 'end')
        self.output.insert('1.0', '設定を保存しました。\n')
        self.refresh_status()

    def _run(self, publish: bool) -> None:
        settings = self.current_settings()
        save_settings(self.project_root, settings)
        try:
            result = run_pipeline(self.project_root, settings, publish=publish)
            self.output.delete('1.0', 'end')
            self.output.insert('1.0', json.dumps(result, ensure_ascii=False, indent=2))
            messagebox.showinfo('完了', '生成が終わりました。review_bundle.zip を必要時にこのチャットへ投げてください。')
        except Exception as exc:
            report = write_error_report(self.project_root, step='gui_run_pipeline', exc=exc, settings=settings)
            self.output.delete('1.0', 'end')
            self.output.insert('1.0', report)
            messagebox.showerror('失敗', '失敗しました。赤い欄の内容をそのままこのチャットへ貼ってください。')
        finally:
            self.refresh_status()

    def run_full(self) -> None:
        self._run(publish=True)

    def run_local_only(self) -> None:
        self._run(publish=False)

    def copy_error(self) -> None:
        text = self.output.get('1.0', 'end').strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo('コピー完了', '内容をクリップボードに入れました。')


def launch_gui(project_root: Path, initial_error: str = '') -> None:
    app = App(project_root, initial_error=initial_error)
    app.mainloop()
