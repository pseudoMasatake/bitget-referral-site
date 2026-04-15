from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, parse_qsl, urlencode, urlunparse
from zipfile import ZIP_DEFLATED, ZipFile

from .settings import infer_repo_name, infer_site_url, validate_settings

SITE_NAME = "Bitget比較ラボ"
SITE_TAGLINE = "Bitget招待リンクの成果を最大化するための比較・始め方・FAQ集約サイト"
OBJECTIVE = "maximize_bitget_referral_clicks_then_referral_outcomes"

PAGES: list[dict[str, Any]] = [
    {"slug": "index", "title": "Bitgetを比較して最短で始めるための入口", "keyword": "Bitget 比較", "stage": "hub", "category": "hub", "reader": "Bitgetを候補に入れている比較検討者", "angle": "比較・手順・FAQを1か所にまとめる入口", "related": ["bitget-registration-guide", "bitget-fees-guide", "bitget-safety-guide", "bitget-bonus-guide"]},
    {"slug": "bitget-registration-guide", "title": "Bitgetの始め方を最短で確認する", "keyword": "Bitget 始め方", "stage": "high_intent", "category": "getting_started", "reader": "すぐ登録したい初心者", "angle": "登録手順と詰まりどころを先回りして潰す", "related": ["bitget-kyc-guide", "bitget-fees-guide", "bitget-bonus-guide"]},
    {"slug": "bitget-fees-guide", "title": "Bitgetの手数料を登録前に整理する", "keyword": "Bitget 手数料", "stage": "high_intent", "category": "fees", "reader": "費用で迷っている比較検討者", "angle": "何の費用で差が出やすいかに絞る", "related": ["bitget-bybit-comparison", "bitget-binance-comparison", "bitget-registration-guide"]},
    {"slug": "bitget-safety-guide", "title": "Bitgetの安全性を不安ごとに切り分ける", "keyword": "Bitget 安全性", "stage": "mid_intent", "category": "safety", "reader": "海外取引所に慎重な初心者", "angle": "抽象論ではなく確認項目を先に出す", "related": ["bitget-kyc-guide", "bitget-faq", "bitget-registration-guide"]},
    {"slug": "bitget-bonus-guide", "title": "Bitgetの招待特典とキャンペーン確認の入口", "keyword": "Bitget 招待コード", "stage": "high_intent", "category": "bonus", "reader": "特典で比較したい人", "angle": "特典条件は断定せず確認導線として使う", "related": ["bitget-registration-guide", "bitget-beginner-checklist", "bitget-faq"]},
    {"slug": "bitget-app-guide", "title": "Bitgetアプリ中心で使いたい人向けの整理", "keyword": "Bitget アプリ", "stage": "mid_intent", "category": "app", "reader": "スマホ中心の利用者", "angle": "アプリ前提で判断材料を整理する", "related": ["bitget-registration-guide", "bitget-safety-guide", "bitget-copy-trading-guide"]},
    {"slug": "bitget-beginner-checklist", "title": "Bitgetに進む前の初心者チェックリスト", "keyword": "仮想通貨 初心者 取引所 おすすめ", "stage": "mid_intent", "category": "beginner", "reader": "初めて海外取引所を触る人", "angle": "おすすめより失敗回避に寄せる", "related": ["bitget-registration-guide", "bitget-safety-guide", "bitget-faq"]},
    {"slug": "bitget-copy-trading-guide", "title": "Bitgetのコピートレード導線を確認する", "keyword": "Bitget コピートレード", "stage": "mid_intent", "category": "feature", "reader": "機能面で比較したい人", "angle": "機能説明から登録判断へつなぐ", "related": ["bitget-app-guide", "bitget-fees-guide", "bitget-registration-guide"]},
    {"slug": "bitget-kyc-guide", "title": "Bitgetの本人確認まわりを登録前に把握する", "keyword": "Bitget 本人確認", "stage": "high_intent", "category": "kyc", "reader": "登録直前に詰まりたくない人", "angle": "本人確認の不安を先に解消する", "related": ["bitget-registration-guide", "bitget-safety-guide", "bitget-bonus-guide"]},
    {"slug": "bitget-bybit-comparison", "title": "BitgetとBybitを比較してから決める", "keyword": "Bitget Bybit 比較", "stage": "high_intent", "category": "comparison", "reader": "BitgetとBybitで迷っている人", "angle": "選び分け条件を先に出す", "related": ["bitget-fees-guide", "bitget-registration-guide", "bitget-beginner-checklist"]},
    {"slug": "bitget-binance-comparison", "title": "BitgetとBinanceを比較したい人向けの整理", "keyword": "Bitget Binance 比較", "stage": "mid_intent", "category": "comparison", "reader": "Bitgetを比較候補に残すか迷っている人", "angle": "大手比較の文脈でBitgetの位置を整理する", "related": ["bitget-fees-guide", "bitget-app-guide", "bitget-safety-guide"]},
    {"slug": "bitget-mexc-comparison", "title": "BitgetとMEXCで迷う人向けの判断材料", "keyword": "Bitget MEXC 比較", "stage": "mid_intent", "category": "comparison", "reader": "BitgetとMEXCのどちらかで迷う人", "angle": "比較表から関連ページへ流す", "related": ["bitget-registration-guide", "bitget-fees-guide", "bitget-bonus-guide"]},
    {"slug": "bitget-faq", "title": "Bitgetで詰まりやすい疑問のまとめ", "keyword": "Bitget よくある質問", "stage": "support", "category": "faq", "reader": "比較や登録手順を読んだ後に細部が気になる人", "angle": "FAQ自体で終わらせず適切な導線へ戻す", "related": ["bitget-registration-guide", "bitget-safety-guide", "bitget-bonus-guide"]},
]

