import streamlit as st
import pandas as pd
import calendar
import random
import io
import copy
from datetime import date
from collections import defaultdict

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="ניהול כוננויות - גרסה מתוקנת ומאוזנת", page_icon="🏥", layout="wide")

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Heebo',sans-serif; direction:rtl; }
.main-title  { text-align:center; font-size:2.2rem; font-weight:800; color:#1a3a5c; margin-bottom:.1rem; }
.sub-title   { text-align:center; font-size:.93rem; color:#6b8cae; margin-bottom:1.4rem; }
.sec-header  { font-size:1.05rem; font-weight:700; color:#1a3a5c; border-right:4px solid #2980b9; padding-right:10px; margin:1rem 0 .5rem; }
.cal-wrap { overflow-x:auto; }
.cal-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.8rem; min-width:720px; }
.cal-table th { background:#1a3a5c; color:#fff; padding:8px 4px; text-align:center; font-weight:700; border:1px solid #15304e; }
.cal-table td { border:1px solid #ccdde9; vertical-align:top; padding:5px 6px; background:#fff; min-width:105px; }
.cal-table td.empty  { background:#f0f4f8; }
.cal-table td.fri-td { background:#fef9ec !important; }
.cal-table td.sat-td { background:#fdf0f0 !important; }
.cal-table td.hol-td { background:#f5f0ff !important; }
.day-num { font-size:.7rem; color:#8aa3b8; font-weight:700; display:block; margin-bottom:3px; }
.badge { display:block; padding:2px 7px; border-radius:11px; font-size:.74rem; font-weight:600; color:#fff; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:115px; }
.badge-heavy { border:2px solid rgba(255,255,255,.4); }
.badge-light { opacity:.85; font-style:italic; }
.badge-pref::after { content:" ★"; font-size:.65rem; opacity:.9; }
.fair-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.87rem; }
.fair-table th { background:#1a3a5c; color:#fff; padding:8px 6px; text-align:center; }
.fair-table td { border:1px solid #d6e4f0; padding:6px 10px; text-align:center; }
.fair-table tr:nth-child(even) td { background:#f7fafd; }
.bar-wrap { background:#e8f0f8; border-radius:5px; height:13px; width:100%; }
.bar-fill { border-radius:5px; height:13px; }
div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:8px; padding:.5rem 1.6rem; font-family:'Heebo',sans-serif; font-size:.95rem; font-weight:600; }
div.stButton > button:hover { background:#2a5a8c; }
.stTextArea textarea, .stTextInput input { direction:rtl; font-family:'Heebo',sans-serif; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONSTANTS & DEFAULTS
# ══════════════════════════════════════════════════════
COLORS = [
    "#2980b9","#27ae60","#8e44ad","#e67e22","#c0392b",
    "#16a085","#d35400","#1a5276","#1abc9c","#922b21",
    "#607d8b","#795548","#f39c12","#6c3483","#0e6655",
]
HEBREW_DAYS   = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
HEBREW_MONTHS = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                 "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
SHIFT_LABELS  = {1:"טור 1 (כבד)", 2:"טור 2 (כבד)", 3:"טור 3 (פסיבי)"}

DEFAULT_DOCTORS = [
    "הרשקוביץ מ'", "דנין י'", "דומני א:", "סאימן א'", "שלי ש'", 
    "הלר א'", "טלמן ג'", "שיפרין-בונ", "רוזנברג א'", "חטיב מ'", "ווינר ר'"
]

DEFAULT_SHIFT_RULES = {
    "הרשקוביץ מ'": [1, 3],
    "טלמן ג'":      [1, 3],
    "שלי ש'":       [1, 3],
    "סאימן א'":     [2, 3],
    "דנין י'":      [2, 3],
}

def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    if not raw or not raw.strip(): return []
    num_days = calendar.monthrange(year, month)[1]
    result: set[int] = set()
    for token in raw.replace(" ", "").split(","):
        if not token: continue
        if "/" in token:
            parts = token.rsplit("/", 1)
            token = parts[0]
            try:
                if int(parts[1]) != month: continue
            except: continue
        if "-" in token:
            bounds = token.split("-", 1)
            try:
                lo, hi = int(bounds[0]), int(bounds[1])
                for d in range(lo, hi + 1):
                    if 1 <= d <= num_days: result.add(d)
            except: pass
        else:
            try:
                d = int(token)
                if 1 <= d <= num_days: result.add(d)
            except: pass
    return sorted(result)

def get_day_type(d: int, year: int, month: int, holidays: set) -> str:
    wd = date(year, month, d).weekday()
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    if d in holidays: return "hol"
    if (d + 1) in holidays: return "hol_eve"
    return "normal"

# ══════════════════════════════════════════════════════
# NEW BALANCED SCHEDULER WITH UPPER BOUND CAPS
# ══════════════════════════════════════════════════════

def build_schedule(
    doctors: list[str],
    year: int,
    month: int,
    holidays: set,
    personal_blocks: dict,
    personal_prefs: dict,
    shift_rules: dict
):
    num_days = calendar.monthrange(year, month)[1]
    num_docs = len(doctors)
    
    # חישוב מתמטי מדויק של גבולות עליונים להבטחת שוויון
    total_slots = num_days * 3 # 90 ל-30 יום
    heavy_slots = num_days * 2 # 60 ל-30 יום
    light_slots = num_days     # 30 ל-30 יום
    
    max_total_cap = (total_slots // num_docs) + (1 if total_slots % num_docs != 0 else 0)
    max_heavy_cap = (heavy_slots // num_docs) + (1 if heavy_slots % num_docs != 0 else 0)
    max_light_cap = (light_slots // num_docs) + (1 if light_slots % num_docs != 0 else 0)

    # ניסיונות הרצה מרובים למציאת פתרון חוקי (בגלל החסימות)
    for attempt in range(500):
        cnt1 = defaultdict(int)
        cnt2 = defaultdict(int)
        cnt3 = defaultdict(int)
        assignment = {}
        success = True
        
        # מעבר יום-יום, שומר על רצף סופ"ש לרופא במידת האפשר אך מוגבל במכסות קשיחות
        for day in range(1, num_days + 1):
            day_type = get_day_type(day, year, month, holidays)
            
            # בדיקה האם זה יום המשך של סופ"ש (שבת) כדי לשמור על רציפות אם המכסה מאפשרת
            is_weekend_continuation = (day_type == "sat" and day > 1)
            
            for shift in [1, 2, 3]:
                # מציאת מי ששובץ אתמול בטור הזה למקרה של רציפות סופ"ש
                prev_doc = assignment.get((day-1, shift), None) if is_weekend_continuation else None
                
                # סינון מועמדים לפי חוקים קשיחים ומכסות
                cands = []
                for d in doctors:
                    # 1. בדיקת חוקי טורים קשיחים וחסימות אישיות
                    if shift not in shift_rules.get(d, [1, 2, 3]): continue
                    if day in personal_blocks.get(d, []): continue
                    
                    # 2. מניעת כפילות באותו היום (אותו רופא לא יכול לעשות שני טורים באותו יום)
                    day_docs = [assignment.get((day, s)) for s in [1, 2, 3] if s != shift]
                    if d in day_docs: continue
                    
                    # 3. בדיקת מכסות קשיחות
                    if cnt1[d] + cnt2[d] + cnt3[d] >= max_total_cap: continue
                    if shift in [1, 2] and (cnt1[d] + cnt2[d]) >= max_heavy_cap: continue
                    if shift == 3 and cnt3[d] >= max_light_cap: continue
                    
                    cands.append(d)
                
                if not cands:
                    success = False
                    break
                
                # קביעת הרופא הנבחר
                if prev_doc and prev_doc in cands:
                    # שמירה על רצף סופ"ש (שישי-שבת)
                    chosen = prev_doc
                else:
                    # תיעדוף קודם כל לפי העדפות אישיות (Preferences) אם קיימות
                    pref_cands = [d for d in cands if day in personal_prefs.get(d, [])]
                    target_pool = pref_cands if pref_cands else cands
                    
                    # בחירה במי שיש לו הכי פחות שיבוצים בטור הנוכחי, ואז הכי פחות סה"כ
                    if shift in [1, 2]:
                        chosen = min(target_pool, key=lambda d: (cnt1[d] + cnt2[d], cnt1[d] + cnt2[d] + cnt3[d]))
                    else:
                        chosen = min(target_pool, key=lambda d: (cnt3[d], cnt1[d] + cnt2[d] + cnt3[d]))
                
                # רישום השיבוץ
                assignment[(day, shift)] = chosen
                if shift == 1: cnt1[chosen] += 1
                elif shift == 2: cnt2[chosen] += 1
                elif shift == 3: cnt3[chosen] += 1
                
            if not success: break
            
        if success:
            # בדיקה סופית שההפרשים אכן שוויוניים לחלוטין (הפרש <= 1)
            heavy_counts = [cnt1[d] + cnt2[d] for d in doctors]
            light_counts = [cnt3[d] for d in doctors]
            total_counts = [cnt1[d] + cnt2[d] + cnt3[d] for d in doctors]
            
            if (max(heavy_counts) - min(heavy_counts) <= 1 and 
                max(light_counts) - min(light_counts) <= 1 and 
                max(total_counts) - min(total_counts) <= 1):
                
                # סיכום לטבלת תצוגה
                active_days = {d: cnt1[d] + cnt2[d] for d in doctors}
                passive_days = {d: cnt3[d] for d in doctors}
                pref_granted = defaultdict(int)
                for (day, shift), doc in assignment.items():
                    if shift in (1, 2) and day in personal_prefs.get(doc, []):
                        pref_granted[doc] += 1
                        
                return assignment, active_days, passive_days, dict(pref_granted)

    # אם אחרי 500 ניסיונות בגלל אילוצי חסימות קשים לא נמצא פתרון מושלם, נחזיר ריק
    return {}, {}, {}, {}

# ══════════════════════════════════════════════════════
# UI & RENDERERS (ללא שינוי, תואם לגרסה הקודמת)
# ══════════════════════════════════════════════════════

def render_calendar(year, month, assignment, color_map, holidays, personal_prefs) -> str:
    cal  = calendar.Calendar(firstweekday=6)
    head = "".join(f"<th>{d}</th>" for d in HEBREW_DAYS)
    body = ""
    for week in cal.monthdayscalendar(year, month):
        row = "<tr>"
        for day in week:
            if day == 0:
                row += '<td class="empty"></td>'
                continue
            dtype   = get_day_type(day, year, month, holidays)
            td_cls  = {"fri":"fri-td","sat":"sat-td","hol":"hol-td","hol_eve":"hol-td"}.get(dtype, "")
            day_lbl = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
            hol_ico = " ✡" if dtype in ("hol","hol_eve") else ("🕯" if dtype == "fri" else "")
            cells = ""
            for shift, badge_cls in [(1,"badge-heavy"),(2,"badge-heavy"),(3,"badge-light")]:
                doc = assignment.get((day, shift), "—")
                col = color_map.get(doc, "#aaa")
                label = SHIFT_LABELS[shift].split()[0]
                is_pref = (shift in (1, 2)) and (day in personal_prefs.get(doc, []))
                extra_cls = " badge-pref" if is_pref else ""
                cells += (f'<span class="badge {badge_cls}{extra_cls}" '
                          f'style="background:{col}">{label}: {doc}</span>')
            row += (f'<td class="{td_cls}">'
                    f'<span class="day-num">{day} {day_lbl}{hol_ico}</span>'
                    f'{cells}</td>')
        body += row + "</tr>"
    return (f'<div class="cal-wrap"><table class="cal-table">'
            f'<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')

def render_fairness(doctors, heavy, light, color_map, personal_prefs, pref_granted) -> str:
    max_h = max((heavy.get(d, 0) for d in doctors), default=1)
    max_l = max((light.get(d, 0) for d in doctors), default=1)
    rows  = ""
    for doc in sorted(doctors, key=lambda d: -(heavy.get(d,0) + light.get(d,0))):
        h, l = heavy.get(doc, 0), light.get(doc, 0)
        col  = color_map.get(doc, "#999")
        ph   = int(h / max_h * 100) if max_h else 0
        pl   = int(l / max_l * 100) if max_l else 0
        req     = len(personal_prefs.get(doc, []))
        granted = pref_granted.get(doc, 0)
        pref_cell = (f"<span style='color:#1e8449;font-weight:600'>{granted}</span><span style='color:#888'>/{req}</span>" if req > 0 else "<span style='color:#bbb'>—</span>")
        name_badge = f'<span style="background:{col};color:#fff;padding:2px 9px;border-radius:10px;font-weight:600">{doc}</span>'
        bar_h = f'<div class="bar-wrap"><div class="bar-fill" style="width:{ph}%;background:#2980b9"></div></div>'
        bar_l = f'<div class="bar-wrap"><div class="bar-fill" style="width:{pl}%;background:#27ae60"></div></div>'
        rows += (f"<tr><td>{name_badge}</td><td>{h}</td><td>{bar_h}</td><td>{l}</td><td>{bar_l}</td><td>{h+l}</td><td>{pref_cell}</td></tr>")
    return (f'<table class="fair-table"><thead><tr><th>רופא</th><th>ימי כבד (1+2)</th><th>פילוג כבד</th><th>ימי פסיבי (3)</th><th>פילוג פסיבי</th><th>סה"כ ימים</th><th>העדפות (אקטיבי)</th></tr></thead><tbody>{rows}</tbody></table>')

st.markdown('<div class="main-title">🏥 ניהול כוננויות - גרסה מתוקנת ומאוזנת</div>', unsafe_allow_html=True)

with st.expander("⚙️ הגדרות", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        doctors_input = st.text_area("👨‍⚕️ רשימת רופאים", value="\n".join(DEFAULT_DOCTORS), height=160)
    with c2:
        today = date.today()
        sel_month = st.selectbox("📅 חודש", list(range(1, 13)), index=5, format_func=lambda m: HEBREW_MONTHS[m - 1]) # ברירת מחדל יוני
    with c3:
        sel_year = st.selectbox("📆 שנה", list(range(today.year - 1, today.year + 4)), index=1)
    holidays_raw = st.text_input("✡️ ימי חג / ערב-חג:", value="", placeholder="2-4/10, 14/04")

doctors = [d.strip() for d in doctors_input.strip().splitlines() if d.strip()]
personal_blocks = {}
personal_prefs = {}
shift_rules = {}

with st.expander("🚫 חסימות והעדפות"):
    cols = st.columns(2)
    for i, doc in enumerate(doctors):
        with cols[i % 2]:
            st.markdown(f"**{doc}**")
            b = st.text_input(f"חסימות {doc}", key=f"b_{doc}", placeholder="1-5")
            p = st.text_input(f"העדפות {doc}", key=f"p_{doc}", placeholder="10,12")
            dflt_s = DEFAULT_SHIFT_RULES.get(doc, [1, 2, 3])
            s = st.multiselect(f"טורים {doc}", [1, 2, 3], default=dflt_s, format_func=lambda x: SHIFT_LABELS[x], key=f"s_{doc}")
            personal_blocks[doc] = parse_day_ranges(b, sel_year, sel_month)
            personal_prefs[doc] = parse_day_ranges(p, sel_year, sel_month)
            shift_rules[doc] = s or [1, 2, 3]

st.markdown("---")
run_btn = st.button("✨ צור סידור אופטימלי")

if run_btn:
    if len(doctors) < 3:
        st.error("⚠️ יש להזין לפחות 3 רופאים.")
    else:
        holidays = set(parse_day_ranges(holidays_raw, sel_year, sel_month))
        assignment, heavy, light, pref_granted = build_schedule(doctors, sel_year, sel_month, holidays, personal_blocks, personal_prefs, shift_rules)
        
        if not assignment:
            st.error("❌ לא ניתן היה ליצור סידור המאזן את הטורים בצורה מושלמת תחת אילוצי החסימות הנוכחיים. נסה להפחית חסימות קשיחות.")
        else:
            color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}
            st.markdown(f"### 📋 לוח כוננויות - {HEBREW_MONTHS[sel_month-1]} {sel_year}")
            st.markdown(render_calendar(sel_year, sel_month, assignment, color_map, holidays, personal_prefs), unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown('<div class="sec-header">📊 טבלת צדק מתוקנת ומאוזנת מתמטית</div>', unsafe_allow_html=True)
            st.markdown(render_fairness(doctors, heavy, light, color_map, personal_prefs, pref_granted), unsafe_allow_html=True)
            
            df_export = []
            for day in range(1, calendar.monthrange(sel_year, sel_month)[1] + 1):
                df_export.append({
                    "תאריך": f"{day:02d}/{sel_month:02d}/{sel_year}",
                    "טור 1": assignment.get((day, 1), "—"),
                    "טור 2": assignment.get((day, 2), "—"),
                    "טור 3": assignment.get((day, 3), "—"),
                })
            csv = pd.DataFrame(df_export).to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ הורד כ-CSV מתוקן", csv, f"schedule_{sel_month}_{sel_year}.csv", "text/csv")
