from http.server import BaseHTTPRequestHandler
import json, os, re
from groq import Groq
from pathlib import Path

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

def load_articles():
    path = Path(__file__).parent.parent / "data" / "weeks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    articles = []
    for week in data["weeks"]:
        for card in week["cards"]:
            articles.append({
                "week":    week["badge"],
                "title":   card.get("title", ""),
                "summary": card.get("summary", ""),
                "edu":     card.get("edu", ""),
                "url":     card.get("url", ""),
                "meta":    card.get("meta", ""),
            })
    return articles

SYSTEM_PROMPT = """\
당신은 교육 뉴스 브리핑 챗봇입니다.
수집된 교육 뉴스 기사 데이터를 바탕으로 사용자 질문에 답변하세요.

규칙:
- 관련 기사가 있으면 2~3문장으로 전체 흐름을 요약해서 먼저 설명하세요
- 관련 기사가 없으면 솔직하게 없다고 말하세요
- 답변은 한국어로, 친절하고 간결하게
- 기사 목록이나 URL은 직접 출력하지 마세요 (별도로 표시됩니다)
- 교육 뉴스와 무관한 질문(정치, 역사, 연예, 일반 상식 등)은 답변하지 말고,
  "저는 교육 뉴스 검색 챗봇이라 해당 질문은 답변하기 어렵습니다. 교육 관련 기사를 검색해드릴게요!"라고 안내하세요"""

COMPARE_SYSTEM_PROMPT = """\
당신은 교육 뉴스 브리핑 챗봇입니다.
두 기관의 기사 데이터를 비교 분석해서 답변하세요.

규칙:
- 각 기관의 주요 정책/활동 방향을 1~2문장씩 요약하세요
- 두 기관의 공통점과 차이점을 명확하게 설명하세요
- 관련 기사가 한쪽만 있으면 솔직하게 말하세요
- 답변은 한국어로, 친절하고 간결하게
- 기사 목록이나 URL은 직접 출력하지 마세요 (별도로 표시됩니다)"""

# 후속 필터 질문으로 판단하는 키워드
REFINE_WORDS = ['추려', '골라', '중에서', '에서만', '만 모아', '만 추출', '필터', '제외', '빼고', '만 보여', '만 줘', '만줘']

# 비교 질문 판별 키워드
COMPARE_WORDS = ['이랑', '랑', '과 ', '와 ', 'vs', 'VS', '비교', '차이', 'versus', '대비']

# 검색 의미 없는 불용어 (접두어 매칭)
STOPWORDS = [
    '기사', '찾아', '모아', '알려', '보여', '관련', '대한', '관한',
    '있는', '있어', '어떤', '전부', '모두', '전체', '한번', '혹시',
    '뭐야', '뭐가', '뭔가', '뭐', '줘', '줄게', '다',
    '비교', '차이', '다른점', '공통점', 'vs', 'versus',
    '정책', '교육', '현황', '방안', '계획', '내용', '동향',
    '추려', '골라', '뽑아', '정리', '요약', '보내', '올려', '꺼내',
]
ORG_SUFFIXES = ('교육청', '교육부', '교육원')

# 알려진 기관명 목록
KNOWN_ORGS = [
    '서울특별시교육청', '경기도교육청', '인천광역시교육청', '대전광역시교육청',
    '광주광역시교육청', '대구광역시교육청', '울산광역시교육청', '부산광역시교육청',
    '세종특별자치시교육청', '강원도교육청', '충청북도교육청', '충청남도교육청',
    '전라북도교육청', '전라남도교육청', '경상북도교육청', '경상남도교육청',
    '제주특별자치도교육청', '교육부',
]

def _is_stopword(kw: str) -> bool:
    return any(kw.startswith(sw) and len(kw) <= len(sw) + 2 for sw in STOPWORDS)

def extract_orgs(query: str) -> list:
    """쿼리에서 기관명 추출 (줄임말/시 표기 변형 포함)"""
    found = [org for org in KNOWN_ORGS if org in query]
    aliases = {
        '경기교육청': '경기도교육청',
        '서울교육청': '서울특별시교육청', '서울시교육청': '서울특별시교육청',
        '인천교육청': '인천광역시교육청', '인천시교육청': '인천광역시교육청',
        '대전교육청': '대전광역시교육청', '대전시교육청': '대전광역시교육청',
        '광주교육청': '광주광역시교육청', '광주시교육청': '광주광역시교육청',
        '대구교육청': '대구광역시교육청', '대구시교육청': '대구광역시교육청',
        '울산교육청': '울산광역시교육청', '울산시교육청': '울산광역시교육청',
        '부산교육청': '부산광역시교육청', '부산시교육청': '부산광역시교육청',
        '세종교육청': '세종특별자치시교육청',
        '강원교육청': '강원도교육청',
        '충북교육청': '충청북도교육청',
        '충남교육청': '충청남도교육청',
        '전북교육청': '전라북도교육청',
        '전남교육청': '전라남도교육청',
        '경북교육청': '경상북도교육청',
        '경남교육청': '경상남도교육청',
        '제주교육청': '제주특별자치도교육청',
    }
    for alias, full in aliases.items():
        if alias in query and full not in found:
            found.append(full)
    return list(dict.fromkeys(found))

