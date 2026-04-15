# Affiliate Bot Project

このプロジェクトは、**あなたが編集する場所を `config/user_settings.json` だけに集約**した、GitHub Pages 用の自動生成アフィリエイトサイトです。

## あなたが触る場所
- `config/user_settings.json` だけ

## あなたが触らない場所
- `core/` すべて
- `scripts/` すべて
- `.github/workflows/` すべて

## 起動方法
- ローカル: `python scripts/launch.py`
- GitHub: Actions → `Build and Publish Affiliate Site` → `Run workflow`

## ChatGPT に投げるとき
この3つだけ渡せば改善しやすいです。
- `config/user_settings.json`
- `data/state/improvement_packet.md`
- `data/state/build_state.json`
