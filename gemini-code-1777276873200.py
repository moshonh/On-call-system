import streamlit as st
import pandas as pd
import calendar
import random
import io
from datetime import date
from collections import defaultdict

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="ניהול כוננויות", page_icon="🏥", layout="wide")

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
.badge-pref::after { content: " ★"; font-size:.65rem; opacity:.9; }
.fair-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.87rem; }
.fair-table th { background:#1a3a5c; color:#fff; padding:8px 6px; text-align:center; }
.fair-table td { border:1px solid #d6e4f0; padding:6px 10px; text-align:center; }
.fair-table tr:nth-child(even) td { background:#f7fafd; }
.bar-wrap { background:#e8f0f8; border-radius:5px; height:13px; width:100%; }
.bar-fill { border-radius:5px; height:13px; }
div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:8px; padding:.5rem 1.6rem; font-family:'Heebo',sans-serif; font-size:.95rem; font-weight:600; }
div.stButton > button:hover { background:#2a5a8c; }
.stTextArea textarea, .stTextInput input { direction:rtl; font-family:'Heebo',sans-serif; }
.info-box  { background:#e8f4fd; border:1px solid #aed6f1; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#1a5276; margin:.4rem 0; }
.pref-box  { background:#eafaf1; border:1px solid #a9dfbf; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#1e8449; margin:.4rem 0; }
.warn-box  { background:#fff8e1; border:1px solid #ffe082; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#7a5800; margin:.4rem 0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════
COLORS = ["#2980b9","#27ae60","#8e44ad","#e67e22","#c0392b","#16a085","#d35400","#1a5276","#1abc9c","#922b21","#607d8b","#795548","#f39c12","#6c3483","#0e6655"]
HEBREW_DAYS = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
HEBREW_MONTHS = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
SHIFT_LABELS = {1:"טור 1 (כבד)", 2:"טור 2 (כבד)", 3:"טור 3 (פסיבי)"}

DEFAULT_ALLOWED = {
    "הרשקוביץ מ'": [1, 3],
    "טלמן ג'":      [1, 3],
    "שלי ש'":       [1, 3],
    "סאימן א'":     [2, 3],
    "דנין י'":      [2, 3],
}

def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
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

def get_day_type(d: int, year: int, month: int, holidays: set[int]) -> str:
    wd = date(year, month, d).weekday()
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    if d in holidays: return "hol"
    return "normal"

def build_coupled_blocks(year: int, month: int, holidays: set[int]) -> list[dict]:
    num_days = calendar.monthrange(year, month)[1]
    used: set[int] = set()
    blocks: list[dict] = []
    d = 1
    while d <= num_days:
        if d in used:
            d += 1
            continue
        dtype = get_day_type(d, year, month, holidays)
        if dtype in ("fri", "hol"):
            block_days = [d]
            nxt = d + 1
            while nxt <= num_days:
                nt = get_day_type(nxt, year, month, holidays)
                if nt in ("sat", "hol"):
                    block_days.append(nxt)
                    used.add(nxt)
                    nxt += 1
                else: break
            if nxt <= num_days and get_day_type(nxt, year, month, holidays) == "sat" and nxt not in used:
                block_days.append(nxt)
                used.add(nxt)
            blocks.append({"days": block_days, "coupled": len(block_days) > 1})
        else:
            blocks.append({"days": [d], "coupled": False})
        used.add(d)
        d += 1
    return blocks

def eligible(doc: str, shift: int, block_days: list[int], personal_blocks: dict, shift_rules: dict) -> bool:
    if shift not in shift_rules.get(doc, [1, 2, 3]): return False
    blocked = personal_blocks.get(doc, [])
    return not any(day in blocked for day in block_days)

def block_has_preference(doc: str, block_days: list[int], personal_prefs: dict) -> bool:
    prefs = personal_prefs.get(doc, [])
    return any(day in prefs for day in block_days)

# ══════════════════════════════════════════════════════
# CORE SCHEDULER LOGIC (REVISED V5)
# ══════════════════════════════════════════════════════

def pick_optimized(candidates: list[str], shift_type: int, block_days: list[int], days_count: dict, personal_prefs: dict) -> str:
    if not candidates: return ""
    
    # 1. חישוב סך ימים נוכחי לכל מועמד
    total_days = {d: sum(days_count[s][d] for s in [1, 2, 3]) for d in candidates}
    
    # 2. אילוץ שוויון בטור 3 (פסיבי) - אם זה הטור הנבחר
    if shift_type == 3:
        min_s3 = min(days_count[3][d] for d in candidates)
        candidates = [d for d in candidates if days_count[3][d] == min_s3]
    
    # 3. אילוץ שוויון כללי (הפרש עד 1)
    current_totals = {d: total_days[d] for d in candidates}
    min_total = min(current_totals.values())
    candidates = [d for d in candidates if current_totals[d] == min_total]
    
    # 4. העדפה רכה (Soft Preference)
    prefs = [d for d in candidates if block_has_preference(d, block_days, personal_prefs)]
    
    return random.choice(prefs if prefs else candidates)

def build_schedule(doctors: list[str], year: int, month: int, holidays: set[int], personal_blocks: dict, personal_prefs: dict, shift_rules: dict, fairness_tolerance: int = 1) -> tuple[dict, dict, dict, dict]:
    blocks = build_coupled_blocks(year, month, holidays)
    assignment: dict = {}
    days_count: dict = {1: defaultdict(int), 2: defaultdict(int), 3: defaultdict(int)}
    pref_granted: dict = defaultdict(int)

    def get_cands(shift: int, days: list[int], exclude: set) -> list[str]:
        c = [d for d in doctors if eligible(d, shift, days, personal_blocks, shift_rules) and d not in exclude]
        return c if c else [d for d in doctors if d not in exclude]

    # שלב א': חלוקת טור 3 (פסיבי) - הבטחת שוויון איכותי
    for blk in blocks:
        days = blk["days"]
        cands = get_cands(3, days, set())
        chosen = pick_optimized(cands, 3, days, days_count, personal_prefs)
        if not chosen: chosen = random.choice(doctors)
        for day in days:
            assignment[(day, 3)] = chosen
            days_count[3][chosen] += 1
        if block_has_preference(chosen, days, personal_prefs):
            pref_granted[chosen] += 1

    # שלב ב': חלוקת טורים 1+2 (כבד) - הבטחת שוויון כמותי
    for blk in blocks:
        days = blk["days"]
        for shift in [1, 2]:
            occupied = {assignment.get((days[0], s)) for s in [1, 2, 3] if s != shift} - {None}
            cands = get_cands(shift, days, occupied)
            chosen = pick_optimized(cands, shift, days, days_count, personal_prefs)
            if not chosen: chosen = random.choice(doctors)
            for day in days:
                assignment[(day, shift)] = chosen
                days_count[shift][chosen] += 1
            if block_has_preference(chosen, days, personal_prefs):
                pref_granted[chosen] += 1

    heavy_count = {d: days_count[1][d] + days_count[2][d] for d in doctors}
    light_count = {d: days_count[3][d] for d in doctors}
    return assignment, heavy_count, light_count, dict(pref_granted)

# ══════════════════════════════════════════════════════
# RENDERERS & UI
# ══════════════════════════════════════════════════════

def render_calendar(year, month, assignment, color_map, holidays, personal_prefs: dict) -> str:
    cal = calendar.Calendar(firstweekday=6)
    head = "".join(f"<th>{d}</th>" for d in HEBREW_DAYS)
    body = ""
    for week in cal.monthdayscalendar(year, month):
        row = "<tr>"
        for day in week:
            if day == 0:
                row += '<td class="empty"></td>'; continue
            dtype = get_day_type(day, year, month, holidays)
            td_cls = {"fri":"fri-td","sat":"sat-td","hol":"hol-td"}.get(dtype, "")
            day_lbl = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
            hol_ico = " ✡" if dtype == "hol" else ("🕯" if dtype == "fri" else "")
            cells = ""
            for shift, badge_cls in [(1,"badge-heavy"),(2,"badge-heavy"),(3,"badge-light")]:
                doc = assignment.get((day, shift), "—")
                col = color_map.get(doc, "#aaa")
                label = SHIFT_LABELS[shift].split()[0]
                is_pref = day in personal_prefs.get(doc, [])
                extra_cls = " badge-pref" if is_pref else ""
                cells += f'<span class="badge {badge_cls}{extra_cls}" style="background:{col}">{label}: {doc}</span>'
            row += f'<td class="{td_cls}"><span class="day-num">{day} {day_lbl}{hol_ico}</span>{cells}</td>'
        body += row + "</tr>"
    return f'<div class="cal-wrap"><table class="cal-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

def render_fairness(doctors, heavy, light, color_map, personal_prefs: dict, pref_granted: dict) -> str:
    max_h = max((heavy.get(d, 0) for d in doctors), default=1)
    max_l = max((light.get(d, 0) for d in doctors), default=1)
    rows = ""
    for doc in sorted(doctors, key=lambda d: -(heavy.get(d,0) + light.get(d,0))):
        h, l = heavy.get(doc, 0), light.get(doc, 0)
        col = color_map.get(doc, "#999")
        ph = int(h / max_h * 100) if max_h else 0
        pl = int(l / max_l * 100) if max_l else 0
        req, granted = len(personal_prefs.get(doc, [])), pref_granted.get(doc, 0)
        pref_cell = f"<span style='color:#1e8449;font-weight:600'>{granted}</span><span style='color:#888'>/{req}</span>" if req > 0 else "<span style='color:#bbb'>—</span>"
        name_badge = f'<span style="background:{col};color:#fff;padding:2px 9px;border-radius:10px;font-weight:600">{doc}</span>'
        bar_h = f'<div class="bar-wrap"><div class="bar-fill" style="width:{ph}%;background:#2980b9"></div></div>'
        bar_l = f'<div class="bar-wrap"><div class="bar-fill" style="width:{pl}%;background:#27ae60"></div></div>'
        rows += f"<tr><td>{name_badge}</td><td>{h}</td><td>{bar_h}</td><td>{l}</td><td>{bar_l}</td><td>{pref_cell}</td></tr>"
    return f'<table class="fair-table"><thead><tr><th>רופא</th><th>סל כבד (1+2)</th><th>פילוג כבד</th><th>סל פסיבי (3)</th><th>פילוג פסיבי</th><th>העדפות שמומשו</th></tr></thead><tbody>{rows}</tbody></table>'

def build_excel(year, month, assignment, heavy, light, holidays, personal_prefs, pref_granted) -> bytes:
    num_days = calendar.monthrange(year, month)[1]
    sched_rows = []
    for day in range(1, num_days + 1):
        dtype = get_day_type(day, year, month, holidays)
        day_name = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
        sched_rows.append({"תאריך": f"{day:02d}/{month:02d}/{year}", "יום": day_name, "סוג": {"fri":"שישי","sat":"שבת","hol":"חג","normal":"רגיל"}.get(dtype,"רגיל"), "טור 1 (כבד)": assignment.get((day, 1), "—"), "טור 2 (כבד)": assignment.get((day, 2), "—"), "טור 3 (פסיבי)": assignment.get((day, 3), "—")})
    all_docs = sorted(set(list(heavy.keys()) + list(light.keys())))
    fair_rows = [{"רופא": d, "סל כבד": heavy.get(d, 0), "סל פסיבי": light.get(d, 0), "סה\"כ": heavy.get(d, 0) + light.get(d, 0), "העדפות שביקש": len(personal_prefs.get(d, [])), "העדפות שמומשו": pref_granted.get(d, 0)} for d in all_docs]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(sched_rows).to_excel(w, sheet_name="סידור", index=False)
        pd.DataFrame(fair_rows).to_excel(w, sheet_name="טבלת צדק", index=False)
    return buf.getvalue()

# ══════════════════════════════════════════════════════
# UI PANELS
# ══════════════════════════════════════════════════════

st.markdown('<div class="main-title">🏥 ניהול כוננויות – לוח חודשי</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">הפרש מקסימלי 1 יום · ספירת ימי צמד · העדפות רכות · ייצוא Excel</div>', unsafe_allow_html=True)

with st.expander("⚙️ הגדרות בסיסיות", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        doctors_input = st.text_area("👨‍⚕️ רשימת רופאים", value="הרשקוביץ מ'\nטלמן ג'\nשלי ש'\nסאימן א'\nדנין י'\nד\"ר כהן\nד\"ר לוי\nד\"ר פרץ", height=150)
    with c2:
        sel_month = st.selectbox("📅 חודש", list(range(1,13)), index=date.today().month-1, format_func=lambda m: HEBREW_MONTHS[m-1])
    with c3:
        sel_year = st.selectbox("📆 שנה", list(range(date.today().year-1, date.today().year+4)), index=1)
    holidays_raw = st.text_input("✡️ ימי חג:", value="")

doctors_preview = [d.strip() for d in doctors_input.strip().splitlines() if d.strip()]

personal_blocks: dict = {}
with st.expander("🚫 חסימות קשות"):
    cols_blk = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_blk[i % 2]:
            raw = st.text_input(f"🚫 {doc}", key=f"blk_{doc}")
            personal_blocks[doc] = parse_day_ranges(raw, sel_year, sel_month)

personal_prefs: dict = {}
with st.expander("⭐ העדפות רכות"):
    cols_prf = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_prf[i % 2]:
            raw_p = st.text_input(f"⭐ {doc}", key=f"prf_{doc}")
            personal_prefs[doc] = parse_day_ranges(raw_p, sel_year, sel_month)

shift_rules: dict = {}
with st.expander("🔧 טורים מותרים"):
    cols_sr = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        dflt = DEFAULT_ALLOWED.get(doc, [1, 2, 3])
        with cols_sr[i % 2]:
            allowed = st.multiselect(f"{doc}", options=[1, 2, 3], default=dflt, format_func=lambda x: SHIFT_LABELS[x], key=f"sr_{doc}")
            shift_rules[doc] = allowed or [1, 2, 3]

st.markdown("---")
if st.button("✨ צור סידור כוננויות"):
    if len(doctors_preview) < 3:
        st.error("⚠️ יש להזין לפחות 3 רופאים.")
    else:
        holidays = parse_holidays(holidays_raw, sel_year, sel_month) if 'parse_holidays' in locals() else parse_day_ranges(holidays_raw, sel_year, sel_month)
        color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors_preview)}
        assignment, heavy, light, pref_granted = build_schedule(doctors_preview, sel_year, sel_month, set(parse_day_ranges(holidays_raw, sel_year, sel_month)), personal_blocks, personal_prefs, shift_rules)
        
        st.markdown(f"### 📋 לוח כוננויות – {HEBREW_MONTHS[sel_month-1]} {sel_year}")
        st.markdown(render_calendar(sel_year, sel_month, assignment, color_map, set(parse_day_ranges(holidays_raw, sel_year, sel_month)), personal_prefs), unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown('<div class="sec-header">📊 טבלת צדק – שני סלים + העדפות</div>', unsafe_allow_html=True)
        fc1, fc2 = st.columns([3, 1])
        with fc1:
            st.markdown(render_fairness(doctors_preview, heavy, light, color_map, personal_prefs, pref_granted), unsafe_allow_html=True)
        with fc2:
            h_vals = list(heavy.values()); l_vals = list(light.values())
            h_std = pd.Series(h_vals).std(); l_std = pd.Series(l_vals).std()
            st.metric("סטיית תקן – כבד", f"{h_std:.2f}"); st.metric("סטיית תקן – פסיבי", f"{l_std:.2f}")
            if (h_std + l_std) / 2 < 1.5: st.success("✅ חלוקה הוגנת מאוד")
            else: st.warning("⚠️ חלוקה סבירה")

        csv_exp = pd.DataFrame([{"תאריך": f"{d:02d}/{sel_month:02d}/{sel_year}", "טור 1": assignment.get((d,1),"—"), "טור 2": assignment.get((d,2),"—"), "טור 3": assignment.get((d,3),"—")} for d in range(1, calendar.monthrange(sel_year, sel_month)[1]+1)])
        st.download_button("📊 הורד Excel", data=build_excel(sel_year, sel_month, assignment, heavy, light, set(parse_day_ranges(holidays_raw, sel_year, sel_month)), personal_prefs, pref_granted), file_name=f"כוננויות_{sel_month}_{sel_year}.xlsx")