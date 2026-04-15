# 手順書

## 初回だけ
1. `start_local_windows.bat` または `start_local_unix.sh` を起動する。
2. GUI が開いたら、`Bitget 招待リンク` を貼る。
3. `GitHub に公開する` を ON のままにする。
4. すでに `gh auth login` 済みならそのまま `保存して公開まで実行` を押す。
5. `gh` 未設定なら、GUI の GitHub 欄に
   - GitHub ユーザー名
   - Personal Access Token
   を入れて `保存して公開まで実行` を押す。

## 2回目以降
1. 同じ起動ファイルを実行する。
2. 自動で生成・push・公開更新まで進む。
3. 必要なら `data/state/review_bundle.zip` をこのチャットへ投げる。

## エラー時
1. GUI の赤い欄をそのままコピーする。
2. または `data/state/setup_error_report.txt` を開いて中身を全部コピーする。
3. このチャットに貼る。
