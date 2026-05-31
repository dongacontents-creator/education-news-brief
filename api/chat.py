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
아래 관련 기사 데이터를 바탕으로 사용자 질문에 답변하세요.

규칙:
- 관련 기사가 있으면 2~3문장으로 전체 흐름을 요약해서 먼저 설명하세요
- 관련 기사가 없으면 솔직하게 없다고 말하세요
- 답변은 한국어로, 친절하고 간결하게
- 기사 목록이나 URL은 직접 출력하지 마세요 (별도로 표시됩니다)"""

def find_articles(articles: list, query: str) -> list:
    query_lower = query.lower()
    keywords = re.findall(r'\S+', query_lower)
    scored = []
    for art in articles:
        text = (art["title"] + art["summary"] + art["edu"] + art["week"]).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, art))
    scored.sort(key=lambda x: -x[0])
    return [art for _, art in scored[:10]]

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


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        question = body.get("message", "").strip()

        if not question:
            self._json(400, {"error": "질문을 입력해주세요."})
            return

        try:
            articles = load_articles()
            matched = find_articles(articles, question)
            context = build_context(matched)

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"질문: {question}\n\n관련 기사 데이터:\n{context}"},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            answer = completion.choices[0].message.content.strip()

            # 기사 카드용 데이터 별도 반환
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
