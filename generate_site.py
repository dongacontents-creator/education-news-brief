#!/usr/bin/env python3
"""
data/weeks.json → index.html 자동 생성
- 가로 정렬 최적화 (page-wrap 내부로 섹션 통합)
- 드롭다운 선택 시 자동 닫힘 로직 추가
"""

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

/* 레이아웃: 모든 섹션의 가로 길이를 통일하는 컨테이너 */
.page-wrap { max-width:1080px; margin:0 auto; padding:28px 24px 60px; }

.page-header { background:#fff; border-radius:14px; padding:26px 30px 22px; margin-bottom:20px; border:.5px solid #dde1ea; width: 100%; }
.page-header h1 { font-size:20px; font-weight:700; color:#1a1a2e; margin-bottom:4px; }

.filter-wrap { background:#fff; border-radius:10px; border:.5px solid #dde1ea; padding:13px 16px; margin-bottom:20px; display:flex; flex-direction:column; gap:9px; width: 100%; }
.filter-row { display:flex; gap:7px; flex-wrap:wrap; align-items:center; }

.edu-dropdown-wrap { position:relative; }
.edu-dropdown-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; display:inline-flex; align-items:center; gap:5px; }
.edu-dropdown-btn:hover { background:#f5f6fb; border-color:#bbbfce; }
.edu-dropdown-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.edu-dropdown-btn .arrow { font-size:9px; transition:transform .2s; }
.edu-dropdown-btn.open .arrow { transform:rotate(180deg); }

.edu-sub-panel { display:none; position:absolute; top:calc(100% + 6px); left:0; background:#fff; border:.5px solid #dde1ea; border-radius:10px; padding:10px 12px; z-index:100; min-width:260px; box-shadow:0 8px 24px rgba(0,0,0,.10); }
.edu-sub-panel.open { display:block; }
.edu-sub-grid { display:grid; grid-template-columns:1fr 1fr; gap:5px; }
.edu-sub-btn { padding:5px 10px; border-radius:14px; border:1px solid #e5e7ef; background:#f8fafc; color:#555; font-size:11px; font-weight:600; cursor:pointer; text-align:left; transition:all .15s; }
.edu-sub-btn:hover { background:#eff6ff; border-color:#93c5fd; color:#1d4ed8; }
.edu-sub-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }

.filter-label { font-size:11px; font-weight:700; color:#aaa; letter-spacing:.04em; white-space:nowrap; margin-right:2px; }
.filter-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; }
.filter-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }

.week-section { margin-bottom:30px; width: 100%; }
.week-header { display:flex; align-items:center; gap:10px; margin-bottom:13px; }
.week-badge { background:#1e40af; color:#fff; font-size:12px; font-weight:700; padding:4px 13px; border-radius:12px; white-space:nowrap; }
.week-date { font-size:12px; color:#aaa; }
.week-line { flex:1; height:1px; background:#e5e7ef; }

.card-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; width: 100%; }
@media (max-width: 900px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .card-grid { grid-template-columns: 1fr; } }

.news-card { background:#fff; border-radius:12px; border:.5px solid #dde1ea; padding:15px 16px 13px; display:flex; flex-direction:column; gap:7px; transition:box-shadow .18s,border-color .18s; height: 100%; }
.news-card:hover { border-color:#c0c7dc; box-shadow:0 3px 14px rgba(30,64,175,.06); }
.news-card.hidden { display:none; }
.card-tags { display:flex; flex-wrap:wrap; gap:5px; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:2px 9px; border-radius:8px; white-space:nowrap; }
.tag-edu-교육부 { background:#eff6ff; color:#1d4ed8; }
.tag-edu-업계동향 { background:#fefce8; color:#854d0e; border:1px solid #fde047; }
.filter-btn-industry { padding:6px 14px; border-radius:18px; border:1.5px solid #fde047; background:#fefce8; color:#854d0e; font-size:12px; font-weight:700; cursor:pointer; }
.filter-btn-industry.active { background:#ca8a04; border-color:#ca8a04; color:#fff; }

.card-title { font-size:14px; font-weight:700; color:#1a1a2e; line-height:1.4; min-height: 2.8em; }
.card-summary { font-size:13px; color:#444; line-height:1.55; flex:1; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; }
.card-insight { font-size:12px; color:#1d4ed8; font-weight:600; padding:5px 10px; background:#eff6ff; border-radius:7px; }
.card-footer { display:flex; align-items:center; justify-content:flex-end; margin-top:2px; gap:7px; }
.btn-link { display:inline-block; padding:5px 13px; background:#1e40af; color:#fff; text-decoration:none; border-radius:7px; font-size:12px; font-weight:600; }
.btn-brief { display:inline-block; padding:5px 13px; background:#f1f5f9; color:#475569; border:none; border-radius:7px; font-size:12px; font-weight:600; cursor:pointer; }

.week-keywords { display:flex; gap:7px; flex-wrap:wrap; margin-bottom:13px; }
.kw { display:inline-flex; align-items:center; gap:4px; padding:5px 14px; border-radius:20px; background:#1e3a8a; color:#bfdbfe; font-size:12px; font-weight:700; }
.kw::before { content:'#'; opacity:.55; }

.modal-backdrop { display:none; position:fixed; inset:0; background:rgba(15,23,42,.45); z-index:1000; align-items:center; justify-content:center; padding:20px; }
.modal-backdrop.open { display:flex; }
.modal-box { background:#fff; border-radius:16px; width:100%; max-width:520px; padding:28px 28px 24px; position:relative; }
.modal-close { position:absolute; top:14px; right:16px; background:none; border:none; font-size:20px; color:#94a3b8; cursor:pointer; }

.month-dropdown-wrap { position:relative; }
.month-dropdown-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; display:inline-flex; align-items:center; gap:5px; }
.month-dropdown-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.month-dropdown-btn.open .arrow { transform:rotate(180deg); }
.month-sub-panel { display:none; position:absolute; top:calc(100% + 6px); left:0; background:#fff; border:.5px solid #dde1ea; border-radius:10px; padding:10px 12px; z-index:100; min-width:120px; box-shadow:0 8px 24px rgba(0,0,0,.10); }
.month-sub-panel.open { display:block; }
.month-sub-grid { display:flex; flex-direction:column; gap:5px; }
.month-sub-btn { padding:5px 10px; border-radius:14px; border:1px solid #e5e7ef; background:#f8fafc; color:#555; font-size:11px; font-weight:600; cursor:pointer; text-align:left; }
.month-sub-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
</style>
</head>'''

MODAL_HTML = '''<div class="modal-backdrop" id="modal" onclick="if(event.target===this)closeModal()">
<div class="modal-box">
<button class="modal-close" onclick="closeModal()">✕</button>
<div class="modal-title" id="m-title" style="font-weight:700; font-size:16px; margin-bottom:12px;"></div>
<div style="height:1px; background:#e5e7ef; margin-bottom:16px;"></div>
<ul id="m-points" style="list-style:none; display:flex; flex-direction:column; gap:10px; font-size:13.5px; color:#334155;"></ul>
<div id="m-insight" style="margin-top:16px; padding:10px 14px; background:#eff6ff; border-radius:8px; font-size:12px; font-weight:700; color:#1d4ed8;"></div>
<div style="margin-top:20px; display:flex; justify-content:flex-end; gap:8px;">
<button class="btn-brief" onclick="closeModal()">닫기</button>
<a class="btn-link" href="#" id="m-link" target="_blank">원문보기</a>
</div>
</div>
</div>'''

JS_FUNCTIONS = '''
let activeMonth = 'all', activeWeek = 'all', activeEdu = 'all';

function filterAllWeeks(el) {
  activeMonth = 'all'; activeWeek = 'all';
  document.querySelectorAll('.week-all-btn').forEach(b => b.classList.add('active'));
  document.querySelectorAll('.month-dropdown-btn').forEach(b => { b.classList.remove('active', 'open'); });
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
  applyFilter();
}

function filterMonthSub(weekId, el) {
  activeWeek = weekId;
  document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  // 선택 시 드롭다운 닫기
  document.querySelectorAll('.month-sub-panel').forEach(p => p.classList.remove('open'));
  document.querySelectorAll('.month-dropdown-btn').forEach(b => b.classList.remove('open'));
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
  // 선택 시 드롭다운 닫기
  document.getElementById('edu-sub-panel').classList.remove('open');
  dropBtn.classList.remove('open');
  applyFilter();
}

function toggleEduPanel(btn) {
  document.getElementById('edu-sub-panel').classList.toggle('open');
  btn.classList.toggle('open');
}

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
  document.getElementById('m-title').textContent = d.title;
  document.getElementById('m-insight').textContent = d.insight;
  document.getElementById('m-link').href = d.url;
  document.getElementById('m-points').innerHTML = d.points.map(p => '<li>' + p + '</li>').join('');
  document.getElementById('modal').classList.add('open');
}

function closeModal() { document.getElementById('modal').classList.remove('open'); }
'''

EDU_SUB_BUTTONS = [
    '서울특별시교육청', '경기도교육청', '인천광역시교육청', '대전광역시교육청',
    '광주광역시교육청', '대구광역시교육청', '울산광역시교육청', '부산광역시교육청',
    '세종특별자치시교육청', '강원도교육청', '충청북도교육청', '충청남도교육청',
    '전라북도교육청', '전라남도교육청', '경상북도교육청', '경상남도교육청',
    '제주특별자치도교육청',
]

def build_week_filter_buttons(weeks):
    from collections import OrderedDict
    months = OrderedDict()
    for w in weeks:
        parts = w['badge'].split()
        month = parts[0]
        label = parts[1].replace('주차', '주')
        if month not in months: months[month] = []
        months[month].append({'id': w['id'], 'label': label})
    html = ''
    for m, sws in months.items():
        sub = ''.join(f'<button class="month-sub-btn" onclick="filterMonthSub(\'{s["id"]}\',this)">{escape(s["label"])}</button>' for s in sws)
        html += f'<div class="month-dropdown-wrap"><button class="month-dropdown-btn" onclick="toggleMonthPanel(\'{m}\',this)">{escape(m)} <span class="arrow">▼</span></button><div class="month-sub-panel" id="month-sub-{m}"><div class="month-sub-grid">{sub}</div></div></div>'
    return html

def build_week_sections(weeks, all_cards):
    html = ''
    for w in weeks:
        kw = ''.join(f'<span class="kw">{escape(k)}</span>' for k in w['keywords'])
        cards = ''
        for c in w['cards']:
            idx = len(all_cards)
            all_cards.append({'title': c['title'], 'points': c.get('points', [c['summary']]), 'insight': c['insight'], 'url': c['url']})
            tags = ''.join(f'<span class="tag {t["class"]}">{escape(t["text"])}</span>' for t in c['tags'])
            cards += (f'<div class="news-card" data-edu="{escape(c["edu"])}" data-idx="{idx}">'
                      f'<div class="card-tags">{tags}</div><div class="card-title">{escape(c["title"])}</div>'
                      f'<div class="card-meta">{escape(c["meta"])}</div><div class="card-summary">{escape(c["summary"])}</div>'
                      f'<div class="card-insight">{escape(c["insight"])}</div>'
                      f'<div class="card-footer"><button class="btn-brief" onclick="openBrief(this)">간략보기</button>'
                      f'<a class="btn-link" href="{c["url"]}" target="_blank">원문보기</a></div></div>')
        m = w['badge'].split()[0]
        html += (f'<div class="week-section" data-week="{w["id"]}" data-month="{m}">'
                 f'<div class="week-header"><span class="week-badge">{escape(w["badge"])}</span>'
                 f'<span class="week-date">{escape(w["date"])}</span><div class="week-line"></div></div>'
                 f'<div class="week-keywords">{kw}</div><div class="card-grid">{cards}</div></div>')
    return html

def main():
    try:
        data = json.loads(Path('data/weeks.json').read_text(encoding='utf-8'))
    except:
        print("data/weeks.json 파일 확인 필요")
        return

    weeks_desc = data['weeks'][::-1]
    all_cards = []
    
    wk_btns = build_week_filter_buttons(weeks_desc)
    wk_secs = build_week_sections(weeks_desc, all_cards)
    edu_panel = ''.join(f'<button class="edu-sub-btn" onclick="filterEduSub(\'{n}\',this)">{n}</button>' for n in EDU_SUB_BUTTONS)
    
    final_html = (
        HTML_HEAD + '<body><div class="page-wrap">'
        '<div class="page-header"><h1>📰 교육 뉴스 브리핑</h1></div>'
        '<div class="filter-wrap"><div class="filter-row"><span class="filter-label">주차</span>'
        '<button class="filter-btn week-all-btn active" onclick="filterAllWeeks(this)">전체</button>' + wk_btns + '</div>'
        '<div class="filter-row" id="edu-row"><span class="filter-label">선택</span>'
        '<button class="filter-btn active" id="edu-all-btn" onclick="filterEdu(\'all\',this)">전체</button>'
        '<button class="filter-btn" id="edu-dept-btn" onclick="filterEdu(\'교육부\',this)">교육부</button>'
        '<div class="edu-dropdown-wrap"><button class="edu-dropdown-btn" id="edu-drop-btn" onclick="toggleEduPanel(this)">교육청 선택 <span class="arrow">▼</span></button>'
        '<div class="edu-sub-panel" id="edu-sub-panel"><div class="edu-sub-grid">' + edu_panel + '</div></div></div>'
        '<button class="filter-btn-industry" id="industry-btn" onclick="filterEdu(\'업계동향\',this)">📊 업계동향</button></div></div>'
        + wk_secs + '</div>' + MODAL_HTML + 
        '<script>const CARD_DATA = ' + json.dumps(all_cards, ensure_ascii=False) + ';' + JS_FUNCTIONS + '</script></body></html>'
    )
    
    Path('index.html').write_text(final_html, encoding='utf-8')
    print("index.html 생성 완료")

if __name__ == '__main__':
    main()
