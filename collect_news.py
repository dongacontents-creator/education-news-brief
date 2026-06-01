#!/usr/bin/env python3
"""
매주 월요일 자동 실행:
1. 네이버 뉴스 API로 교육 뉴스 수집
2. Groq(Llama) API로 요약 / 인사이트 / 포인트 생성
3. data/weeks.json에 새 주차 자동 추가
"""

import os, json, re, sys
import xml.etree.ElementTree as ET
import requests
from html import unescape
from groq import Groq
from pathlib import Path
from datetime import date, timedelta

# ── 환경변수 ─────────────────────────────────────────────
NAVER_ID     = os.environ['NAVER_CLIENT_ID']
NAVER_SECRET = os.environ['NAVER_CLIENT_SECRET']
groq_client  = Groq(api_key=os.environ['GROQ_API_KEY'])

# ── 검색 쿼리 정의 ────────────────────────────────────────
QUERIES = [
    # ── 교육부 정책 ──────────────────────────────────────────
    ("교육부 교육과정 정책",           "교육부"),
    ("교육부 초등 중등 고교 정책",     "교육부"),
    ("교육부 AI 디지털교육 정책",      "교육부"),
    ("수능 입시 교육과정 개편",        "교육부"),
    ("초등 교육과정 개편 학교",        "교육부"),

    # ── 교사·학교 현장 ───────────────────────────────────────
    ("교사 처우 수업 현장",            "교육부"),
    ("교사 어려움 고충 학교",          "교육부"),
    ("초등 교사 수업 학교",            "교육부"),
    ("학교폭력 생활지도 교사",         "교육부"),
    ("초등학교 돌봄 방과후",           "교육부"),

    # ── AI·디지털 교육 ───────────────────────────────────────
    ("AI 디지털교과서 현장 활용",      "AI동향"),
    ("학교 AI 활용 수업 학생",         "AI동향"),
    ("생성형AI 학생 교사 활용",        "AI동향"),
    ("AI 교육 부작용 우려 문제",       "AI동향"),
    ("에듀테크 디지털 학습 서비스",    "AI동향"),
    ("교육 AI 챗봇 튜터링 서비스",     "AI동향"),
    ("AI 코딩교육 소프트웨어 학교",    "AI동향"),
    ("디지털교육 플랫폼 학습관리",     "AI동향"),

    # ── 동종업계 경쟁사 ──────────────────────────────────────
    ("아이스크림미디어 아이스크림에듀", "업계동향"),
    ("천재교육 천재교과서",            "업계동향"),
    ("비상교육 비상교과서",            "업계동향"),
    ("미래엔 교과서",                  "업계동향"),
    ("지학사 교과서 교육",             "업계동향"),
    ("금성출판사 교과서",              "업계동향"),
    ("웅진씽크빅 교육",                "업계동향"),
    ("대교 교육 학습",                 "업계동향"),
    ("교원그룹 교원 빨간펜",           "업계동향"),
    ("YBM 교육 콘텐츠",               "업계동향"),
    ("메가스터디 교육",                "업계동향"),
    ("디딤돌 초등 학습",               "업계동향"),
]

# ── RSS 피드 정의 ─────────────────────────────────────────
RSS_FEEDS = [
    {
        "url":             "https://www.korea.kr/rss/dept_moe.xml",
        "source":          "교육부",
        "edu_hint":        "교육부",
        "filter_keywords": None,  # 교육부 전용 피드 → 전량 수집
    },
    {
        "url":             "https://www.korea.kr/rss/pressrelease.xml",
        "source":          "정책브리핑",
        "edu_hint":        "교육부",
        # 전 부처 보도자료 → 교육 관련만 필터링
        "filter_keywords": ["교육", "학교", "교사", "학생", "교육부", "교육청",
                            "입시", "수능", "교과서", "유아", "초등", "중학", "고교",
                            "대학", "직업훈련", "평생교육", "특수교육"],
    },
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
    "교육정책":             "tag-edu-교육정책",
    "교육현장":             "tag-edu-교육현장",
    "AI동향":               "tag-edu-AI동향",
    "교과서시장":           "tag-edu-교과서시장",
    "업계동향":             "tag-edu-업계동향",
    "기타":                 "tag-edu-기타",
}

