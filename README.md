# Bitget Referral Auto Site

このプロジェクトは、Bitget の招待リンクを 1 回入れたあと、
- ページ生成
- GitHub への push
- GitHub Pages 公開
- 改善用レビュー束の生成
をできるだけ自動で回すためのものです。

## あなたが普段やること

- `start_local_windows.bat` または `start_local_unix.sh` を起動する
- 初回だけ GUI に従って設定する
- たまに `data/state/review_bundle.zip` をこのチャットへ投げる

## 重要

- 初回の GitHub 認証だけは必要です。
- GUI は `gh` ログイン済みならそれを使います。
- `gh` が使えない場合は、GUI で GitHub ユーザー名と Personal Access Token を 1 回だけ入れられます。
- 失敗時は `data/state/setup_error_report.txt` が出ます。GUI 上でもそのままコピーできます。
