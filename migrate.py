#!/usr/bin/env python3
"""기존 education_news_brief_v4.html에서 data/weeks.json으로 데이터 추출 (1회 실행)"""

from bs4 import BeautifulSoup
import json, re, os

with open('education_news_brief_v4.html', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')

# CARD_DATA (JS 배열)에서 points, lang 추출
m = re.search(r'const CARD_DATA = (\[.*?\]);', html_content, re.DOTALL)
card_data = json.loads(m.group(1)) if m else []

weeks = []
for section in soup.find_all('div', class_='week-section'):
    week_id = section.get('data-week', '')
    badge = section.find('span', class_='week-badge').get_text(strip=True)
    date_el = section.find('span', class_='week-date')
    date = date_el.get_text(strip=True) if date_el else ''
    keywords = [kw.get_text(strip=True) for kw in section.find_all('span', class_='kw')]

    cards = []
    for card in section.find_all('div', class_='news-card'):
        idx = int(card.get('data-idx', -1))
        edu = card.get('data-edu', '')

        tags = []
        tags_div = card.find('div', class_='card-tags')
        if tags_div:
            for span in tags_div.find_all('span', class_='tag'):
                cls_list = [c for c in span.get('class', []) if c != 'tag']
                tags.append({'class': ' '.join(cls_list), 'text': span.get_text(strip=True)})

        def text(cls):
            el = card.find('div', class_=cls)
            return el.get_text(strip=True) if el else ''

        link = card.find('a', class_='btn-link')
        url = link.get('href', '#') if link else '#'
        has_translate = bool(card.find('button', class_='btn-translate'))

        cd = card_data[idx] if 0 <= idx < len(card_data) else {}
        points = cd.get('points', [text('card-summary')])
        lang = cd.get('lang', 'ko')

        cards.append({
            'edu': edu,
            'tags': tags,
            'title': text('card-title'),
            'meta': text('card-meta'),
            'summary': text('card-summary'),
            'insight': text('card-insight'),
            'url': url,
            'points': points,
            'lang': lang,
            'has_translate': has_translate,
        })

    weeks.append({
        'id': week_id,
        'badge': badge,
        'date': date,
        'keywords': keywords,
        'cards': cards,
    })

os.makedirs('data', exist_ok=True)
output = {'weeks': weeks}
with open('data/weeks.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

total_cards = sum(len(w['cards']) for w in weeks)
print(f"완료: {len(weeks)}개 주차, {total_cards}개 카드 → data/weeks.json")
