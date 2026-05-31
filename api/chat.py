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

def find_articles(articles: list, query: str, force_org: str = None) -> list:
    query_lower = query.lower()
    raw_keywords = re.findall(r'\S+', query_lower)
    keywords = [kw for kw in raw_keywords if not _is_stopword(kw) and len(kw) >= 2]

    org_keywords   = [kw for kw in keywords if any(kw.endswith(s) or s in kw for s in ORG_SUFFIXES)]
    topic_keywords = [kw for kw in keywords if kw not in org_keywords]

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

        # 비교 검색(force_org): 첫 번째 키워드(핵심 주제) 필수 매칭, 나머지는 점수 보너스
        # 일반 검색: 모든 토픽 키워드 AND
        if topic_keywords:
            if force_org:
                if topic_keywords[0] not in text:
                    continue
            else:
                if not all(kw in text for kw in topic_keywords):
                    continue

        score = topic_score + sum(1 for kw in org_keywords if kw in text)
        if org_match:
            score += 3

        if score > 0:
            scored.append((score, art))

    scored.sort(key=lambda x: -x[0])
    return [art for _, art in scored[:5]]  # 비교 시 각 기관당 5개

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

            # ── 비교 질문 ──────────────────────────────────────
            if is_compare_query(question):
                orgs = extract_orgs(question)
                raw_keywords = re.findall(r'\S+', question.lower())
                keywords = [kw for kw in raw_keywords if not _is_stopword(kw) and len(kw) >= 2]
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
                matched = find_articles(articles, question)
                # 일반 검색은 최대 10개
                raw_keywords = re.findall(r'\S+', question.lower())
                keywords = [kw for kw in raw_keywords if not _is_stopword(kw) and len(kw) >= 2]
                org_keywords = [kw for kw in keywords if any(kw.endswith(s) or s in kw for s in ORG_SUFFIXES)]
                topic_keywords = [kw for kw in keywords if kw not in org_keywords]
                scored = []
                for art in articles:
                    text = (art["title"] + art["summary"] + art["edu"] + art["week"]).lower()
                    if topic_keywords and not all(kw in text for kw in topic_keywords):
                        continue
                    topic_score = sum(1 for kw in topic_keywords if kw in text)
                    org_match = any(kw in art["edu"].lower() for kw in org_keywords)
                    score = topic_score + sum(1 for kw in org_keywords if kw in text)
                    if org_match:
                        score += 3
                    if score > 0:
                        scored.append((score, art))
                scored.sort(key=lambda x: -x[0])
                matched = [art for _, art in scored[:10]]
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
