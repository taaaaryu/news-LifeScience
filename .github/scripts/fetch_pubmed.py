#!/usr/bin/env python3
"""Fetch recent PubMed candidates and build the digest-generation prompt.

The script is the source of truth for daily digest selection rules. It keeps
candidate facts grounded in PubMed metadata/abstracts and excludes papers that
were already introduced recently.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "life-science-digest"
EMAIL = "taruu6109@gmail.com"
JST = ZoneInfo("Asia/Tokyo")

QUERIES = [
    '(immunology OR immunity OR "immune cell" OR "T cell" OR "innate immune") AND (mice OR mouse OR murine)',
    '("functional morphology" OR morphogenesis OR histology OR "tissue architecture") AND (mice OR mouse OR murine OR human)',
]
LOOKBACK_DAYS = (5, 10, 21)
RECENT_DUPLICATE_DAYS = 30
MAX_ABSTRACT_CHARS = 1800
MAX_CANDIDATES = 18

# One primary category per paper. Keep this taxonomy stable so weekly summaries
# can count papers consistently across days.
CATEGORY_TAXONOMY = [
    "免疫制御・炎症",
    "感染・ワクチン",
    "腫瘍免疫",
    "粘膜・アレルギー・微生物叢",
    "機能形態・発生",
]


def esearch(query, reldate):
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": "20",
        "sort": "date",
        "datetype": "pdat",
        "reldate": str(reldate),
        "retmode": "json",
        "tool": TOOL,
        "email": EMAIL,
    }
    url = f"{EUTILS}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    return data.get("esearchresult", {}).get("idlist", [])


def efetch_details(pmids):
    if not pmids:
        return {}
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
        "tool": TOOL,
        "email": EMAIL,
    }
    url = f"{EUTILS}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        xml_bytes = r.read()
    root = ET.fromstring(xml_bytes)
    results = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else None
        if not pmid:
            continue
        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""
        year_el = article.find(".//JournalIssue/PubDate/Year")
        medline_date_el = article.find(".//JournalIssue/PubDate/MedlineDate")
        date_str = (
            year_el.text
            if year_el is not None
            else (medline_date_el.text if medline_date_el is not None else "")
        )
        author_els = article.findall(".//AuthorList/Author")
        authors = []
        for author in author_els[:3]:
            last = author.find("LastName")
            fore = author.find("ForeName")
            if last is not None:
                name = last.text
                if fore is not None:
                    name = f"{fore.text} {name}"
                authors.append(name)
        author_str = ", ".join(authors) + (" ほか" if len(author_els) > 3 else "")
        abstract_parts = []
        for ab in article.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            text = "".join(ab.itertext()).strip()
            abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(p for p in abstract_parts if p).strip()
        doi = ""
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = (eid.text or "").strip()
        results[pmid] = {
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "date": date_str,
            "authors": author_str,
            "abstract": abstract,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
    return results


def recent_digest_files(days=RECENT_DUPLICATE_DAYS):
    digest_dir = Path("digests")
    if not digest_dir.exists():
        return []
    cutoff = datetime.now(JST).date() - timedelta(days=days)
    files = []
    for path in digest_dir.glob("????-??-??.md"):
        try:
            file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date >= cutoff:
            files.append(path)
    return sorted(files)


def load_recent_published_ids(days=RECENT_DUPLICATE_DAYS):
    pmids = set()
    dois = set()
    for path in recent_digest_files(days):
        text = path.read_text(encoding="utf-8")
        pmids.update(re.findall(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?", text))
        for doi in re.findall(r"(?im)^\s*(?:\*\*)?DOI(?:\*\*)?\s*[:：]\s*([^\s]+)", text):
            dois.add(doi.strip().rstrip(".,;)").lower())
    return pmids, dois


def collect_candidates():
    recent_pmids, _ = load_recent_published_ids()
    seen = set(recent_pmids)
    ordered_ids = []
    source_query = {}

    for reldate in LOOKBACK_DAYS:
        for query_index, query in enumerate(QUERIES):
            for pmid in esearch(query, reldate):
                if pmid in seen:
                    continue
                seen.add(pmid)
                ordered_ids.append(pmid)
                source_query[pmid] = "immunology" if query_index == 0 else "morphology"
            time.sleep(0.4)
        # A slightly larger pool than before helps preserve the default 2:1 topic balance.
        if len(ordered_ids) >= 12:
            break
    return ordered_ids[:MAX_CANDIDATES], source_query


def main():
    ids, source_query = collect_candidates()
    details = efetch_details(ids)
    _, recent_dois = load_recent_published_ids()

    entries = []
    for pmid in ids:
        d = details.get(pmid)
        if not d or not d["abstract"]:
            continue
        if d["doi"] and d["doi"].lower() in recent_dois:
            continue
        abstract = d["abstract"]
        if len(abstract) > MAX_ABSTRACT_CHARS:
            abstract = abstract[:MAX_ABSTRACT_CHARS] + "…"
        entries.append(
            f"### PMID {d['pmid']}\n"
            f"検索系統: {source_query.get(pmid, 'unknown')}\n"
            f"タイトル: {d['title']}\n"
            f"雑誌・日付: {d['journal']} ({d['date']})\n"
            f"著者: {d['authors']}\n"
            f"DOI: {d['doi'] or '不明'}\n"
            f"リンク: {d['url']}\n"
            f"アブストラクト: {abstract}\n"
        )
        if len(entries) >= 15:
            break

    candidates_text = "\n---\n".join(entries) if entries else "(該当候補なし。今日は配信をスキップしてよい)"
    jst_date = datetime.now(JST).strftime("%Y-%m-%d")
    categories = " / ".join(CATEGORY_TAXONOMY)

    persona = f"""あなたは生命科学の「毎朝ダイジェスト」を作成するエージェントです。