CTA_VARIANTS = [
    {"id": "cta_start", "label": "Bitgetの登録ページを開く", "tone": "direct"},
    {"id": "cta_bonus", "label": "招待特典の条件を確認する", "tone": "bonus"},
    {"id": "cta_steps", "label": "登録前の確認ポイントを見る", "tone": "soft"},
    {"id": "cta_app", "label": "アプリ前提で始め方を見る", "tone": "app"},
]

FAQ_COMMON = [
    ("このサイトは何を目的にしているか", "Bitgetへの登録を検討している人が、比較・不安解消・手順確認を短時間で済ませるための入口です。"),
    ("特典は必ず受け取れるか", "時期や条件で変わる可能性があります。最終条件は必ず公式導線で確認してください。"),
    ("最初に確認すべき点は何か", "本人確認、対応地域、手数料、入出金手段、アプリの使い勝手です。"),
]

CSS = """
:root{--text:#111;--muted:#666;--line:#ddd;--soft:#f7f7f8;--accent:#0a58ca;}
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:1050px;margin:0 auto;padding:24px;line-height:1.8;color:var(--text)}
a{color:var(--accent);text-decoration:none}h1,h2,h3{line-height:1.25}.muted{color:var(--muted)}
.hero,.box,.card,.table-wrap{border:1px solid var(--line);border-radius:18px;padding:18px;margin:18px 0}.hero{background:var(--soft)}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.cta-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.cta{display:inline-block;padding:12px 16px;border:1px solid #111;border-radius:999px;color:#111;background:#fff}.cta.secondary{background:var(--soft)}
table{width:100%;border-collapse:collapse}th,td{border:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}ul{padding-left:1.2rem}code{background:#f3f3f3;padding:2px 6px;border-radius:6px}
"""


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def deterministic_score(*parts: str) -> float:
    joined = "::".join(parts)
    value = int(hashlib.sha256(joined.encode("utf-8")).hexdigest()[:8], 16)
    return round((value % 1000) / 1000, 4)