DOMAIN_MAP = {
    # 주요 전국지 (서브도메인 포함)
    "joongang.co.kr": "중앙일보", "joins.com": "중앙일보",
    "chosun.com": "조선일보", "news.chosun.com": "조선일보", "edu.chosun.com": "조선에듀",
    "biz.chosun.com": "조선비즈", "chosunbiz.com": "조선비즈",
    "tvchosun.com": "TV조선", "news.tvchosun.com": "TV조선", "itchosun.com": "IT조선",
    "donga.com": "동아일보", "hani.co.kr": "한겨레",
    "hankyung.com": "한국경제", "hankookilbo.com": "한국일보",
    "heraldcorp.com": "헤럴드경제", "biz.heraldcorp.com": "헤럴드경제",
    "mk.co.kr": "매일경제", "yonhapnews.co.kr": "연합뉴스",
    "ohmynews.com": "오마이뉴스", "sisain.co.kr": "시사IN",
    "naeil.com": "내일신문", "labortoday.co.kr": "매일노동뉴스",
    "busan.com": "부산일보",
    "newstomato.com": "뉴스토마토", "greened.kr": "녹색경제신문",
    "aitimes.com": "AI타임스", "aitimes.kr": "AI타임스",
    "bloter.net": "블로터", "zdnet.co.kr": "ZDNet코리아",
    "dt.co.kr": "디지털타임스", "inews24.com": "아이뉴스24",
    "edujin.co.kr": "에듀진", "eduinnews.co.kr": "에듀인뉴스",
    "veritas-a.com": "베리타스알파",
    "sbs.co.kr": "SBS", "kbs.co.kr": "KBS", "mbc.co.kr": "MBC", "ytn.co.kr": "YTN",
    # 기존 항목
    "sedaily.com": "서울경제", "mt.co.kr": "머니투데이", "khan.co.kr": "경향신문",
    "etnews.com": "전자신문", "edaily.co.kr": "이데일리", "munhwa.com": "문화일보",
    "seoul.co.kr": "서울신문", "segye.com": "세계일보", "joongdo.co.kr": "중도일보",
    "newsis.com": "뉴시스", "news1.kr": "뉴스1", "newspim.com": "뉴스핌",
    "pressian.com": "프레시안", "mediatoday.co.kr": "미디어오늘", "yna.co.kr": "연합뉴스",
    "fnnews.com": "파이낸셜뉴스", "ddaily.co.kr": "디지털데일리", "ajunews.com": "아주경제",
    "asiae.co.kr": "아시아경제", "etoday.co.kr": "이투데이", "viva100.com": "브릿지경제",
    "enewstoday.co.kr": "이뉴스투데이", "breaknews.com": "브레이크뉴스",
    "newstown.co.kr": "뉴스타운", "platum.kr": "플래텀", "hellot.net": "헬로티",
    "nongmin.com": "농민신문", "hansbiz.co.kr": "한스경제",
    "m-economynews.com": "M이코노미뉴스", "m-i.kr": "매일일보",
    "sportsseoul.com": "스포츠서울", "stnsports.co.kr": "STN스포츠",
    "ibabynews.com": "베이비뉴스", "newslock.co.kr": "뉴스락",
    "gosiweek.com": "피앤피뉴스", "lawissue.co.kr": "법률이슈",
    "christiantoday.co.kr": "크리스천투데이", "kpinews.kr": "KPI뉴스",
    "newsgn.com": "뉴스간보기", "newstnt.com": "뉴스TNT", "ttlnews.com": "TTL뉴스",
    "cwn.kr": "충청와이드뉴스", "siminilbo.co.kr": "시민일보",
    "sisanews24.co.kr": "시사뉴스24", "pointdaily.co.kr": "포인트데일리",
    "shinailbo.co.kr": "신아일보", "beyondpost.co.kr": "비욘드포스트",
    "bzeronews.com": "비제로뉴스", "cctimes.kr": "충청타임즈",
    "ccdailynews.com": "충청데일리뉴스", "ccdn.co.kr": "충청데일리뉴스",
    "expressnews.co.kr": "익스프레스뉴스", "fsnews.co.kr": "FS뉴스",
    "segyenews.com": "세계뉴스", "asiatime.co.kr": "아시아타임스",
    "metroseoul.co.kr": "메트로서울", "daehanilbo.co.kr": "대한일보",
    "chungnamilbo.co.kr": "충남일보", "daejonilbo.com": "대전일보",
    "econonews.co.kr": "이코노뉴스", "hangyo.com": "한국교육신문",
    "edpl.co.kr": "교육플러스", "eduplusnews.com": "에듀플러스",
    "edupress.kr": "에듀프레스", "lecturernews.com": "강사신문",
    "news.unn.net": "한국대학신문", "imaeil.com": "매일신문",
    "yeongnam.com": "영남일보", "kookje.co.kr": "국제신문",
    "kyeonggi.com": "경기일보", "kyeongin.com": "경인일보",
    "incheonilbo.com": "인천일보", "kihoilbo.co.kr": "기호일보",
    "ksilbo.co.kr": "경상일보", "ksmnews.co.kr": "경상매일신문",
    "kyongbuk.co.kr": "경북일보", "gukjenews.com": "국제뉴스",
    "kwnews.co.kr": "강원일보", "kwangju.co.kr": "광주일보",
    "gnmaeil.com": "경남매일", "gndomin.com": "경남도민일보",
    "ggilbo.com": "금강일보", "goodmorningcc.com": "굿모닝충청",
    "gimhaenews.co.kr": "김해뉴스", "knnews.co.kr": "경남신문",
    "domin.co.kr": "제주도민일보", "jemin.com": "제민일보",
    "mediajeju.com": "미디어제주", "jbnews.com": "전북뉴스",
    "jeonmae.co.kr": "전남매일", "jndn.com": "전남도민신문",
    "dkilbo.com": "대경일보", "dynews.co.kr": "동양일보",
    "ulsanpress.net": "울산프레스", "hidomin.com": "경남도민일보",
    "kbsm.net": "KBS부산", "samdailbo.com": "삼일보",
    "ikbn.news": "인천경기방송", "ikbc.co.kr": "KBC광주방송",
    "kgnews.co.kr": "경기뉴스", "gg.newdaily.co.kr": "뉴데일리",
    "koreajoongangdaily.joins.com": "코리아중앙데일리",
    "cstimes.com": "컨슈머타임스", "news.kbs.co.kr": "KBS뉴스",
    "imnews.imbc.com": "MBC뉴스", "news.knn.co.kr": "KNN",
    "jibs.co.kr": "JIBS제주방송", "dgmbc.com": "대구MBC",
    "mbceg.co.kr": "MBC경남", "web.ubc.co.kr": "울산방송",
    "news.ebs.co.kr": "EBS뉴스", "dazabi.com": "다자비",
    # 방송·서브도메인
    "news.sbs.co.kr": "SBS", "biz.sbs.co.kr": "SBS",
    "view.asiae.co.kr": "아시아경제",
    "daily.hankooki.com": "한국일보", "weekly.hankooki.com": "한국일보",
    # 주요 뉴스
    "nocutnews.co.kr": "노컷뉴스", "kmib.co.kr": "국민일보",
    "wikitree.co.kr": "위키트리", "mydaily.co.kr": "마이데일리",
    "newsworker.co.kr": "뉴스워커", "newsworks.co.kr": "뉴스웍스",
    "datanews.co.kr": "데이터뉴스", "starnewskorea.com": "스타뉴스",
    "pinpointnews.co.kr": "핀포인트뉴스", "tfmedia.co.kr": "더팩트",
    "ekn.kr": "에너지경제신문", "g1tv.co.kr": "G1강원민방",
    "dnews.co.kr": "대한경제", "cnbnews.com": "CNB뉴스",
    "newscj.com": "천지일보", "ngonews.kr": "NGO뉴스",
    "jejumaeil.net": "제주매일", "kbmaeil.com": "경북매일",
    "joongboo.com": "중부일보", "mdilbo.com": "무등일보",
    "jjan.kr": "전라일보", "suwonilbo.kr": "수원일보",
    "ccnnews.co.kr": "CCN뉴스",
    # 교육청 공식 사이트
    "sen.go.kr": "서울특별시교육청", "goe.go.kr": "경기도교육청",
    "ice.go.kr": "인천광역시교육청", "pen.go.kr": "부산광역시교육청",
    "dge.go.kr": "대구광역시교육청", "dje.go.kr": "대전광역시교육청",
    "gen.go.kr": "광주광역시교육청", "use.go.kr": "울산광역시교육청",
    "sje.go.kr": "세종특별자치시교육청", "gwe.go.kr": "강원도교육청",
    "cbe.go.kr": "충청북도교육청", "cne.go.kr": "충청남도교육청",
    "jbe.go.kr": "전라북도교육청", "jne.go.kr": "전라남도교육청",
    "gbe.kr": "경상북도교육청", "gne.go.kr": "경상남도교육청",
    "jje.go.kr": "제주특별자치도교육청",
    "korea.kr": "대한민국 정책브리핑",
}

