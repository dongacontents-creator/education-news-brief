#!/usr/bin/env python3
"""
data/weeks.json → index.html 자동 생성
- 가로 정렬 최적화 (page-wrap 내부로 섹션 통합)
- 드롭다운 선택 시 자동 닫힘 로직 추가
"""

import json, re
from pathlib import Path
from html import escape

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

# ── 정적 HTML 파트 ─────────────────────────────────────────

HTML_HEAD = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>교육 뉴스 브리핑</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Apple SD Gothic Neo','Malgun Gothic',sans-serif; background:#f0f2f6; color:#1a1a2e; font-size:14px; line-height:1.6; }

/* 레이아웃: 모든 섹션의 가로 길이를 통일하는 컨테이너 */
.page-wrap { max-width:1080px; margin:0 auto; padding:28px 24px 60px; }

.page-header { background:#fff; border-radius:14px; padding:26px 30px 22px; margin-bottom:20px; border:.5px solid #dde1ea; width: 100%; }
.page-header h1 { font-size:20px; font-weight:700; color:#1a1a2e; margin-bottom:4px; }

.filter-wrap { background:#fff; border-radius:10px; border:.5px solid #dde1ea; padding:13px 16px; margin-bottom:20px; display:flex; flex-direction:column; gap:9px; width: 100%; }
.filter-row { display:flex; gap:7px; flex-wrap:wrap; align-items:center; }
.search-wrap { display:flex; align-items:center; gap:8px; padding:7px 12px; border:1.5px solid #dde1ea; border-radius:20px; background:#f8fafc; }
.search-wrap:focus-within { border-color:#1e40af; background:#fff; }
.search-wrap input { border:none; background:transparent; outline:none; font-size:13px; color:#1a1a2e; width:100%; }
.search-wrap input::placeholder { color:#94a3b8; }
.search-icon { color:#94a3b8; font-size:14px; }

.edu-dropdown-wrap { position:relative; }
.edu-dropdown-btn { padding:6px 14px; border-radius:18px; border:1.5px solid #dde1ea; background:#fff; color:#555; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; display:inline-flex; align-items:center; gap:5px; }
.edu-dropdown-btn:hover { background:#f5f6fb; border-color:#bbbfce; }
.edu-dropdown-btn.active { background:#1e40af; border-color:#1e40af; color:#fff; }
.edu-dropdown-btn .arrow { font-size:9px; transition:transform .2s; }
.edu-dropdown-btn.open .arrow { transform:rotate(180deg); }

.edu-sub-panel { display:none; position:absolute; top:calc(100% + 6px); left:0; background:#fff; border:.5px solid #dde1ea; border-radius:10px; padding:10px 12px; z-index:100; min-width:340px; box-shadow:0 8px 24px rgba(0,0,0,.10); }
.edu-sub-panel.open { display:block; }
.edu-sub-grid { display:grid; grid-template-columns:1fr 1fr; gap:5px; }
.edu-sub-btn { padding:5px 10px; border-radius:14px; border:1px solid #e5e7ef; background:#f8fafc; color:#555; font-size:11px; font-weight:600; cursor:pointer; text-align:left; transition:all .15s; width:100%; }
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
.tag-edu-AI동향 { background:#f5f3ff; color:#6d28d9; border:1px solid #c4b5fd; }
.tag-official { background:#dcfce7; color:#166534; border:1px solid #86efac; }
.tag-source { background:#f1f5f9; color:#475569; }
.tag-topic { background:#f1f5f9; color:#64748b; }
.filter-btn-industry { padding:6px 14px; border-radius:18px; border:1.5px solid #fde047; background:#fefce8; color:#854d0e; font-size:12px; font-weight:700; cursor:pointer; }
.filter-btn-industry.active { background:#ca8a04; border-color:#ca8a04; color:#fff; }
.filter-btn-ai { padding:6px 14px; border-radius:18px; border:1.5px solid #c4b5fd; background:#f5f3ff; color:#6d28d9; font-size:12px; font-weight:700; cursor:pointer; }
.filter-btn-ai.active { background:#7c3aed; border-color:#7c3aed; color:#fff; }

.card-title { font-size:14px; font-weight:700; color:#1a1a2e; line-height:1.4; min-height: 2.8em; }
.card-summary { font-size:13px; color:#444; line-height:1.55; flex:1; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; }
.card-insight { font-size:12px; color:#1d4ed8; font-weight:600; padding:5px 10px; background:#eff6ff; border-radius:7px; }
.card-footer { display:flex; align-items:center; justify-content:flex-end; margin-top:2px; gap:7px; }
.btn-link { display:inline-block; padding:5px 13px; background:#1e40af; color:#fff; text-decoration:none; border-radius:7px; font-size:12px; font-weight:600; }
.btn-brief { display:inline-block; padding:5px 13px; background:#f1f5f9; color:#475569; border:none; border-radius:7px; font-size:12px; font-weight:600; cursor:pointer; }

.weekly-insight { background:#f0f7ff; border-left:4px solid #1e40af; border-radius:0 10px 10px 0; padding:13px 16px; margin-bottom:13px; display:flex; flex-direction:column; gap:6px; }
.weekly-insight-title { font-size:12px; font-weight:700; color:#1e40af; margin-bottom:2px; }
.weekly-insight-item { font-size:13px; color:#1e293b; line-height:1.5; }
.weekly-insight-item::before { content:'· '; color:#1e40af; font-weight:700; }
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

CHATBOT_HTML = '''
<style>
#chatbot-btn{position:fixed;bottom:28px;right:28px;width:52px;height:52px;border-radius:50%;background:#1e40af;color:#fff;border:none;font-size:24px;cursor:pointer;box-shadow:0 4px 16px rgba(30,64,175,.35);z-index:900;display:flex;align-items:center;justify-content:center;}
#chatbot-btn:hover{background:#1d3c9e;}
#chatbot-panel{position:fixed;bottom:90px;right:28px;width:360px;max-height:520px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.15);display:none;flex-direction:column;z-index:900;overflow:hidden;}
#chatbot-panel.open{display:flex;}
#chatbot-header{background:#1e40af;color:#fff;padding:14px 16px;font-weight:700;font-size:14px;display:flex;justify-content:space-between;align-items:center;}
#chatbot-close{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1;}
#chatbot-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;}
.chat-msg{max-width:85%;padding:9px 13px;border-radius:12px;font-size:13px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}
.chat-msg.user{background:#1e40af;color:#fff;align-self:flex-end;border-bottom-right-radius:3px;}
.chat-msg.bot{background:#f1f5f9;color:#1e293b;align-self:flex-start;border-bottom-left-radius:3px;}
.chat-msg.loading{color:#94a3b8;font-style:italic;}
#chatbot-input-wrap{display:flex;padding:10px;gap:8px;border-top:1px solid #e5e7eb;}
#chatbot-input{flex:1;border:1.5px solid #dde1ea;border-radius:10px;padding:8px 12px;font-size:13px;outline:none;resize:none;height:40px;}
#chatbot-input:focus{border-color:#1e40af;}
#chatbot-send{background:#1e40af;color:#fff;border:none;border-radius:10px;padding:8px 14px;font-size:13px;cursor:pointer;white-space:nowrap;}
#chatbot-send:hover{background:#1d3c9e;}
#chatbot-send:disabled{background:#94a3b8;cursor:not-allowed;}
</style>

<button id="chatbot-btn" onclick="toggleChat()" title="뉴스 검색 챗봇">💬</button>

<div id="chatbot-panel">
  <div id="chatbot-header">
    <span>📚 교육 뉴스 검색</span>
    <button id="chatbot-close" onclick="toggleChat()">✕</button>
  </div>
  <div id="chatbot-messages">
    <div class="chat-msg bot">안녕하세요! 수집된 교육 뉴스에서 원하는 기사를 찾아드립니다.
예) "5월 경기도교육청 돌봄 정책 기사 모아줘"</div>
  </div>
  <div id="chatbot-input-wrap">
    <input id="chatbot-input" type="text" placeholder="질문을 입력하세요..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat();}">
    <button id="chatbot-send" onclick="sendChat()">전송</button>
  </div>
</div>

<script>
const VERCEL_API = 'https://education-news-brief.vercel.app/api/chat';

function toggleChat(){
  const p = document.getElementById('chatbot-panel');
  p.classList.toggle('open');
  if(p.classList.contains('open')) document.getElementById('chatbot-input').focus();
}

async function sendChat(){
  const input = document.getElementById('chatbot-input');
  const msg = input.value.trim();
  if(!msg) return;

  const send = document.getElementById('chatbot-send');
  addMsg(msg, 'user');
  input.value = '';
  send.disabled = true;

  const loading = addMsg('답변을 찾는 중...', 'bot loading');

  try {
    const res = await fetch(VERCEL_API, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: msg}),
    });
    const data = await res.json();
    loading.remove();
    addMsg(data.answer || data.error || '오류가 발생했습니다.', 'bot');
  } catch(e) {
    loading.remove();
    addMsg('서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.', 'bot');
  } finally {
    send.disabled = false;
    input.focus();
  }
}

function addMsg(text, cls){
  const box = document.getElementById('chatbot-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg ' + cls;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}
</script>
'''

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
  document.querySelectorAll('.month-dropdown-btn').forEach(b => b.classList.remove('open', 'active'));
  if (!isOpen) {
    panel.classList.add('open');
    btn.classList.add('open', 'active');
    document.querySelectorAll('.week-all-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
  } else {
    activeMonth = 'all'; activeWeek = 'all';
    document.querySelectorAll('.week-all-btn').forEach(b => b.classList.add('active'));
    document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
  }
  activeMonth = isOpen ? 'all' : month;
  if (isOpen) activeWeek = 'all';
  applyFilter();
}

function filterMonthSub(weekId, el) {
  activeWeek = weekId;
  document.querySelectorAll('.month-sub-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.week-all-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  // 선택 시 드롭다운 닫기, 부모 월 버튼 active 표시
  document.querySelectorAll('.month-sub-panel').forEach(p => p.classList.remove('open'));
  document.querySelectorAll('.month-dropdown-btn').forEach(b => b.classList.remove('open', 'active'));
  const parentWrap = el.closest('.month-dropdown-wrap');
  if (parentWrap) parentWrap.querySelector('.month-dropdown-btn').classList.add('active');
  applyFilter();
}

function filterEdu(edu, el) {
  activeEdu = edu;
  document.querySelectorAll('#edu-all-btn,#industry-btn,#ai-btn,#edu-dept-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.edu-sub-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  const dropBtn = document.getElementById('edu-drop-btn');
  if (edu !== '업계동향' && edu !== 'AI동향') dropBtn.classList.remove('active');
  document.getElementById('edu-sub-panel').classList.remove('open');
  dropBtn.classList.remove('open');
  applyFilter();
}

function filterEduSub(edu, el) {
  activeEdu = edu;
  document.querySelectorAll('#edu-all-btn,#industry-btn,#ai-btn,#edu-dept-btn').forEach(b => b.classList.remove('active'));
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

let searchQuery = '';
function onSearch(val) {
  searchQuery = val.trim().toLowerCase();
  applyFilter();
}

function applyFilter() {
  document.querySelectorAll('.week-section').forEach(sec => {
    const mMatch = activeMonth === 'all' || sec.dataset.month === activeMonth;
    const wMatch = activeWeek === 'all' || sec.dataset.week === activeWeek;
    let visible = 0;
    sec.querySelectorAll('.news-card').forEach(card => {
      const eMatch = activeEdu === 'all' || card.dataset.edu === activeEdu;
      const title = card.querySelector('.card-title')?.textContent.toLowerCase() || '';
      const sMatch = !searchQuery || title.includes(searchQuery);
      const show = mMatch && wMatch && eMatch && sMatch;
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
            def fmt_tag(t):
                text = t["text"].replace("업계동향", "업계 동향").replace("AI동향", "AI 동향")
                return f'<span class="tag {t["class"]}">{escape(text)}</span>'
            tags = ''.join(fmt_tag(t) for t in c['tags'])
            cards += (f'<div class="news-card" data-edu="{escape(c["edu"])}" data-idx="{idx}">'
                      f'<div class="card-tags">{tags}</div><div class="card-title">{escape(c["title"])}</div>'
                      f'<div class="card-meta">{escape(c["meta"])}</div><div class="card-summary">{escape(c["summary"])}</div>'
                      f'<div class="card-insight">{escape(c["insight"])}</div>'
                      f'<div class="card-footer"><button class="btn-brief" onclick="openBrief(this)">간략보기</button>'
                      f'<a class="btn-link" href="{c["url"]}" target="_blank">원문보기</a></div></div>')
        m = w['badge'].split()[0]
        insight_items = w.get('weekly_insight', [])
        if insight_items:
            insight_html = ''.join(f'<span class="weekly-insight-item">{escape(i)}</span>' for i in insight_items)
            insight_block = f'<div class="weekly-insight"><span class="weekly-insight-title">🔍 이번 주의 교육 인사이트</span>{insight_html}</div>'
        else:
            insight_block = ''
        html += (f'<div class="week-section" data-week="{w["id"]}" data-month="{m}">'
                 f'<div class="week-header"><span class="week-badge">{escape(w["badge"])}</span>'
                 f'<span class="week-date">{escape(w["date"])}</span><div class="week-line"></div></div>'
                 f'{insight_block}<div class="week-keywords">{kw}</div><div class="card-grid">{cards}</div></div>')
    return html

def main():
    try:
        data = load_weeks_json(Path('data/weeks.json'))
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
        '<div class="filter-wrap"><div class="search-wrap"><span class="search-icon">🔍</span><input type="text" placeholder="기사 제목 검색..." oninput="onSearch(this.value)"></div><div class="filter-row"><span class="filter-label">주차</span>'
        '<button class="filter-btn week-all-btn active" onclick="filterAllWeeks(this)">전체</button>' + wk_btns + '</div>'
        '<div class="filter-row" id="edu-row"><span class="filter-label">선택</span>'
        '<button class="filter-btn active" id="edu-all-btn" onclick="filterEdu(\'all\',this)">전체</button>'
        '<button class="filter-btn" id="edu-dept-btn" onclick="filterEdu(\'교육부\',this)">교육부</button>'
        '<div class="edu-dropdown-wrap"><button class="edu-dropdown-btn" id="edu-drop-btn" onclick="toggleEduPanel(this)">교육청 선택 <span class="arrow">▼</span></button>'
        '<div class="edu-sub-panel" id="edu-sub-panel"><div class="edu-sub-grid">' + edu_panel + '</div></div></div>'
        '<button class="filter-btn-industry" id="industry-btn" onclick="filterEdu(\'업계동향\',this)">📊 업계 동향</button>'
                 '<button class="filter-btn-ai" id="ai-btn" onclick="filterEdu(\'AI동향\',this)">🤖 AI 동향</button></div></div>'
        + wk_secs + '</div>' + MODAL_HTML + 
        '<script>const CARD_DATA = ' + json.dumps(all_cards, ensure_ascii=False) + ';' + JS_FUNCTIONS + '</script>'
        + CHATBOT_HTML + '</body></html>'
    )
    
    Path('index.html').write_text(final_html, encoding='utf-8')
    print("index.html 생성 완료")

if __name__ == '__main__':
    main()
