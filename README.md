# affiliate_bot_project

## 構造
- `user/` あなたの設定だけ。今後の本体更新で消さない。
- `app/` 私が更新する本体コード。
- `docs/` 生成される公開用サイト。
- `data/state/` 実行ログと review bundle。

## 今後の更新ルール
- 私が送る更新は原則 `app/` と起動スクリプトだけ。
- `user/profile.json` は残す。ここに招待URLと token を保持する。
- 新しい本体ZIPを上書きしても `user/` を消さなければ再入力不要。