def fetch_rss(url: str) -> list:
    """RSS XML 피드를 파싱해 기사 dict 목록 반환 (Naver API items와 동일한 키 구조)."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter('item'):
            def _t(tag, el=item):
                node = el.find(tag)
                return unescape(node.text or '').strip() if node is not None and node.text else ''
            link = _t('link')
            items.append({
                "title":        _t('title'),
                "link":         link,
                "originallink": link,
                "description":  _t('description'),
                "pubDate":      _t('pubDate'),
            })
        print(f"    RSS 파싱 완료: {len(items)}건 ({url})")
        return items
    except Exception as e:
        print(f"    RSS 수집 실패 ({url}): {e}")
        return []

def strip_tags(html: str) -> str:
    from html import unescape
    return unescape(re.sub(r'<[^>]+>', '', html)).strip()

def _repair_json_line(line):
    m = re.match(r'^(\s*"(?:[^"\\]|\\.)+"\s*:\s*")(.*)', line)
    if not m:
        return line
    prefix, rest = m.group(1), m.group(2)
    result, i = [], 0
    while i < len(rest):
        ch = rest[i]
        if ch == '\\':
            result.append(ch); i += 1
            if i < len(rest): result.append(rest[i])
            i += 1
        elif ch == '"':
            ahead = rest[i+1:].lstrip()
            if not ahead or ahead[0] in ',}]':
                result.append('"'); i += 1
                result.append(rest[i:]); break
            else:
                result.append('\\"'); i += 1
        else:
            result.append(ch); i += 1
    return prefix + ''.join(result)

def load_weeks_json(path):
    text = path.read_text(encoding='utf-8')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fixed = '\n'.join(_repair_json_line(l) for l in text.split('\n'))
        return json.loads(fixed)

def week_info(ref: date | None = None):
    today = ref or date.today()
    mon   = today - timedelta(days=today.weekday())
    sun   = mon + timedelta(days=6)
    wom   = (mon.day - 1) // 7 + 1
    return {
        "date":  f"{mon.strftime('%m.%d')}~{sun.strftime('%m.%d')}",
        "badge": f"{mon.month}월 {wom}주차",
        "start": mon,
        "end":   sun,
    }

def naver_search(query: str, display: int = 100) -> list:
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

WEEKLY_PROMPT = """\
이번 주 수집된 교육 뉴스 {n}건을 바탕으로 이번 주 교육계 흐름을 대표하는 종합 인사이트 3줄을 작성하세요.

