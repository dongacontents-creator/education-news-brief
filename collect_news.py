#!/usr/bin/env python3
"""
매주 월요일 자동 실행:
1. 네이버 뉴스 API로 교육 뉴스 수집
2. Gemini API로 요약 / 인사이트 / 포인트 생성
3. data/weeks.json에 새 주차 자동 추가
"""

import os, json, re, sys
import requests
from google import genai
from pathlib import Path
from datetime import date, timedelta

# ── 환경변수 ─────────────────────────────────────────────
NAVER_ID     = os.environ['NAVER_CLIENT_ID']
NAVER_SECRET = os.environ['NAVER_CLIENT_SECRET']
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options={'api_version': 'v1'})

# ── 검색 쿼리 정의 ────────────────────────────────────────
QUERIES = [
    ("교육부 교육정책",           "교육부"),
    ("교육부 AI 디지털교육",      "교육부"),
    ("서울교육청",                "서울특별시교육청"),
    ("경기도교육청",              "경기도교육청"),
    ("인천교육청",                "인천광역시교육청"),
    ("부산교육청",                "부산광역시교육청"),
    ("대구교육청",                "대구광역시교육청"),
    ("대전교육청",                "대전광역시교육청"),
    ("광주교육청",                "광주광역시교육청"),
    ("울산교육청",                "울산광역시교육청"),
    ("세종교육청",                "세종특별자치시교육청"),
    ("강원교육청",                "강원도교육청"),
    ("충북교육청",                "충청북도교육청"),
    ("충남교육청",                "충청남도교육청"),
    ("전북교육청",                "전라북도교육청"),
    ("전남교육청",                "전라남도교육청"),
    ("경북교육청",                "경상북도교육청"),
    ("경남교육청",                "경상남도교육청"),
    ("제주교육청",                "제주특별자치도교육청"),
    ("에듀테크 교육 스타트업",    "업계동향"),
    ("AI 교과서 디지털교육",      "업계동향"),
]

EDU_TAGS = {
    "교육부":               "tag-edu-교육부",
    "서울특별시교육청":     "tag-edu-서울특별시교육청",
    "경기도교육청":         "tag-edu-경기도교육청",
    "인천광역시교육청":     "tag-edu-인천광역시교육청",
    "부산광역시교육청":     "tag-edu-부산광역시교육청",
    "대구광역시교육청":     "tag-edu-대구광역시교육청",
    "대전광역시교육청":     "tag-edu-대전광역시교육청",
    "광주광역시교육청":     "tag-edu-광주광역시교육청",
    "울산광역시교육청":     "tag-edu-울산광역시교육청",
    "세종특별자치시교육청": "tag-edu-세종특별자치시교육청",
    "강원도교육청":         "tag-edu-강원도교육청",
    "충청북도교육청":       "tag-edu-충청북도교육청",
    "충청남도교육청":       "tag-edu-충청남도교육청",
    "전라북도교육청":       "tag-edu-전라북도교육청",
    "전라남도교육청":       "tag-edu-전라남도교육청",
    "경상북도교육청":       "tag-edu-경상북도교육청",
    "경상남도교육청":       "tag-edu-경상남도교육청",
    "제주특별자치도교육청": "tag-edu-제주특별자치도교육청",
    "업계동향":             "tag-edu-업계동향",
    "기타":                 "tag-edu-기타",
}

def strip_tags(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html).strip()

def week_info(ref: date | None = None):
    today = ref or date.today()
    mon   = today - timedelta(days=today.weekday())
    sun   = mon + timedelta(days=6)
    wom   = (mon.day - 1) // 7 + 1
    return {
        "date":  f"{mon.strftime('%m.%d')}~{sun.strftime('%m.%d')}",
        "badge": f"{mon.month}월 {wom}주차",
    }

def naver_search(query: str, display: int = 5) -> list:
    resp = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        headers={
            "X-Naver-Client-Id":     NAVER_ID,
            "X-Naver-Client-Secret": NAVER_SECRET,
        },
        params={"query": query, "display": display, "sort": "date"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])

