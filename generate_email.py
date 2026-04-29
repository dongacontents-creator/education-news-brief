#!/usr/bin/env python3
"""매주 최신 주차 뉴스 3개를 골라 이메일 HTML을 생성하는 스크립트"""

from bs4 import BeautifulSoup
import json, re, sys
from datetime import date

BRIEFING_URL = "https://dongacontents-creator.github.io/education-news-brief/education_news_brief_v4.html"

with open('education_news_brief_v4.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# ── 가장 마지막 주차 찾기 ────────────────────────────
weeks = ['w8','w7','w6','w5','w4','w3','w2','w1']
latest_sec = None
for w in weeks:
    sec = soup.find('div', class_='week-section', attrs={'data-week': w})
    if sec and sec.find_all('div', class_='news-card'):
        latest_sec = sec
        break

badge = latest_sec.find('span', class_='week-badge').get_text().strip()
week_date = latest_sec.find('span', class_='week-date').get_text().strip()
keywords = [s.get_text().strip() for s in latest_sec.find_all('span', class_='kw')]
cards = latest_sec.find_all('div', class_='news-card')

# ── 주요 뉴스 3개 선택 (교육부/교육청/에듀테크 우선) ──
selected = cards[:3]

def make_card(card):
    title = card.find('div', class_='card-title').get_text().strip()
    meta  = card.find('div', class_='card-meta').get_text().strip()
    summary = card.find('div', class_='card-summary').get_text().strip()
    link = card.find('a', class_='btn-link')
    url  = link.get('href','') if link else '#'
    return title, meta, summary, url

cards_html = ""
for card in selected:
    title, meta, summary, url = make_card(card)
    cards_html += f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; margin-bottom:16px;">
      <div style="font-size:12px; color:#64748b; margin-bottom:8px;">{meta}</div>
      <div style="font-size:17px; font-weight:700; color:#1e293b; line-height:1.4; margin-bottom:10px;">{title}</div>
      <div style="font-size:14px; color:#475569; line-height:1.6; margin-bottom:16px;">{summary}</div>
      <a href="{url}" style="display:inline-block; background:#3b82f6; color:#ffffff; text-decoration:none; padding:8px 16px; border-radius:6px; font-size:13px; font-weight:600;">원문 보기 →</a>
    </div>"""

kw_html = "".join(
    f'<span style="display:inline-block; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe; border-radius:20px; padding:5px 14px; font-size:13px; font-weight:600; margin:4px;">#{kw}</span>'
    for kw in keywords
)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📚 주간 교육 뉴스 브리핑 — {badge}</title></head>
<body style="margin:0; padding:0; background:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:620px; margin:0 auto; padding:32px 16px;">

  <!-- 헤더 -->
  <div style="background:linear-gradient(135deg,#1e40af,#3b82f6); border-radius:16px; padding:32px; margin-bottom:24px; text-align:center;">
    <div style="font-size:13px; color:#bfdbfe; letter-spacing:0.1em; margin-bottom:8px;">WEEKLY EDUCATION NEWS</div>
    <div style="font-size:28px; font-weight:800; color:#ffffff; margin-bottom:6px;">📚 교육 뉴스 브리핑</div>
    <div style="font-size:15px; color:#dbeafe;">{badge} &nbsp;·&nbsp; {week_date}</div>
  </div>

  <!-- 주요 뉴스 -->
  <div style="font-size:13px; font-weight:700; color:#64748b; letter-spacing:0.08em; margin-bottom:12px;">이번 주 주요 뉴스</div>
  {cards_html}

  <!-- 이슈 키워드 -->
  <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; margin-bottom:16px;">
    <div style="font-size:13px; font-weight:700; color:#64748b; letter-spacing:0.08em; margin-bottom:14px;">이번 주 이슈 키워드</div>
    <div>{kw_html}</div>
  </div>

  <!-- 전체 보기 -->
  <div style="background:linear-gradient(135deg,#0f172a,#1e40af); border-radius:12px; padding:28px; text-align:center; margin-bottom:24px;">
    <div style="font-size:16px; font-weight:700; color:#ffffff; margin-bottom:8px;">더 많은 교육 뉴스가 궁금하신가요?</div>
    <div style="font-size:13px; color:#94a3b8; margin-bottom:20px;">전체 주차별 뉴스브리핑을 한눈에 확인하세요</div>
    <a href="{BRIEFING_URL}" style="display:inline-block; background:#3b82f6; color:#ffffff; text-decoration:none; padding:12px 28px; border-radius:8px; font-size:15px; font-weight:700;">전체 뉴스브리핑 보기 →</a>
  </div>

  <!-- 푸터 -->
  <div style="text-align:center; font-size:12px; color:#94a3b8; line-height:1.8;">
    매주 월요일 오전 8시 자동 발송<br>
    교육 뉴스 브리핑 · dongacontents@gmail.com
  </div>

</div>
</body>
</html>"""

with open('email_newsletter.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(html)