対象読者は、農学部の博士課程学生。専門はマウスを中心とした動物免疫学・機能形態学で、ヒトの免疫学にも一定の知識がある。
物理学（光学・分光・工学的な測定原理など）は苦手なので、手法解説で物理が絡む場合は数式や専門的な物理用語を避け、必要なときだけ平易に説明すること。

# 絶対条件（最重要・厳守）
- 以下の「候補リスト」に書かれている情報（PMID・タイトル・著者・雑誌・日付・DOI・リンク・アブストラクト）だけを使う。候補リストにない具体的な数値・手法の詳細・結論を創作しない。
- アブストラクトに書かれていない情報は無理に埋めず「アブストラクトに記載なし」と明記する。
- 候補リストにない論文は一切紹介しない。DOIやリンクは候補リストのものをそのまま使う。
- 直近{RECENT_DUPLICATE_DAYS}日の日次digestに登場したPMID/DOIは候補から除外済み。過去配信と重複する論文を再紹介しない。

# 選定
- 十分な候補があればちょうど3件を選ぶ。
- 基本バランスは「免疫系2件 + 機能形態・発生系1件」。ただし弱い論文を数合わせで採用せず、その日の候補の質を優先してよい。
- 新規性、マウスモデルとの関連、実験設計として持ち帰れる点を重視する。
- 同じ疾患・同じ細胞種・同じ手法に3件が偏りすぎないようにする。

# カテゴリ
各論文に、次の固定カテゴリから最も近いものを1つだけ付ける：
{categories}
カテゴリはWeekly集計に使うので表記を変えない。

# 各項目に書くこと
1. タイトル（日本語訳＋原題）、掲載先・日付、著者、カテゴリ
2. 何が新しいか：従来と比べ何が分かった/できるようになったか。1〜3文。アブストラクトの範囲だけ。
3. 手法（どうやったか）：アブストラクトに記載された実験・解析手法を具体的に。マウス系統・モデル名が書かれていれば触れる。一般原理の説明は必要な場合だけ。
4. 実験設計メモ：この論文からマウス実験・機能形態学へ持ち帰れる具体的な設計上の1点を1〜2文で書く。抽象的な「重要」「参考になる」「応用できる」で埋めない。特に持ち帰る点がなければ「特記なし」でよい。
5. PMID、PubMedリンク、DOIを候補リストどおり記載する。

# 文体
- knowledgeableな研究室メンバーが朝に同僚へ渡す短いメモの日本語。
- 定型的な導入・結びを避ける。「〜と言えるでしょう」「〜が期待されます」「非常に興味深い」「注目すべき」「重要な示唆を与える」「研究のたねになりそうです」は原則使わない。
- タイトルを本文1文目で言い換えて繰り返さない。
- 同じ文型、同じ締め方を3本で反復しない。
- 具体的に、何を測った・比較した・変わった・観察したかを書く。
- 技術用語は読者が知っているものなら普通に使い、過剰説明しない。
- エビデンスが限定的なら、その限界を短く明記する。
- 太字を増やしすぎない。

# 出力形式
- 日本語、Markdown、朝に数分で読める分量。
- 冒頭は `# 生命科学 毎朝ダイジェスト（{jst_date}）`。
- 「今日の一言」は、本当に3本に共通する軸がある場合だけ1段落でまとめる。共通軸が弱ければ、3本の内容を短く並べるだけでよい。無理に物語を作らない。
- `---` の後に `## 1. …` `## 2. …` `## 3. …`。
- 各論文のメタデータ内に必ず `**カテゴリ:** <固定カテゴリ名>` と `**PMID:** <PMID>` を入れる。
- セクション見出しは `### 何が新しいか` `### 手法（どうやったか）` `### 実験設計メモ`。
- 前置き・後書きの雑談、コードフェンスは書かない。

# 候補リスト
{candidates_text}
"""

    with open("/tmp/prompt.txt", "w", encoding="utf-8") as f:
        f.write(persona)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"date={jst_date}\n")
            f.write(f"candidate_count={len(entries)}\n")
    else:
        print(f"date={jst_date}")
        print(f"candidate_count={len(entries)}")


if __name__ == "__main__":
    main()