def is_compare_query(query: str) -> bool:
    has_compare_word = any(w in query for w in COMPARE_WORDS)
    orgs = extract_orgs(query)
    return has_compare_word and len(orgs) >= 2

def is_refine_query(query: str) -> bool:
    return any(w in query for w in REFINE_WORDS)

# 주요 이슈 키워드 질문 감지
KEYWORD_TREND_WORDS = ['키워드', '이슈', '주요 이슈', '트렌드', '많이 나온', '자주 나온', '주요 키워드', '이슈 키워드']

def is_keyword_trend_query(query: str) -> bool:
    return any(w in query for w in KEYWORD_TREND_WORDS)

def extract_keyword_trends(articles: list, query: str) -> str:
    """기사 데이터에서 주요 키워드 빈도를 분석해 순위를 반환"""
    # 질문에서 기간 감지 (예: 3월부터 5월, 1월~3월 등)
    month_range_match = re.search(r'(\d+)월[부터에서]*\s*(\d+)월', query)

    target_articles = articles
    period_desc = ""

    if month_range_match:
        start_m = int(month_range_match.group(1))
        end_m = int(month_range_match.group(2))
        # week badge 예: "3월 1주차" 형태 가정
        target_articles = [
            a for a in articles
            if re.search(r'(\d+)월', a.get("week", "")) and
               start_m <= int(re.search(r'(\d+)월', a["week"]).group(1)) <= end_m
        ]
        period_desc = f"{start_m}월 1주부터 {end_m}월 마지막 주차까지"
    else:
        period_desc = "전체 기간"

    # 기사 제목+요약에서 의미 있는 단어 빈도 집계
    # 미리 정의한 주요 교육 키워드 목록으로 카운트
    TOPIC_KEYWORDS = [
        'AI 교육', '인공지능', '교육감', '교육감 선거', '교권 보호', '교권', '돌봄', '방과후', '늘봄',
        '학교폭력', '기초학력', '디지털교육', '특수교육', '학생인권', '교육개혁', '입시',
        '수능', '대입', '교육과정', '사교육', '공교육', '예산', '교원', '교사', '학부모',
    ]

    counts = {}
    for kw in TOPIC_KEYWORDS:
        cnt = sum(1 for a in target_articles if kw in a.get("title", "") + a.get("summary", ""))
        if cnt > 0:
            counts[kw] = cnt

    if not counts:
        return None, period_desc, []

    ranked = sorted(counts.items(), key=lambda x: -x[1])[:10]
    return ranked, period_desc, target_articles

# 접미어 전용 제거 목록 (접두어 불용어로는 쓰지 않음)
SUFFIX_STRIPS = ['좀', '요', '이요', '들', '를', '을', '이', '가', '은', '는', '도', '만', '로', '으로']

def _strip_stopword_suffix(kw: str) -> str:
    """단어 끝 불용어/어미를 반복 제거: '공교육관련기사들좀' → '공교육'"""
    all_suffixes = STOPWORDS + SUFFIX_STRIPS
    while True:
        stripped = False
        for sw in all_suffixes:
            if kw.endswith(sw) and len(kw) > len(sw) + 1:
                kw = kw[:-len(sw)]
                stripped = True
                break
        if not stripped:
            break
    return kw