CARD_PROMPT = """\
다음 교육 뉴스 기사를 분석해 JSON으로 정리하세요.

제목: {title}
내용: {desc}
URL: {url}
edu 힌트: {edu_hint}

규칙:
1. edu_type: 아래 중 정확히 하나 선택
   교육부 / 서울특별시교육청 / 경기도교육청 / 인천광역시교육청 /
   부산광역시교육청 / 대구광역시교육청 / 대전광역시교육청 /
   광주광역시교육청 / 울산광역시교육청 / 세종특별자치시교육청 /
   강원도교육청 / 충청북도교육청 / 충청남도교육청 / 전라북도교육청 /
   전라남도교육청 / 경상북도교육청 / 경상남도교육청 /
   제주특별자치도교육청 / 업계동향 / 기타
2. relevant: 교육 관련 기사면 true, 아니면 false
3. source: 언론사 이름 (간단히)
4. topic: 핵심 주제 2~5글자
5. summary: 2문장 이내 한국어 요약
6. insight: "👉 " 로 시작하는 한 줄 인사이트
7. points: 핵심 포인트 3개 (한 문장씩)
8. keywords: 대표 키워드 2개 (한글, 띄어쓰기 없이)

JSON만 출력 (```json 불필요):
{{
  "relevant": true,
  "edu_type": "...",
  "source": "...",
  "topic": "...",
  "summary": "...",
  "insight": "👉 ...",
  "points": ["...", "...", "..."],
  "keywords": ["...", "..."]
}}"""

def gemini_card(title: str, desc: str, url: str, edu_hint: str) -> dict | None:
    prompt = CARD_PROMPT.format(
        title=title, desc=desc, url=url,
        edu_hint=edu_hint or "없음(자동 분류)",
    )
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"  Gemini 오류: {e}")
        return None

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="", help="YYYY-MM-DD")
    args = parser.parse_args()
    ref_date = date.fromisoformat(args.date) if args.date else None
    data_path = Path("data/weeks.json")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    seen_urls = {
        card["url"]
        for w in data["weeks"]
        for card in w["cards"]
    }

    last_num = max(int(w["id"][1:]) for w in data["weeks"])
    new_id   = f"w{last_num + 1}"
    info = week_info(ref_date)

    print(f"수집 시작: {new_id} ({info['badge']}) {info['date']}")

    cards    = []
    keywords = []

    for query, edu_hint in QUERIES:
        print(f"  검색: {query}")
        try:
            articles = naver_search(query, display=4)
        except Exception as e:
            print(f"  검색 실패: {e}")
            continue

        for art in articles:
            url   = art.get("originallink") or art.get("link", "#")
            title = strip_tags(art.get("title", ""))
            desc  = strip_tags(art.get("description", ""))

            if url in seen_urls:
                continue
            seen_urls.add(url)

            print(f"    처리: {title[:40]}...")
            result = gemini_card(title, desc, url, edu_hint)
            if not result or not result.get("relevant"):
                print("    → 관련 없음, 스킵")
                continue

            edu_type = result.get("edu_type", "기타")
            tag_cls  = EDU_TAGS.get(edu_type, "tag-edu-기타")

            tags = [{"class": tag_cls, "text": edu_type}]
            if result.get("source"):
                tags.append({"class": "tag-source", "text": result["source"]})
            if result.get("topic"):
                tags.append({"class": "tag-topic", "text": result["topic"]})

            pub = art.get("pubDate", "")
            try:
                from email.utils import parsedate
                t = parsedate(pub)
                pub_str = f"{t[0]}.{t[1]:02d}.{t[2]:02d}" if t else ""
            except Exception:
                pub_str = ""

            cards.append({
                "edu":          edu_type,
                "tags":         tags,
                "title":        title,
                "meta":         f"{pub_str} · {result.get('source', '')}",
                "summary":      result.get("summary", desc[:100]),
                "insight":      result.get("insight", ""),
                "url":          url,
                "points":       result.get("points", [desc]),
                "lang":         "ko",
                "has_translate": False,
            })

            keywords.extend(result.get("keywords", []))
            print(f"    → 추가 완료 ({edu_type})")

    if not cards:
        print("수집된 뉴스 없음 — 종료")
        sys.exit(0)

    seen_kw  = set()
    kw_final = []
    for kw in keywords:
        if kw not in seen_kw:
            seen_kw.add(kw)
            kw_final.append(kw)
        if len(kw_final) == 3:
            break

    new_week = {
        "id":       new_id,
        "badge":    info["badge"],
        "date":     info["date"],
        "keywords": kw_final,
        "cards":    cards,
    }

    data["weeks"].append(new_week)
    data_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n완료: {new_id} ({info['badge']}) — {len(cards)}개 카드 추가")


if __name__ == "__main__":
    main()
