# 3分セットアップ

## 触るのは原則これだけ
- `config/user_settings.json`

## 1. まず 1ファイルだけ編集
次の項目だけ差し替える。
- `site.site_url`
- `site.owner_name`
- `offers[].offer_url`

余裕があれば次も変える。
- `site.site_name`
- `offers[].name`
- `offers[].audience`

## 2. GitHub に置く
- 新規リポジトリを作る
- このフォルダ一式を push する

## 3. Pages を有効化
- Settings → Pages
- Source を GitHub Actions にする

## 4. Actions を有効化
- Actions タブを開く
- Workflow を有効化する

## 5. 起動
- Actions → `Build and Publish Affiliate Site`
- `Run workflow` を押す

## 今後の操作
- ふだんは `Run workflow` を押すだけ
- 改善したいときは `data/state/improvement_packet.md` を ChatGPT に投げるだけ