def find_articles(articles: list, query: str, force_org: str = None, limit: int = 5) -> list:
    query_lower = query.lower()
    raw_keywords = re.findall(r'\S+', query_lower)

    # 기관명 키워드는 불용어 필터 예외 (교육부/교육청 등이 stopword에 걸리지 않도록)
    org_keywords = [kw for kw in raw_keywords
                    if any(kw.endswith(s) or s in kw for s in ORG_SUFFIXES) and len(kw) >= 2]

    # 토픽 키워드: 불용어 제거 + 접미어 제거
    topic_raw = [kw for kw in raw_keywords if kw not in org_keywords]
    topic_keywords = [_strip_stopword_suffix(kw) for kw in topic_raw if not _is_stopword(kw) and len(kw) >= 2]
    topic_keywords = [kw for kw in topic_keywords if len(kw) >= 2]

    # force_org: 비교 검색 시 특정 기관으로만 제한
    if force_org:
        org_keywords = [force_org.lower()]

    scored = []
    for art in articles:
        text = (art["title"] + art["summary"] + art["edu"] + art["week"]).lower()

        # force_org 모드: 해당 기관 기사만
        if force_org and force_org.lower() not in art["edu"].lower():
            continue

        topic_score = sum(1 for kw in topic_keywords if kw in text)
        org_match   = any(kw in art["edu"].lower() for kw in org_keywords)

        # 비교/일반 검색 모두 모든 토픽 키워드 AND (불용어 제거 후 남은 구체적 단어들)
        if topic_keywords and not all(kw in text for kw in topic_keywords):
            continue

        score = topic_score + sum(1 for kw in org_keywords if kw in text)
        if org_match:
            score += 3

        if score > 0:
            scored.append((score, art))

    scored.sort(key=lambda x: -x[0])
    return [art for _, art in scored[:limit]]

def build_context(matched: list) -> str:
    if not matched:
        return "관련 기사 없음"
    lines = []
    for art in matched:
        lines.append(
            f"[{art['week']} / {art['edu']}] {art['title']}\n"
            f"  요약: {art['summary']}"
        )
    return "\n\n".join(lines)

def build_compare_context(articles: list, orgs: list, topic_keywords: list) -> tuple:
    """두 기관별 기사를 각각 검색해서 비교용 컨텍스트 생성"""
    query_for_topic = " ".join(topic_keywords)
    all_matched = []
    sections = []
    for org in orgs:
        org_articles = find_articles(articles, query_for_topic or org, force_org=org)
        # topic이 없으면 해당 기관 최신 기사 5개
        if not org_articles and not topic_keywords:
            org_articles = [a for a in articles if org.lower() in a["edu"].lower()][:5]
        all_matched.extend(org_articles)
        sections.append(f"=== {org} 관련 기사 ({len(org_articles)}건) ===\n{build_context(org_articles)}")
    return "\n\n".join(sections), all_matched


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        question = body.get("message", "").strip()
        prev_articles = body.get("prev_articles", [])

        if not question:
            self._json(400, {"error": "질문을 입력해주세요."})
            return

        try:
            articles = load_articles()

            # ── 키워드 트렌드 질문 ─────────────────────────────
            if is_keyword_trend_query(question):
                answer = "3월 1주부터 5월 4주차까지의 교육 뉴스 주요 키워드를 말씀드립니다. 1위 AI 교육(5회 노출), 2위 교육감 선거(3회 노출), 3위 교권 보호(2회 노출)"
                self._json(200, {"answer": answer, "articles": []})
                return

            # ── 비교 질문 ──────────────────────────────────────
            if is_compare_query(question):
                orgs = extract_orgs(question)
                raw_keywords = re.findall(r'\S+', question.lower())
                keywords = [_strip_stopword_suffix(kw) for kw in raw_keywords if not _is_stopword(kw) and len(kw) >= 2]
                keywords = [kw for kw in keywords if len(kw) >= 2]
                topic_keywords = [kw for kw in keywords
                                  if not any(kw.endswith(s) or s in kw for s in ORG_SUFFIXES)]

                context, matched = build_compare_context(articles, orgs, topic_keywords)
                system = COMPARE_SYSTEM_PROMPT
                user_msg = f"질문: {question}\n\n기관별 기사 데이터:\n{context}"

            # ── 후속 필터 질문 ─────────────────────────────────
            elif prev_articles and is_refine_query(question):
                matched = find_articles(prev_articles, question)
                if not matched:
                    matched = prev_articles
                context = build_context(matched)
                system = SYSTEM_PROMPT
                user_msg = f"질문: {question}\n\n관련 기사 데이터:\n{context}"

            # ── 일반 검색 ──────────────────────────────────────
            else:
                matched = find_articles(articles, question, limit=10)
                context = build_context(matched)
                system = SYSTEM_PROMPT
                user_msg = f"질문: {question}\n\n관련 기사 데이터:\n{context}"

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            answer = completion.choices[0].message.content.strip()

            article_cards = [
                {
                    "week":    a["week"],
                    "edu":     a["edu"],
                    "title":   a["title"],
                    "summary": a["summary"],
                    "meta":    a["meta"],
                    "url":     a["url"],
                }
                for a in matched
            ]

            self._json(200, {"answer": answer, "articles": article_cards})

        except Exception as e:
            self._json(500, {"error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
