#!/usr/bin/env python3
"""data/weeks.json → index.html 자동 생성"""

import json
from pathlib import Path
from html import escape

# ── 정적 HTML 파트 ─────────────────────────────────────────

HTML_HEAD = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>동아출판 교육 뉴스 브리프</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Apple SD Gothic Neo','Malgun Gothic',sans-serif; background:#f0f2f6; color:#1a1a2e; font-size:14px; line-height:1.6; }
.page-wrap { max-width:860px; margin:0 auto; padding:28px 16px 60px; }
.page-header { background:#fff; border-radius:14px; padding:26px 30px 22px; margin-bottom:20px; border:.5px solid #dde1ea; }
.page-header h1 { font-size:20px; font-weight:700; color:#1a1a2e; margin-bottom:4px; }
.page-header p { font-size:13px; color:#888; }
.filter-wrap { background:#fff; border-radius:10px; border:.5px solid #dde1ea; padding:13px 16px; margin-bottom:20px; display:flex; flex-direction:column; gap:9px; }
.filter-row { display:flex; gap:7px; flex-wrap:wrap; align-items:center; }
.filter-row#edu-row { align-items:center; }
.edu-dropdown-wrap { position:relative; }
.edu-dropdown-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; display:inline-flex; align-items:center; gap:5px; }
.edu-dropdown-btn:hover { background:#f5f6fb; border-color:#bbbfce; }
.edu-dropdown-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.edu-dropdown-btn .arrow { font-size:9px; transition:transform .2s; }
.edu-dropdown-btn.open .arrow { transform:rotate(180deg); }
.edu-sub-panel { display:none; position:absolute; top:calc(100% + 6px); left:0; background:#fff; border:.5px solid #dde1ea; border-radius:10px; padding:10px 12px; z-index:100; min-width:260px; box-shadow:0 8px 24px rgba(0,0,0,.10); }
.edu-sub-panel.open { display:block; }
.edu-sub-grid { display:grid; grid-template-columns:1fr 1fr; gap:5px; }
.edu-sub-btn { padding:5px 10px; border-radius:14px; border:1px solid #e5e7ef; background:#f8fafc; color:#555; font-size:11px; font-weight:600; cursor:pointer; text-align:left; transition:all .15s; white-space:nowrap; }
.edu-sub-btn:hover { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8; }
.edu-sub-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.filter-label { font-size:11px; font-weight:700; color:#aaa; letter-spacing:.04em; white-space:nowrap; margin-right:2px; }
.filter-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; }
.filter-btn:hover { background:#f5f6fb; border-color:#bbbfce; }
.filter-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.week-section { margin-bottom:30px; }
.week-header { display:flex; align-items:center; gap:10px; margin-bottom:13px; }
.week-badge { background:#1e40af; color:#fff; font-size:12px; font-weight:700; padding:4px 13px; border-radius:12px; white-space:nowrap; }
.week-date { font-size:12px; color:#aaa; }
.week-line { flex:1; height:1px; background:#e5e7ef; }
.card-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.news-card { background:#fff; border-radius:12px; border:.5px solid #dde1ea; padding:15px 16px 13px; display:flex; flex-direction:column; gap:7px; transition:box-shadow .18s,border-color .18s; }
.news-card:hover { border-color:#c0c7dc; box-shadow:0 3px 14px rgba(30,64,175,.06); }
.news-card.hidden { display:none; }
.card-tags { display:flex; flex-wrap:wrap; gap:5px; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:2px 9px; border-radius:8px; white-space:nowrap; }
.tag-edu-교육부 { background:#eff6ff; color:#1d4ed8; }
.tag-edu-서울특별시교육청 { background:#fdf4ff; color:#7e22ce; }
.tag-edu-경기도교육청 { background:#f0fdf4; color:#15803d; }
.tag-edu-대구광역시교육청 { background:#fff7ed; color:#c2410c; }
.tag-edu-부산광역시교육청 { background:#fff1f2; color:#be123c; }
.tag-edu-인천광역시교육청 { background:#ecfdf5; color:#047857; }
.tag-edu-광주광역시교육청 { background:#f0f9ff; color:#0369a1; }
.tag-edu-대전광역시교육청 { background:#fff7ed; color:#9a3412; }
.tag-edu-울산광역시교육청 { background:#f0fdfa; color:#0f766e; }
.tag-edu-세종특별자치시교육청 { background:#fdf2f8; color:#9d174d; }
.tag-edu-강원도교육청 { background:#f7fee7; color:#3f6212; }
.tag-edu-충청북도교육청 { background:#fffbeb; color:#78350f; }
.tag-edu-충청남도교육청 { background:#fff1f2; color:#881337; }
.tag-edu-전라북도교육청 { background:#eff6ff; color:#1e40af; }
.tag-edu-전라남도교육청 { background:#f0fdf4; color:#14532d; }
.tag-edu-경상북도교육청 { background:#fefce8; color:#713f12; }
.tag-edu-경상남도교육청 { background:#fef2f2; color:#7f1d1d; }
.tag-edu-제주특별자치도교육청 { background:#f0f9ff; color:#0c4a6e; }
.tag-edu-기타 { background:#f8fafc; color:#64748b; }
.tag-edu-업계동향 { background:#fefce8; color:#854d0e; border:1px solid #fde047; }
.filter-btn-industry { padding:6px 14px; border-radius:18px; border:1.5px solid #fde047; background:#fefce8; color:#854d0e; font-size:12px; font-weight:700; cursor:pointer; transition:all .15s; }
.filter-btn-industry:hover { background:#fef08a; }
.filter-btn-industry.active { background:#ca8a04; border-color:#ca8a04; color:#fff; }
.tag-source { background:#f1f5f9; color:#475569; }
.tag-topic { background:#faf5ff; color:#7c3aed; }
.card-title { font-size:14px; font-weight:700; color:#1a1a2e; line-height:1.4; }
.card-meta { font-size:11px; color:#aaa; }
.card-summary { font-size:13px; color:#444; line-height:1.55; flex:1; }
.card-insight { font-size:12px; color:#1d4ed8; font-weight:600; padding:5px 10px; background:#eff6ff; border-radius:7px; }
.card-footer { display:flex; align-items:center; justify-content:flex-end; margin-top:2px; gap:7px; }
.btn-link { display:inline-block; padding:5px 13px; background:#1e40af; color:#fff; text-decoration:none; border-radius:7px; font-size:12px; font-weight:600; transition:background .15s; }
.btn-link:hover { background:#1d3a9b; }
.btn-brief { display:inline-block; padding:5px 13px; background:#f1f5f9; color:#475569; border:none; border-radius:7px; font-size:12px; font-weight:600; cursor:pointer; transition:background .15s; }
.btn-brief:hover { background:#e2e8f0; }
.week-keywords { display:flex; gap:7px; flex-wrap:wrap; margin-bottom:13px; }
.kw { display:inline-flex; align-items:center; gap:4px; padding:5px 14px; border-radius:20px; background:#1e3a8a; color:#bfdbfe; font-size:12px; font-weight:700; letter-spacing:.01em; }
.kw::before { content:'#'; opacity:.55; font-weight:400; }
.modal-backdrop { display:none; position:fixed; inset:0; background:rgba(15,23,42,.45); z-index:1000; align-items:center; justify-content:center; padding:20px; }
.modal-backdrop.open { display:flex; }
.modal-box { background:#fff; border-radius:16px; width:100%; max-width:520px; padding:28px 28px 24px; position:relative; box-shadow:0 20px 60px rgba(15,23,42,.18); }
.modal-close { position:absolute; top:14px; right:16px; background:none; border:none; font-size:20px; color:#94a3b8; cursor:pointer; line-height:1; }
.modal-close:hover { color:#1e40af; }
.modal-kicker { font-size:11px; font-weight:700; color:#94a3b8; letter-spacing:.06em; text-transform:uppercase; margin-bottom:8px; }
.modal-title { font-size:16px; font-weight:700; color:#1a1a2e; line-height:1.4; margin-bottom:12px; }
.modal-divider { height:1px; background:#e5e7ef; margin-bottom:16px; }
.modal-points { list-style:none; display:flex; flex-direction:column; gap:10px; }
.modal-points li { display:flex; gap:10px; font-size:13.5px; color:#334155; line-height:1.55; }
.modal-points li::before { content:''; display:block; width:6px; height:6px; border-radius:50%; background:#1e40af; margin-top:7px; flex-shrink:0; }
.modal-insight { margin-top:16px; padding:10px 14px; background:#eff6ff; border-radius:8px; font-size:12px; font-weight:700; color:#1d4ed8; }
.btn-translate { display:inline-block; padding:5px 13px; background:#fef3c7; color:#92400e; border:none; border-radius:7px; font-size:12px; font-weight:600; cursor:pointer; transition:background .15s; white-space:nowrap; }
.btn-translate:hover { background:#fde68a; }
.btn-modal-translate { width:100%; padding:9px; background:#fef3c7; color:#92400e; border:none; border-radius:8px; font-size:13px; font-weight:700; cursor:pointer; transition:background .15s; }
.btn-modal-translate:hover { background:#fde68a; }
.btn-modal-translate:disabled { background:#f1f5f9; color:#94a3b8; cursor:default; }
.modal-footer { margin-top:20px; display:flex; justify-content:flex-end; gap:8px; }
.month-dropdown-wrap { position:relative; }
.month-dropdown-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; display:inline-flex; align-items:center; gap:5px; }
.month-dropdown-btn:hover { background:#f5f6fb; border-color:#bbbfce; }
.month-dropdown-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.month-dropdown-btn .arrow { font-size:9px; transition:transform .2s; }
.month-dropdown-btn.open .arrow { transform:rotate(180deg); }
.month-sub-panel { display:none; position:absolute; top:calc(100% + 6px); left:0; background:#fff; border:.5px solid #dde1ea; border-radius:10px; padding:10px 12px; z-index:100; min-width:120px; box-shadow:0 8px 24px rgba(0,0,0,.10); }
.month-sub-panel.open { display:block; }
.month-sub-grid { display:flex; flex-direction:column; gap:5px; }
.month-sub-btn { padding:5px 10px; border-radius:14px; border:1px solid #e5e7ef; background:#f8fafc; color:#555; font-size:11px; font-weight:600; cursor:pointer; text-align:left; transition:all .15s; white-space:nowrap; }
.month-sub-btn:hover { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8; }
.month-sub-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
</style>
</head>'''

MODAL_HTML = '''<!-- 간략보기 모달 -->
<div class="modal-backdrop" id="modal" onclick="if(event.target===this)closeModal()">
<div class="modal-box">
<button class="modal-close" onclick="closeModal()">✕</button>
<div class="modal-kicker" id="m-kicker"></div>
<div class="modal-title" id="m-title"></div>
<div class="modal-divider"></div>
<ul class="modal-points" id="m-points"></ul>
<div class="modal-insight" id="m-insight"></div>
<div style="margin-top:14px;"><button class="btn-modal-translate" id="m-translate-btn" onclick="doTranslate()">🌐 영어로 번역하기</button></div>
<div id="m-translated" style="display:none; margin-top:14px; padding:14px; background:#fffbeb; border-radius:8px; border:.5px solid #fde68a;">
<div style="font-size:11px; font-weight:700; color:#b45309; letter-spacing:.05em; margin-bottom:8px;">🌐 번역 결과</div>
<ul id="m-translated-list" style="list-style:none; display:flex; flex-direction:column; gap:8px;"></ul>
</div>
<div class="modal-footer">
<button class="btn-brief" onclick="closeModal()">닫기</button>
<a class="btn-link" href="#" id="m-link" target="_blank">원문보기</a>
</div>
</div>
</div>'''

JS_FUNCTIONS = '''
let activeMonth = 'all', activeWeek = 'all', activeEdu = 'all';

function filterAllWeeks(el) {
 activeMonth = 'all';
 activeWeek = 'all';
 document.querySelectorAll('.week-all-btn').forEach(b => b.classList.add('active'));
 document.querySelectorAll('.month-dropdown-btn').forEach(b => { b.classList.remove('active'); b.classList.remove('open'); });
 document.querySelectorAll('.month-sub-panel').forEach(p => p.classList.remove('open'));
 document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
 applyFilter();
}

function toggleMonthPanel(month, btn) {
 const panel = document.getElementById('month-sub-' + month);
 const isOpen = panel.classList.contains('open');
 document.querySelectorAll('.month-sub-panel').forEach(p => p.classList.remove('open'));
 document.querySelectorAll('.month-dropdown-btn').forEach(b => b.classList.remove('open'));
 if (!isOpen) { panel.classList.add('open'); btn.classList.add('open'); }
 activeMonth = month;
 activeWeek = 'all';
 document.querySelectorAll('.week-all-btn').forEach(b => b.classList.remove('active'));
 document.querySelectorAll('.month-dropdown-btn').forEach(b => b.classList.remove('active'));
 document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
 btn.classList.add('active');
 applyFilter();
}

function filterMonthSub(weekId, el) {
 activeWeek = weekId;
 document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
 el.classList.add('active');
 applyFilter();
}

function filterEdu(edu, el) {
 activeEdu = edu;
 document.querySelectorAll('#edu-all-btn,#industry-btn,#edu-dept-btn').forEach(b => b.classList.remove('active'));
 document.querySelectorAll('.edu-sub-btn').forEach(b => b.classList.remove('active'));
 el.classList.add('active');
 const dropBtn = document.getElementById('edu-drop-btn');
 if (edu !== '업계동향') dropBtn.classList.remove('active');
 document.getElementById('edu-sub-panel').classList.remove('open');
 dropBtn.classList.remove('open');
 applyFilter();
}

function filterEduSub(edu, el) {
 activeEdu = edu;
 document.querySelectorAll('#edu-all-btn,#industry-btn,#edu-dept-btn').forEach(b => b.classList.remove('active'));
 document.querySelectorAll('.edu-sub-btn').forEach(b => b.classList.remove('active'));
 el.classList.add('active');
 const dropBtn = document.getElementById('edu-drop-btn');
 dropBtn.classList.add('active');
 document.getElementById('edu-sub-panel').classList.remove('open');
 dropBtn.classList.remove('open');
 applyFilter();
}

function toggleEduPanel(btn) {
 const panel = document.getElementById('edu-sub-panel');
 panel.classList.toggle('open');
 btn.classList.toggle('open');
}

document.addEventListener('click', function(e) {
 document.querySelectorAll('.month-dropdown-wrap').forEach(wrap => {
   if (!wrap.contains(e.target)) {
     wrap.querySelector('.month-sub-panel').classList.remove('open');
     wrap.querySelector('.month-dropdown-btn').classList.remove('open');
   }
 });
 const eduWrap = document.querySelector('.edu-dropdown-wrap');
 if (eduWrap && !eduWrap.contains(e.target)) {
   document.getElementById('edu-sub-panel').classList.remove('open');
   document.getElementById('edu-drop-btn').classList.remove('open');
 }
});

function applyFilter() {
 document.querySelectorAll('.week-section').forEach(sec => {
   const mMatch = activeMonth === 'all' || sec.dataset.month === activeMonth;
   const wMatch = activeWeek === 'all' || sec.dataset.week === activeWeek;
   let visible = 0;
   sec.querySelectorAll('.news-card').forEach(card => {
     const eMatch = activeEdu === 'all' || card.dataset.edu === activeEdu;
     const show = mMatch && wMatch && eMatch;
     card.classList.toggle('hidden', !show);
     if (show) visible++;
   });
   sec.style.display = (mMatch && wMatch && visible > 0) ? '' : 'none';
 });
}

function openBrief(el) {
 const card = el.closest('.news-card');
 const idx = parseInt(card.dataset.idx);
 const d = CARD_DATA[idx];
 if (!d) return;
 document.getElementById('m-kicker').textContent = d.meta || '';
 document.getElementById('m-title').textContent = d.title || '';
 document.getElementById('m-insight').textContent = d.insight || '';
 document.getElementById('m-link').href = d.url || '#';
 const ul = document.getElementById('m-points');
 ul.innerHTML = d.points.map(p => '<li>' + p + '</li>').join('');
 const td = document.getElementById('m-translated');
 if (td) td.style.display = 'none';
 const tl = document.getElementById('m-translated-list');
 if (tl) tl.innerHTML = '';
 document.getElementById('modal').classList.add('open');
}

function translateCard(el) {
 const card = el.closest('.news-card');
 card.querySelector('.btn-brief').click();
 setTimeout(doTranslate, 100);
}

async function doTranslate() {
 const td = document.getElementById('m-translated');
 const tl = document.getElementById('m-translated-list');
 const tb = document.getElementById('m-translate-btn');
 if (!td || !tl) return;
 if (tb) { tb.textContent = '번역 중...'; tb.disabled = true; }
 td.style.display = '';
 tl.innerHTML = '<li style="color:#92400e;">번역 중...</li>';
 const items = document.querySelectorAll('#m-points li');
 const pointsText = Array.from(items).map((li, i) => (i+1) + '. ' + li.textContent).join('\\n');
 const prompt = '다음 한국어 교육 뉴스 내용을 영어로 번역해주세요. 번호 목록(1. 2. 3.)으로만 출력하고 다른 설명은 넣지 마세요.\\n\\n' + pointsText;
 try {
   const res = await fetch('https://api.anthropic.com/v1/messages', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'anthropic-version': '2023-06-01',
       'anthropic-dangerous-direct-browser-access': 'true'
     },
     body: JSON.stringify({
       model: 'claude-haiku-4-5-20251001',
       max_tokens: 1000,
       messages: [{ role: 'user', content: prompt }]
     })
   });
   const data = await res.json();
   const text = data.content[0].text.trim();
   const lines = text.split('\\n').map(l => l.replace(/^\\d+\\.\\s*/, '').trim()).filter(l => l.length > 0);
   tl.innerHTML = lines.map(l => '<li style="font-size:13px;color:#334155;line-height:1.55;">' + l + '</li>').join('');
   if (tb) { tb.textContent = '✓ 번역 완료'; }
 } catch(e) {
   tl.innerHTML = '<li style="color:#dc2626;">번역 실패 — 다시 시도해 주세요</li>';
   if (tb) { tb.textContent = '🌐 다시 시도'; tb.disabled = false; }
 }
}

function closeModal() {
 document.getElementById('modal').classList.remove('open');
}

document.addEventListener('keydown', e => {
 if (e.key === 'Escape') closeModal();
});
'''

EDU_SUB_BUTTONS = [
    '서울특별시교육청', '경기도교육청', '인천광역시교육청', '대전광역시교육청',
    '광주광역시교육청', '대구광역시교육청', '울산광역시교육청', '부산광역시교육청',
    '세종특별자치시교육청', '강원도교육청', '충청북도교육청', '충청남도교육청',
    '전라북도교육청', '전라남도교육청', '경상북도교육청', '경상남도교육청',
    '제주특별자치도교육청',
]

# ── 동적 HTML 생성 함수 ─────────────────────────────────────

def build_week_filter_buttons(weeks):
    from collections import OrderedDict
    months = OrderedDict()
    for w in weeks:
        parts = w['badge'].split()
        month = parts[0]
        week_label = parts[1].replace('주차', '주')
        if month not in months:
            months[month] = []
        months[month].append({'id': w['id'], 'label': week_label})

    html = ''
    for month, sub_weeks in months.items():
        sub_btns = ''.join(
            f'<button class="month-sub-btn" onclick="filterMonthSub(\'{sw["id"]}\',this)">{escape(sw["label"])}</button>'
            for sw in sub_weeks
        )
        html += (
            f'<div class="month-dropdown-wrap">'
            f'<button class="month-dropdown-btn" onclick="toggleMonthPanel(\'{month}\',this)">'
            f'{escape(month)} <span class="arrow">▼</span></button>'
            f'<div class="month-sub-panel" id="month-sub-{month}">'
            f'<div class="month-sub-grid">{sub_btns}</div>'
            f'</div></div>'
        )
    return html


def build_week_sections(weeks, all_cards):
    html = ''
    for w in weeks:
        kw_html = ''.join(f'<span class="kw">{escape(kw)}</span>' for kw in w['keywords'])

        cards_html = ''
        for card in w['cards']:
            idx = len(all_cards)
            all_cards.append({
                'title': card['title'],
                'meta': card['meta'],
                'points': card.get('points', [card['summary']]),
                'insight': card['insight'],
                'url': card['url'],
                'lang': card.get('lang', 'ko'),
            })

            tags_html = ''.join(
                f'<span class="tag {t["class"]}">{escape(t["text"])}</span>'
                for t in card['tags']
            )

            translate_btn = (
                '<button class="btn-translate" onclick="translateCard(this)">번역하기</button>'
                if card.get('has_translate') else ''
            )

            cards_html += (
                f'<div class="news-card" data-edu="{escape(card["edu"])}" data-idx="{idx}">'
                f'<div class="card-tags">{tags_html}</div>'
                f'<div class="card-title">{escape(card["title"])}</div>'
                f'<div class="card-meta">{escape(card["meta"])}</div>'
                f'<div class="card-summary">{escape(card["summary"])}</div>'
                f'<div class="card-insight">{escape(card["insight"])}</div>'
                f'<div class="card-footer">{translate_btn}'
                f'<button class="btn-brief" onclick="openBrief(this)">간략보기</button>'
                f'<a class="btn-link" href="{card["url"]}" target="_blank">원문보기</a>'
                f'</div></div>'
            )

        month = w['badge'].split()[0]
        html += (
            f'<!-- ===== {w["badge"]} ===== -->\n'
            f'<div class="week-section" data-week="{w["id"]}" data-month="{month}">\n'
            f'<div class="week-header">'
            f'<span class="week-badge">{escape(w["badge"])}</span>'
            f'<span class="week-date">{escape(w["date"])}</span>'
            f'<div class="week-line"></div>'
            f'</div>\n'
            f'<div class="week-keywords">{kw_html}</div>\n'
            f'<div class="card-grid">{cards_html}</div>\n'
            f'</div>\n'
        )
    return html


def build_edu_sub_panel():
    btns = ''.join(
        f'<button class="edu-sub-btn" onclick="filterEduSub(\'{name}\',this)">{name}</button>'
        for name in EDU_SUB_BUTTONS
    )
    return f'<div class="edu-sub-grid">{btns}</div>'


# ── 메인 ────────────────────────────────────────────────────

def main():
    data = json.loads(Path('data/weeks.json').read_text(encoding='utf-8'))
    weeks = data['weeks']

    all_cards = []
    week_filter_btns = build_week_filter_buttons(weeks)
    week_sections_html = build_week_sections(weeks, all_cards)
    edu_sub_panel = build_edu_sub_panel()
    card_data_json = json.dumps(all_cards, ensure_ascii=False)

    html = (
        HTML_HEAD + '\n'
        '<body>\n'
        '<div class="page-wrap">\n'
        '<div class="page-header">\n'
        '<h1>📰 교육 뉴스 브리핑</h1>\n'
        '</div>\n'
        '<div class="filter-wrap">\n'
        '<div class="filter-row">\n'
        '<span class="filter-label">주차</span>\n'
        '<button class="filter-btn week-all-btn active" onclick="filterAllWeeks(this)">전체</button>\n'
        + week_filter_btns + '\n'
        '</div>\n'
        '<div class="filter-row" id="edu-row">\n'
        '<span class="filter-label">선택</span>\n'
        '<button class="filter-btn active" id="edu-all-btn" onclick="filterEdu(\'all\',this)">전체</button>\n'
        '<button class="filter-btn" id="edu-dept-btn" onclick="filterEdu(\'교육부\',this)">교육부</button>\n'
        '<div class="edu-dropdown-wrap">\n'
        '<button class="edu-dropdown-btn" id="edu-drop-btn" onclick="toggleEduPanel(this)">교육청 선택 <span class="arrow">▼</span></button>\n'
        '<div class="edu-sub-panel" id="edu-sub-panel">\n'
        + edu_sub_panel + '\n'
        '</div>\n'
        '</div>\n'
        '<button class="filter-btn-industry" id="industry-btn" onclick="filterEdu(\'업계동향\',this)">📊 업계동향</button>\n'
        '</div>\n'
        '</div>\n'
        '</div>\n'
        + week_sections_html
        + MODAL_HTML + '\n'
        '<script>\n'
        'const CARD_DATA = ' + card_data_json + ';\n'
        + JS_FUNCTIONS +
        '</script>\n'
        '</body>\n'
        '</html>'
    )

    Path('index.html').write_text(html, encoding='utf-8')
    print(f'생성 완료: {len(weeks)}개 주차, {len(all_cards)}개 카드')


if __name__ == '__main__':
    main()
