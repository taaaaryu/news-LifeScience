#!/usr/bin/env python3
"""Fetch recent PubMed candidates (real, verified metadata + abstracts)
and build the full prompt file for GitHub Models to write the digest from.
No web browsing / no free-form generation of facts: the model is only
allowed to describe what is present in the candidate list below.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "life-science-digest"
EMAIL = "taruu6109@gmail.com"

QUERIES = [
    '(immunology OR immunity OR "immune cell" OR "T cell" OR "innate immune") AND (mice OR mouse OR murine)',
    '("functional morphology" OR morphogenesis OR histology OR "tissue architecture") AND (mice OR mouse OR murine OR human)',
]


def esearch(query, reldate):
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": "15",
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
                doi = eid.text
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


def collect_candidates():
    seen = set()
    ordered_ids = []
    for reldate in (5, 10, 21):
        for q in QUERIES:
            for pmid in esearch(q, reldate):
                if pmid not in seen:
                    seen.add(pmid)
                    ordered_ids.append(pmid)
            time.sleep(0.4)
        if len(ordered_ids) >= 8:
            break
    return ordered_ids[:30]


def main():
    ids = collect_candidates()
    details = efetch_details(ids)

    entries = []
    for pmid in ids:
        d = details.get(pmid)
        if not d or not d["abstract"]:
            continue
        entries.append(
            f"### PMID {d['pmid']}\n"
            f"タイトル: {d['title']}\n"
            f"雑誌・日付: {d['journal']} ({d['date']})\n"
            f"著者: {d['authors']}\n"
            f"DOI: {d['doi'] or '不明'}\n"
            f"リンク: {d['url']}\n"
            f"アブストラクト: {d['abstract']}\n"
        )

    candidates_text = "\n---\n".join(entries) if entries else "(該当候補なし。今日は配信をスキップしてよい)"

    jst_date = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")

    persona = f"""あなたは生命科学の「毎朝ダイジェスト」を作成するエージェントです。
対象読者は、農学部の博士課程学生。専門はマウスを中心とした動物免疫学・機能形態学で、ヒトの免疫学にも一定の知識がある。
物理学（光学・分光・工学的な測定原理など）は苦手なので、手法解説で物理が絡む場合は数式や専門的な物理用語を避け、身近な例えを使って平易に説明すること。

# 絶対条件（最重要・厳守）
- 以下の「候補リスト」に書かれている情報（タイトル・著者・雑誌・日付・DOI・アブストラクト）だけを使う。候補リストに書かれていない具体的な数値・手法の詳細・結論を創作しない。
- アブストラクトに書かれていない情報は無理に埋めず「アブストラクトに記載なし」と明記する。
- 候補リストにない論文は一切紹介しない。DOIやリンクは候補リストに記載のものをそのまま使う（自分で作らない）。

# タスク
候補リストの中から、新規性・研究のたねになる度合いを基準にちょうど3件を選ぶ。マウスモデルを用いた研究を優先してよい（ヒト免疫の研究も歓迎）。候補が薄い場合は、初学者向けの基礎知識解説に使えそうな候補を1件選んでもよい。

# 各項目に書くこと
1. タイトル（日本語訳＋原題）と 掲載先・日付
2. 何が新しいか: 従来と比べ何が分かった/できるようになったか（1〜3文、アブストラクトの範囲で）
3. 手法（どうやったか）: アブストラクトに記載された実験・解析手法を具体的に。マウス実験であれば系統・モデル名などアブストラクトに書かれていれば触れる。手法の一般原理も1〜2文添えるが、光学・分光・物理的な仕組み（レーザー・波長・光子など）が絡む場合は数式や専門的な物理用語を使わず、身近な例えで平易に説明する。読者は生物実験手法には慣れているが物理は苦手という前提で書く。
4. なぜ重要か / 研究のたね: この学生の研究（マウスモデル中心）にどうつながりうるか
5. リンク（候補リストに記載のURL・DOIをそのまま使う）

# 出力形式
- 日本語。朝に数分で読める簡潔な分量。Markdown。
- 冒頭に `# 生命科学 毎朝ダイジェスト（{jst_date}）` という見出しと、選んだ3件を総括する「今日の一言」を1段落で書く。
- そのあとに `---` 区切り線、続けて `## 1. …` `## 2. …` `## 3. …` の3項目。
- 前置きや後書きの雑談、コードフェンス（```）は書かない。Markdown本文のみを出力する。

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
