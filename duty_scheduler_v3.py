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
st.set_page_config(page_title="ניהול כוננויות - גרסה סופית", page_icon="🏥", layout="wide")

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
.info-box  { background:#e8f4fd; border:1px solid #aed6f1; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#1a5276; margin:.4rem 0; }
.pref-box  { background:#eafaf1; border:1px solid #a9dfbf; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#1e8449; margin:.4rem 0; }
.warn-box  { background:#fff8e1; border:1px solid #ffe082; border-radius:8px; padding:.6rem 1rem; font-size:.83rem; color:#7a5800; margin:.4rem 0; }
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

# Hardcoded doctor list from the provided CSV
DEFAULT_DOCTORS = [
    "הרשקוביץ מ'", "דנין י'", "דומני א:", "סאימן א'", "שלי ש'", 
    "הלר א'", "טלמן ג'", "שיפרין-בונ", "רוזנברג א'", "חטיב מ'", "ווינר ר'"
]

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    if not raw or not raw.strip():
        return []
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
    wd = date(year, month, d).weekday()  # 0=Mon … 5=Sat, 6=Sun
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    if d in holidays: return "hol"
    if (d + 1) in holidays: return "hol_eve"
    return "normal"

def build_coupled_blocks(year: int, month: int, holidays: set) -> list[dict]:
    num_days = calendar.monthrange(year, month)[1]
    used: set[int] = set()
    blocks: list[dict] = []
    d = 1
    while d <= num_days:
        if d in used:
            d += 1
            continue
        dtype = get_day_type(d, year, month, holidays)
        if dtype in ("fri", "hol", "hol_eve"):
            block_days = [d]
            nxt = d + 1
            while nxt <= num_days:
                nt = get_day_type(nxt, year, month, holidays)
                if nt in ("sat", "hol", "hol_eve"):
                    block_days.append(nxt)
                    used.add(nxt)
                    nxt += 1
                else: break
            if (nxt <= num_days and get_day_type(nxt, year, month, holidays) == "sat" and nxt not in used):
                block_days.append(nxt)
                used.add(nxt)
            blocks.append({"days": block_days, "coupled": len(block_days) > 1})
        else:
            blocks.append({"days": [d], "coupled": False})
        used.add(d)
        d += 1
    return blocks

# ══════════════════════════════════════════════════════
# CORE SCHEDULER (MULTI-PASS OPTIMIZATION)
# ══════════════════════════════════════════════════════

def build_schedule(
    doctors: list[str],
    year: int,
    month: int,
    holidays: set,
    personal_blocks: dict,
    personal_prefs: dict,
    shift_rules: dict,
    max_attempts: int = 100
):
    best_assignment = None
    best_score = float('inf')
    
    num_days = calendar.monthrange(year, month)[1]
    blocks = build_coupled_blocks(year, month, holidays)

    for attempt in range(max_attempts):
        assignment = {}
        active_counts = {d: 0 for d in doctors}
        passive_counts = {d: 0 for d in doctors}
        total_counts = {d: 0 for d in doctors}
        
        # Helper to pick candidate with lowest counts
        def pick(cands, primary_cnt, secondary_cnt, days):
            if not cands: return None
            # Sort by primary count, then secondary count, then random
            random.shuffle(cands)
            cands.sort(key=lambda d: (primary_cnt[d], secondary_cnt[d]))
            
            # Try to satisfy preference if it doesn't break fairness
            min_p = primary_cnt[cands[0]]
            fair_cands = [d for d in cands if primary_cnt[d] == min_p]
            pref_cands = [d for d in fair_cands if any(day in personal_prefs.get(d, []) for day in days)]
            return pref_cands[0] if pref_cands else cands[0]

        success = True
        
        # Pass 1: Active Duties (1+2)
        for blk in blocks:
            days = blk["days"]
            # Shift 1
            c1 = [d for d in doctors if 1 in shift_rules.get(d, [1,2,3]) and not any(day in personal_blocks.get(d, []) for day in days)]
            chosen1 = pick(c1, active_counts, total_counts, days)
            if not chosen1: 
                success = False; break
            for d in days: assignment[(d, 1)] = chosen1
            active_counts[chosen1] += 1
            total_counts[chosen1] += 1
            
            # Shift 2
            c2 = [d for d in doctors if 2 in shift_rules.get(d, [1,2,3]) and d != chosen1 and not any(day in personal_blocks.get(d, []) for day in days)]
            chosen2 = pick(c2, active_counts, total_counts, days)
            if not chosen2: 
                success = False; break
            for d in days: assignment[(d, 2)] = chosen2
            active_counts[chosen2] += 1
            total_counts[chosen2] += 1
            
        if not success: continue

        # Pass 2: Passive Duties (3)
        for d in range(1, num_days + 1):
            already = {assignment.get((d, 1)), assignment.get((d, 2))}
            c3 = [doc for doc in doctors if 3 in shift_rules.get(doc, [1,2,3]) and doc not in already and d not in personal_blocks.get(doc, [])]
            chosen3 = pick(c3, passive_counts, total_counts, [d])
            if not chosen3:
                success = False; break
            assignment[(d, 3)] = chosen3
            passive_counts[chosen3] += 1
            total_counts[chosen3] += 1
            
        if not success: continue

        # Calculate Fairness Score (Max Diff)
        # We want diff <= 1 for active, passive, and total
        active_diff = max(active_counts.values()) - min(active_counts.values())
        passive_diff = max(passive_counts.values()) - min(passive_counts.values())
        total_diff = max(total_counts.values()) - min(total_counts.values())
        
        score = active_diff + passive_diff + total_diff
        
        if score < best_score:
            best_score = score
            best_assignment = (assignment, active_counts, passive_counts)
            if score <= 3: # Perfect score (1+1+1)
                break

    if not best_assignment:
        return None, {}, {}, {}

    # Convert counts to actual days for display
    final_assignment, active_blks, passive_days = best_assignment
    disp_active = defaultdict(int)
    disp_passive = defaultdict(int)
    pref_granted = defaultdict(int)
    
    for (d, s), doc in final_assignment.items():
        if s in (1, 2): disp_active[doc] += 1
        else: disp_passive[doc] += 1
        if d in personal_prefs.get(doc, []): pref_granted[doc] += 1
            
    return final_assignment, dict(disp_active), dict(disp_passive), dict(pref_granted)

# ══════════════════════════════════════════════════════
# UI & RENDERERS
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
                is_pref = day in personal_prefs.get(doc, [])
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
    return (f'<table class="fair-table"><thead><tr><th>רופא</th><th>ימי כבד (1+2)</th><th>פילוג כבד</th><th>ימי פסיבי (3)</th><th>פילוג פסיבי</th><th>סה"כ ימים</th><th>העדפות</th></tr></thead><tbody>{rows}</tbody></table>')

st.markdown('<div class="main-title">🏥 ניהול כוננויות - אופטימיזציה מלאה</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">איזון קשיח: הפרש מקסימלי 1 בכל הסלים · רשימת רופאים קבועה</div>', unsafe_allow_html=True)

with st.expander("⚙️ הגדרות", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        doctors_input = st.text_area("👨‍⚕️ רשימת רופאים", value="\n".join(DEFAULT_DOCTORS), height=160)
    with c2:
        today = date.today()
        sel_month = st.selectbox("📅 חודש", list(range(1, 13)), index=today.month - 1, format_func=lambda m: HEBREW_MONTHS[m - 1])
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
            s = st.multiselect(f"טורים {doc}", [1, 2, 3], default=[1, 2, 3], format_func=lambda x: SHIFT_LABELS[x], key=f"s_{doc}")
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
            st.error("❌ לא ניתן היה ליצור סידור העונה על כל החסימות הקשות. נסה להפחית חסימות.")
        else:
            color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}
            st.markdown(f"### 📋 לוח כוננויות - {HEBREW_MONTHS[sel_month-1]} {sel_year}")
            st.markdown(render_calendar(sel_year, sel_month, assignment, color_map, holidays, personal_prefs), unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown('<div class="sec-header">📊 טבלת צדק (הפרש מקסימלי 1)</div>', unsafe_allow_html=True)
            st.markdown(render_fairness(doctors, heavy, light, color_map, personal_prefs, pref_granted), unsafe_allow_html=True)
            
            # Export
            df_export = []
            for day in range(1, calendar.monthrange(sel_year, sel_month)[1] + 1):
                df_export.append({
                    "תאריך": f"{day:02d}/{sel_month:02d}/{sel_year}",
                    "טור 1": assignment.get((day, 1), "—"),
                    "טור 2": assignment.get((day, 2), "—"),
                    "טור 3": assignment.get((day, 3), "—"),
                })
            csv = pd.DataFrame(df_export).to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ הורד כ-CSV", csv, f"schedule_{sel_month}_{sel_year}.csv", "text/csv")