기사 제목 목록:
{titles}

규칙:
- 반드시 JSON 배열로만 출력 (```json 불필요)
- 각 항목은 한 문장, 40자 이내
- 이번 주 교육계 전반의 트렌드·흐름을 담을 것
- 특정 기관명보다 주제 중심으로 작성

["...", "...", "..."]"""

def ai_weekly_insight(cards: list) -> list:
    titles = "\n".join(f"- {c['title']}" for c in cards[:30])
    prompt = WEEKLY_PROMPT.format(n=len(cards), titles=titles)
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=256,
        )
        text = completion.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"  주간 인사이트 오류: {e}")
        return []

CARD_PROMPT = """\
다음 교육 뉴스 기사를 분석해 JSON으로 정리하세요.

제목: {title}
내용: {desc}
URL: {url}
edu 힌트: {edu_hint}

규칙:
1. edu_type: 아래 우선순위로 정확히 하나 선택
   ① 기사가 특정 시도교육청에 관한 것이면 해당 교육청 전체 명칭 사용:
      서울특별시교육청 / 경기도교육청 / 인천광역시교육청 / 부산광역시교육청 /
      대구광역시교육청 / 대전광역시교육청 / 광주광역시교육청 / 울산광역시교육청 /
      세종특별자치시교육청 / 강원도교육청 / 충청북도교육청 / 충청남도교육청 /
      전라북도교육청 / 전라남도교육청 / 경상북도교육청 / 경상남도교육청 / 제주특별자치도교육청
   ② 교육부 주도 정책·발표·통계 기사: 교육부
   ③ 에듀테크·교육출판업체(아이스크림·천재·비상·미래엔·YBM 등) 중심 기사: 업계동향
   ④ AI·디지털교육 기술·플랫폼 중심 기사 (특정 기관 없음): AI동향
   ⑤ 위 어디에도 해당 없으면: 교육부
   ※ edu 힌트가 특정 교육청/교육부면 최우선 참고
2. relevant: 아래 기준으로 판단
   true  → 초중고(K-12) 교육 정책·현장·교사·학생·교과서·참고서·에듀테크 관련 기사
            또는 교육출판 동종업계(천재교육·비상교육·미래엔·아이스크림·YBM 등) 관련 기사
            또는 초중고 교육 현장에서 AI 활용·도입·부작용 관련 기사
   false → 다음 중 하나라도 해당하면 반드시 false
            · 교육감 선거·후보·정당·유세 관련
            · 대학교·전문대·사이버대·대학원 중심 기사 (초중고와 무관)
            · 기업 CSR·봉사·기부·행사 홍보성 기사
            · 특정인 시상·표창·임명·취임 기사
            · 교육과 직접 관련 없는 일반 사회·경제·연예·종교·선교 기사
            · 선교·종교·교회 활동, 정치인 유세, 부동산·금융 기사
3. source: 언론사 이름 (간단히)
4. topic: 핵심 주제 2~5글자
5. summary: 2문장 이내 한국어 요약
6. insight: "👉 " 로 시작하는 한 줄 인사이트
7. points: 핵심 포인트 3개 (한 문장씩)
8. keywords: 핵심 주제어 2개 (한글, 띄어쓰기 없이)
   - 기관명(교육부·교육청·학교명·대학명) 절대 금지
   - 정책명·기술명·현안·트렌드 중심으로 (예: AI디지털교과서, 교권보호, 에듀테크, 기초학력)

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

def ai_card(title: str, desc: str, url: str, edu_hint: str) -> dict | None:
    prompt = CARD_PROMPT.format(
        title=title, desc=desc, url=url,
        edu_hint=edu_hint or "없음(자동 분류)",
    )
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
        )
        text = completion.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"  AI 오류: {e}")
        return None

TITLE_BLOCKLIST = [
    # 선거·정치
    "후보", "유세", "선거", "출마", "공약", "당선", "낙선", "교육감",
    # 시상·인사
    "시상", "표창", "수상", "포상", "훈장", "공로상", "임명", "취임",
    # 대학(초중고 외) 관련
    "지방대", "대학원", "총장", "대학교", "입학처", "전문대", "사이버대",
    "테마캠퍼스", "K-MOOC", "무크선도", "AID 전환", "AID 사업",
    "대학 브리핑", "캠퍼스", "과학대", "한의대", "예술대", "기술대",
    # 기업 CSR·행사
    "채용", "기부", "봉사", "체육대회", "체전", "소년체전",
    # 종교·선교
    "선교사", "선교", "교회 이모저모", "목사", "신부", "설교",
    # 비교육 일반 뉴스
    "[오늘 뭐했니?]", "[패트롤]", "[미리보는 이데일리 신문]",
    "다주택", "전월셋값",
]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="", help="YYYY-MM-DD")
    args = parser.parse_args()
    ref_date = date.fromisoformat(args.date) if args.date else None
    data_path = Path("data/weeks.json")
    data = load_weeks_json(data_path)

    seen_urls = {
        card["url"]
        for w in data["weeks"]
        for card in w["cards"]
    }

    last_num = max(int(w["id"][1:]) for w in data["weeks"])
    new_id   = f"w{last_num + 1}"
    info = week_info(ref_date)

    existing = [w for w in data["weeks"] if w["badge"] == info["badge"] and w["date"] == info["date"]]
    if existing:
        print(f"이미 수집된 주차: {info['badge']} ({info['date']}) — 종료")
        sys.exit(0)

    print(f"수집 시작: {new_id} ({info['badge']}) {info['date']}")

    cards    = []
    keywords = []

    for query, edu_hint in QUERIES:
        print(f"  검색: {query}")
        try:
            articles = naver_search(query)
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

            if any(kw in title for kw in TITLE_BLOCKLIST):
                print(f"    → 필터 제외: {title[:40]}")
                continue

            print(f"    처리: {title[:40]}...")
            result = ai_card(title, desc, url, edu_hint)
            if not result or not result.get("relevant"):
                print("    → 관련 없음, 스킵")
                continue

            # 언론사명: ① ⓒ 저작권 표시 → ② 도메인 매핑(서브도메인 포함) → ③ AI 추론값
            copy_match = re.search(r'[ⓒ©]\s*([^,\n]+)', desc)
            if copy_match:
                source = copy_match.group(1).strip()
            else:
                from urllib.parse import urlparse
                _dom = urlparse(url).netloc.replace("www.", "")
                # 정확한 도메인 우선, 없으면 루트 도메인으로 재시도
                source = DOMAIN_MAP.get(_dom)
                if not source:
                    _root = '.'.join(_dom.split('.')[-2:])
                    source = DOMAIN_MAP.get(_root) or result.get("source", "")

            edu_type = result.get("edu_type", "기타")
            tag_cls  = EDU_TAGS.get(edu_type, "tag-edu-기타")

            tags = [{"class": tag_cls, "text": edu_type}]
            if source:
                tags.append({"class": "tag-source", "text": source})
            if result.get("topic"):
                tags.append({"class": "tag-topic", "text": result["topic"]})

            pub = art.get("pubDate", "")
            try:
                from email.utils import parsedate
                t = parsedate(pub)
                pub_str = f"{t[0]}.{t[1]:02d}.{t[2]:02d}" if t else ""
                pub_date = date(t[0], t[1], t[2]) if t else None
            except Exception:
                pub_str = ""
                pub_date = None

            if pub_date and not (info["start"] <= pub_date <= info["end"]):
                print(f"    → 날짜 범위 외 ({pub_str}), 스킵")
                continue

            cards.append({
                "edu":          edu_type,
                "tags":         tags,
                "title":        title,
                "meta":         f"{pub_str} · {source}",
                "summary":      result.get("summary", desc[:100]),
                "insight":      result.get("insight", ""),
                "url":          url,
                "points":       result.get("points", [desc]),
                "lang":         "ko",
                "has_translate": False,
            })

            keywords.extend(result.get("keywords", []))
            print(f"    → 추가 완료 ({edu_type})")

            if len(cards) >= 200:
                print("  카드 200개 도달 — 수집 중단")
                break
        else:
            continue
        break

    # ── RSS 피드 수집 (네이버 API 이후 병렬 처리) ──────────────
    print("\n[RSS 피드 수집 시작]")
    for feed in RSS_FEEDS:
        print(f"  피드: {feed['url']}")
        articles = fetch_rss(feed["url"])
        filter_kws = feed.get("filter_keywords")

        for art in articles:
            url   = art.get("link", "#")
            title = strip_tags(art.get("title", ""))
            desc  = strip_tags(art.get("description", ""))

            if not title or url in seen_urls:
                continue

            # 전 부처 피드는 교육 관련 키워드 포함 기사만 처리
            if filter_kws and not any(kw in title + desc for kw in filter_kws):
                continue

            if any(kw in title for kw in TITLE_BLOCKLIST):
                print(f"    → 필터 제외(RSS): {title[:40]}")
                continue

            seen_urls.add(url)

            pub = art.get("pubDate", "")
            try:
                from email.utils import parsedate
                t = parsedate(pub)
                pub_str  = f"{t[0]}.{t[1]:02d}.{t[2]:02d}" if t else ""
                pub_date = date(t[0], t[1], t[2]) if t else None
            except Exception:
                pub_str, pub_date = "", None

            if pub_date and not (info["start"] <= pub_date <= info["end"]):
                print(f"    → 날짜 범위 외 ({pub_str}), 스킵")
                continue

            print(f"    처리: {title[:40]}...")
            result = ai_card(title, desc, url, feed["edu_hint"])
            if not result or not result.get("relevant"):
                print("    → 관련 없음, 스킵")
                continue

            edu_type = result.get("edu_type", "교육부")
            tag_cls  = EDU_TAGS.get(edu_type, "tag-edu-기타")
            source   = feed["source"]

            tags = [
                {"class": tag_cls,        "text": edu_type},
                {"class": "tag-source",   "text": source},
                {"class": "tag-official", "text": "공식보도자료"},
            ]
            if result.get("topic"):
                tags.append({"class": "tag-topic", "text": result["topic"]})

            cards.append({
                "edu":           edu_type,
                "tags":          tags,
                "title":         title,
                "meta":          f"{pub_str} · {source}",
                "summary":       result.get("summary", desc[:100]),
                "insight":       result.get("insight", ""),
                "url":           url,
                "points":        result.get("points", [desc]),
                "lang":          "ko",
                "has_translate": False,
            })
            keywords.extend(result.get("keywords", []))
            print(f"    → 추가 완료 ({edu_type}, RSS)")

    if not cards:
        print("수집된 뉴스 없음 — 종료")
        sys.exit(0)

    from collections import Counter
    KW_STOPWORDS = {
        "교육부", "교육청", "서울교육청", "경기도교육청", "인천교육청",
        "부산교육청", "대구교육청", "대전교육청", "광주교육청", "울산교육청",
        "세종교육청", "강원교육청", "충북교육청", "충남교육청", "전북교육청",
        "전남교육청", "경북교육청", "경남교육청", "제주교육청",
        "서울특별시교육청", "경기도교육청", "인천광역시교육청",
        "부산광역시교육청", "대구광역시교육청", "대전광역시교육청",
        "광주광역시교육청", "울산광역시교육청", "세종특별자치시교육청",
        "강원도교육청", "충청북도교육청", "충청남도교육청",
        "전라북도교육청", "전라남도교육청", "경상북도교육청",
        "경상남도교육청", "제주특별자치도교육청",
        "학교", "교사", "학생", "교육", "대학", "교원", "지원", "운영",
        "강화", "확대", "추진", "개선", "발전", "시행", "도입", "계획",
    }
    filtered_kw = [
        kw for kw in keywords
        if kw not in KW_STOPWORDS
        and not kw.isascii()   # 영어 단어 제외
        and len(kw) >= 3       # 2글자 이하 제외
    ]
    kw_final = [kw for kw, _ in Counter(filtered_kw).most_common(3)]

    print("  주간 인사이트 생성 중...")
    weekly_insight = ai_weekly_insight(cards)

    new_week = {
        "id":             new_id,
        "badge":          info["badge"],
        "date":           info["date"],
        "keywords":       kw_final,
        "weekly_insight": weekly_insight,
        "cards":          cards,
    }

    data["weeks"].append(new_week)
    data_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n완료: {new_id} ({info['badge']}) — {len(cards)}개 카드 추가")


if __name__ == "__main__":
    main()