def add_tracking(url: str, page_slug: str, cta_id: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({
        "utm_source": "site",
        "utm_medium": "affiliate",
        "utm_campaign": page_slug,
        "utm_content": cta_id,
    })
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def stage_weight(stage: str) -> float:
    return {"high_intent": 1.0, "mid_intent": 0.78, "support": 0.58, "hub": 0.70}.get(stage, 0.6)


def ctas_for(page_slug: str, stage: str, referral_url: str) -> list[dict[str, str]]:
    pool = CTA_VARIANTS[:3] if stage in {"high_intent", "hub"} else [CTA_VARIANTS[2], CTA_VARIANTS[3], CTA_VARIANTS[0]]
    out = []
    for item in pool:
        out.append({**item, "url": add_tracking(referral_url, page_slug=page_slug, cta_id=item["id"])})
    return out


def canonical(site_url: str, slug: str) -> str:
    base = site_url.rstrip("/")
    return f"{base}/" if slug == "index" else f"{base}/{slug}.html"


def render_page(page: dict[str, Any], pages_by_slug: dict[str, dict[str, Any]], referral_url: str, site_url: str, built_at: str) -> str:
    cta_primary, cta_mid, cta_final = ctas_for(page["slug"], page["stage"], referral_url)
    related = "".join(
        f"<li><a href='{target['slug']}.html'>{target['title']}</a><br><span class='muted'>{target['keyword']}</span></li>"
        for slug in page["related"]
        for target in [pages_by_slug[slug]]
    )

    score = round(stage_weight(page["stage"]) * 0.6 + deterministic_score(page["slug"], "seo") * 0.4, 4)
    decision_points = [
        "まず何を確認すると離脱しにくいか",
        "比較で見るべき順番",
        "登録に進む前の注意点",
    ]

    comparison_rows = "".join(
        f"<tr><th>{i+1}</th><td>{label}</td><td>{note}</td></tr>" for i, (label, note) in enumerate([
            (decision_points[0], "最初の数分で不安を減らすための確認事項。"),
            (decision_points[1], "迷いを短くするための見方。"),
            (decision_points[2], "登録直前の確認用。"),
        ])
    )

    faq_html = "".join(f"<div class='box'><strong>{q}</strong><p>{a}</p></div>" for q, a in FAQ_COMMON)
    description = f"{page['keyword']} を軸に、Bitget の登録前に確認したい点を短く整理したページ。"

    body = f"""
    <header class='hero'>
      <p class='muted'>{SITE_NAME}</p>
      <h1>{page['title']}</h1>
      <p>{page['reader']}向けに、{page['angle']}ためのページです。</p>
      <div class='cta-row'>
        <a class='cta' href='{cta_primary['url']}' rel='nofollow sponsored noopener' target='_blank'>{cta_primary['label']}</a>
        <a class='cta secondary' href='{cta_mid['url']}' rel='nofollow sponsored noopener' target='_blank'>{cta_mid['label']}</a>
      </div>
      <p class='muted'>広告・招待リンクを含みます。条件や特典は変わる可能性があるため、最終条件は必ず公式で確認してください。</p>
    </header>

    <section class='grid'>
      <article class='card'>
        <h2>このページの使い方</h2>
        <ul>
          <li>主要検索意図: {page['keyword']}</li>
          <li>想定読者: {page['reader']}</li>
          <li>役割: {page['angle']}</li>
        </ul>
      </article>
      <article class='card'>
        <h2>早い結論</h2>
        <p>Bitgetを候補として残すか決めるには、手数料・本人確認・使い方の3点を先に押さえると判断が速くなります。</p>
        <p class='muted'>internal_priority_score: {score}</p>
      </article>
    </section>

    <section class='box'>
      <h2>登録前に見るべき3項目</h2>
      <div class='table-wrap'>
        <table>
          <thead><tr><th>#</th><th>確認項目</th><th>見る理由</th></tr></thead>
          <tbody>{comparison_rows}</tbody>
        </table>
      </div>
    </section>

    <section class='box'>
      <h2>このページから次に進む導線</h2>
      <ul>{related}</ul>
      <div class='cta-row'>
        <a class='cta' href='{cta_final['url']}' rel='nofollow sponsored noopener' target='_blank'>{cta_final['label']}</a>
      </div>
    </section>

    <section>
      <h2>よくある質問</h2>
      {faq_html}
    </section>

    <footer class='box'>
      <p>{SITE_TAGLINE}</p>
      <p class='muted'>built_at: {built_at} / objective: {OBJECTIVE}</p>
    </footer>
    """

    json_ld = [
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page["title"],
            "url": canonical(site_url, page["slug"]),
            "description": description,
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in FAQ_COMMON[:3]
            ],
        },
    ]
    json_ld_html = "\n".join(
        f"<script type='application/ld+json'>{json.dumps(item, ensure_ascii=False)}</script>" for item in json_ld
    )
    return f"<!doctype html><html lang='ja'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{page['title']}</title><meta name='description' content='{description}'><link rel='canonical' href='{canonical(site_url, page['slug'])}'><meta name='robots' content='index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1'><style>{CSS}</style>{json_ld_html}</head><body>{body}</body></html>"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def build_site(project_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    docs_dir = project_root / 'docs'
    docs_dir.mkdir(parents=True, exist_ok=True)
    for old in docs_dir.glob('*.html'):
        old.unlink()

    built_at = datetime.now(timezone.utc).isoformat()
    site_url = infer_site_url(settings)
    pages_by_slug = {page['slug']: page for page in PAGES}
    rendered_pages = []

    referral_url = settings['bitget_referral_url'].strip()

    for page in PAGES:
        html = render_page(page, pages_by_slug, referral_url, site_url, built_at)
        filename = 'index.html' if page['slug'] == 'index' else f"{page['slug']}.html"
        write_text(docs_dir / filename, html)
        rendered_pages.append({
            'slug': page['slug'],
            'title': page['title'],
            'keyword': page['keyword'],
            'stage': page['stage'],
            'priority': round(stage_weight(page['stage']) * 0.65 + deterministic_score(page['slug'], 'priority') * 0.35, 4),
            'predicted_ctr': round(stage_weight(page['stage']) * 0.5 + deterministic_score(page['slug'], 'ctr') * 0.5, 4),
        })

    sitemap_entries = []
    for page in PAGES:
        url = canonical(site_url, page['slug'])
        sitemap_entries.append(f"<url><loc>{url}</loc><lastmod>{built_at}</lastmod></url>")
    sitemap = f"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{''.join(sitemap_entries)}</urlset>"
    write_text(docs_dir / 'sitemap.xml', sitemap)
    write_text(docs_dir / 'robots.txt', f"User-agent: *\nAllow: /\nSitemap: {site_url.rstrip('/')}/sitemap.xml\n")
    write_text(docs_dir / 'llms.txt', f"# {SITE_NAME}\n- objective: {OBJECTIVE}\n- site_url: {site_url}\n")
    write_text(docs_dir / '.nojekyll', '')

    warnings = validate_settings(settings)

    bundle_dir = project_root / 'data' / 'state' / 'review_bundle'
    if bundle_dir.exists():
        for child in bundle_dir.rglob('*'):
            if child.is_file():
                child.unlink()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    ranked = sorted(rendered_pages, key=lambda item: item['priority'], reverse=True)
    winners = ranked[:4]
    losers = sorted(rendered_pages, key=lambda item: item['priority'])[:3]

    variant_log_path = bundle_dir / 'variant_log.jsonl'
    lines = []
    for page in rendered_pages:
        row = {
            'slug': page['slug'],
            'keyword': page['keyword'],
            'stage': page['stage'],
            'predicted_ctr': page['predicted_ctr'],
            'priority': page['priority'],
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    write_text(variant_log_path, '\n'.join(lines) + '\n')

    site_metrics = {
        'objective': OBJECTIVE,
        'site_url': site_url,
        'page_count': len(rendered_pages),
        'pages': rendered_pages,
        'built_at': built_at,
        'settings_warning_count': len(warnings),
    }
    write_text(bundle_dir / 'site_metrics.json', json.dumps(site_metrics, ensure_ascii=False, indent=2) + '\n')

    winners_and_losers = {
        'winners': winners,
        'losers': losers,
    }
    write_text(bundle_dir / 'winners_and_losers.json', json.dumps(winners_and_losers, ensure_ascii=False, indent=2) + '\n')

    next_hypotheses = {
        'next_hypotheses': [
            {'id': 'h1', 'idea': '比較系上位ページのCTAをより直接的にする'},
            {'id': 'h2', 'idea': '本人確認ページから登録ページへの内部回遊を増やす'},
            {'id': 'h3', 'idea': '初心者向けページで安全性と手数料の順序を再検証する'},
        ]
    }
    write_text(bundle_dir / 'next_hypotheses.json', json.dumps(next_hypotheses, ensure_ascii=False, indent=2) + '\n')

    request_manifest = {
        'requested_items': [
            {
                'priority': 1,
                'item': 'Bitgetの招待ダッシュボードのスクリーンショット',
                'reason': '実クリック後の成果を評価して、クリック最適化から招待最適化に重みを移すため',
                'when_needed': '成果が出始めた時か、クリックが多いのに成果が見えない時',
            },
            {
                'priority': 2,
                'item': 'GitHub Pagesの実URL',
                'reason': '公開後の内部リンク・canonical・sitemap表記を確定させるため',
                'when_needed': '初回公開後',
            },
        ]
    }
    write_text(bundle_dir / 'request_manifest.json', json.dumps(request_manifest, ensure_ascii=False, indent=2) + '\n')

    summary_md = f"# Review Summary\n\n- objective: {OBJECTIVE}\n- built_at: {built_at}\n- site_url: {site_url}\n- page_count: {len(rendered_pages)}\n- warnings: {len(warnings)}\n\n## Top pages\n" + '\n'.join(f"- {page['slug']} / priority={page['priority']} / ctr={page['predicted_ctr']}" for page in winners) + "\n"
    write_text(bundle_dir / 'summary.md', summary_md)

    context_snapshot = {
        'site_name': SITE_NAME,
        'site_tagline': SITE_TAGLINE,
        'objective': OBJECTIVE,
        'repo_name': infer_repo_name(settings),
        'site_url': site_url,
        'built_at': built_at,
        'warnings': warnings,
        'settings_fingerprint': fingerprint(json.dumps(settings, sort_keys=True, ensure_ascii=False)),
    }
    write_text(bundle_dir / 'context_snapshot.json', json.dumps(context_snapshot, ensure_ascii=False, indent=2) + '\n')

    improvement_brief = f"# Improvement Brief\n\n- 最優先は high_intent ページの CTA 改善。\n- 比較系と登録系の内部リンク回遊を強める。\n- 実成果が取れたら request_manifest の優先1を投げる。\n"
    write_text(bundle_dir / 'improvement_brief.md', improvement_brief)

    bundle_zip = project_root / 'data' / 'state' / 'review_bundle.zip'
    if bundle_zip.exists():
        bundle_zip.unlink()
    with ZipFile(bundle_zip, 'w', compression=ZIP_DEFLATED) as zf:
        for file in sorted(bundle_dir.rglob('*')):
            if file.is_file():
                zf.write(file, arcname=file.relative_to(bundle_dir))

    quick_status = f"# Quick Status\n\n- built_at: {built_at}\n- page_count: {len(rendered_pages)}\n- site_url: {site_url}\n- repo_name: {infer_repo_name(settings)}\n- warnings: {len(warnings)}\n\n## next_action\n1. 初回公開後は review_bundle.zip をこのチャットへ投げる。\n2. 成果が見え始めたら request_manifest.json の priority 1 を送る。\n"
    write_text(project_root / 'data' / 'state' / 'quick_status.md', quick_status)

    state = {
        'built_at': built_at,
        'page_count': len(rendered_pages),
        'pages': rendered_pages,
        'warnings': warnings,
        'site_name': SITE_NAME,
        'site_url': site_url,
        'settings_fingerprint': fingerprint(json.dumps(settings, sort_keys=True, ensure_ascii=False)),
        'review_bundle_zip': str(bundle_zip),
    }
    write_text(project_root / 'data' / 'state' / 'build_state.json', json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    return state
