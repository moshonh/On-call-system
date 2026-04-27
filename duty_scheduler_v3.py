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
# CONSTANTS
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

DEFAULT_ALLOWED = {
    "הרשקוביץ מ'": [1, 3],
    "טלמן ג'":      [1, 3],
    "שלי ש'":       [1, 3],
    "סאימן א'":     [2, 3],
    "דנין י'":      [2, 3],
}

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    if not raw or not raw.strip():
        return []
    num_days = calendar.monthrange(year, month)[1]
    result: set[int] = set()
    for token in raw.replace(" ", "").split(","):
        if not token:
            continue
        if "/" in token:
            parts = token.rsplit("/", 1)
            token = parts[0]
            try:
                if int(parts[1]) != month:
                    continue
            except Exception:
                continue
        if "-" in token:
            bounds = token.split("-", 1)
            try:
                lo, hi = int(bounds[0]), int(bounds[1])
                for d in range(lo, hi + 1):
                    if 1 <= d <= num_days:
                        result.add(d)
            except Exception:
                pass
        else:
            try:
                d = int(token)
                if 1 <= d <= num_days:
                    result.add(d)
            except Exception:
                pass
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
                else:
                    break
            if (nxt <= num_days
                    and get_day_type(nxt, year, month, holidays) == "sat"
                    and nxt not in used):
                block_days.append(nxt)
                used.add(nxt)
            is_coupled = len(block_days) > 1
            blocks.append({"days": block_days, "coupled": is_coupled})
        else:
            blocks.append({"days": [d], "coupled": False})
        used.add(d)
        d += 1
    return blocks


def eligible(doc: str, shift: int, block_days: list, personal_blocks: dict, shift_rules: dict) -> bool:
    if shift not in shift_rules.get(doc, [1, 2, 3]):
        return False
    return not any(day in personal_blocks.get(doc, []) for day in block_days)


def block_has_preference(doc: str, block_days: list, personal_prefs: dict) -> bool:
    return any(day in personal_prefs.get(doc, []) for day in block_days)


# ══════════════════════════════════════════════════════
# CORE SCHEDULER
# ══════════════════════════════════════════════════════

def build_schedule(
    doctors: list[str],
    year: int,
    month: int,
    holidays: set,
    personal_blocks: dict,
    personal_prefs: dict,
    shift_rules: dict,
) -> tuple[dict, dict, dict, dict]:
    blocks = build_coupled_blocks(year, month, holidays)
    
    # Initialize counters
    # Active duties (1+2) are counted together for fairness
    active_counts = defaultdict(int)
    passive_counts = defaultdict(int)
    total_counts = defaultdict(int)
    pref_granted = defaultdict(int)
    assignment = {}

    def get_candidates(shift: int, days: list, exclude: set) -> list[str]:
        c = [d for d in doctors
             if eligible(d, shift, days, personal_blocks, shift_rules)
             and d not in exclude]
        return c

    def pick_best(candidates: list[str], primary_counts: dict, secondary_counts: dict, days: list) -> str:
        if not candidates:
            return ""
        
        # 1. Minimize primary count (active or passive)
        min_p = min(primary_counts[d] for d in candidates)
        l1 = [d for d in candidates if primary_counts[d] == min_p]
        
        # 2. Minimize total count
        min_t = min(total_counts[d] for d in l1)
        l2 = [d for d in l1 if total_counts[d] == min_t]
        
        # 3. Preference
        pref = [d for d in l2 if block_has_preference(d, days, personal_prefs)]
        
        return random.choice(pref if pref else l2)

    # Step 1: Assign Active Duties (1 and 2)
    # We iterate through blocks to ensure coupled days get the same doctor
    for blk in blocks:
        days = blk["days"]
        
        # Assign Shift 1
        cands1 = get_candidates(1, days, set())
        chosen1 = pick_best(cands1, active_counts, total_counts, days)
        if not chosen1:
            # Fallback if no one is eligible
            chosen1 = random.choice([d for d in doctors if 1 in shift_rules.get(d, [1,2,3])])
            
        for d in days:
            assignment[(d, 1)] = chosen1
        active_counts[chosen1] += 1
        total_counts[chosen1] += 1
        if block_has_preference(chosen1, days, personal_prefs):
            pref_granted[chosen1] += 1

        # Assign Shift 2
        # Exclude doctor assigned to Shift 1 on these days
        cands2 = get_candidates(2, days, {chosen1})
        chosen2 = pick_best(cands2, active_counts, total_counts, days)
        if not chosen2:
            # Fallback
            potential = [d for d in doctors if 2 in shift_rules.get(d, [1,2,3]) and d != chosen1]
            chosen2 = random.choice(potential if potential else doctors)
            
        for d in days:
            assignment[(d, 2)] = chosen2
        active_counts[chosen2] += 1
        total_counts[chosen2] += 1
        if block_has_preference(chosen2, days, personal_prefs):
            pref_granted[chosen2] += 1

    # Step 2: Assign Passive Duties (3)
    # Passive duties are assigned day by day for maximum flexibility, 
    # but we still respect the "no same doctor twice" rule.
    num_days = calendar.monthrange(year, month)[1]
    for d in range(1, num_days + 1):
        already_assigned = {assignment.get((d, 1)), assignment.get((d, 2))} - {None}
        cands3 = get_candidates(3, [d], already_assigned)
        chosen3 = pick_best(cands3, passive_counts, total_counts, [d])
        if not chosen3:
            # Fallback
            potential = [doc for doc in doctors if 3 in shift_rules.get(doc, [1,2,3]) and doc not in already_assigned]
            chosen3 = random.choice(potential if potential else doctors)
            
        assignment[(d, 3)] = chosen3
        passive_counts[chosen3] += 1
        total_counts[chosen3] += 1
        if block_has_preference(chosen3, [d], personal_prefs):
            pref_granted[chosen3] += 1

    # Prepare display counts (actual days)
    disp_active = defaultdict(int)
    disp_passive = defaultdict(int)
    for (d, s), doc in assignment.items():
        if s in (1, 2):
            disp_active[doc] += 1
        else:
            disp_passive[doc] += 1

    return assignment, dict(disp_active), dict(disp_passive), dict(pref_granted)


# ══════════════════════════════════════════════════════
# RENDERERS
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
        pref_cell = (
            f"<span style='color:#1e8449;font-weight:600'>{granted}</span>"
            f"<span style='color:#888'>/{req}</span>"
            if req > 0 else "<span style='color:#bbb'>—</span>"
        )
        name_badge = (
            f'<span style="background:{col};color:#fff;'
            f'padding:2px 9px;border-radius:10px;font-weight:600">{doc}</span>'
        )
        bar_h = (f'<div class="bar-wrap"><div class="bar-fill" '
                 f'style="width:{ph}%;background:#2980b9"></div></div>')
        bar_l = (f'<div class="bar-wrap"><div class="bar-fill" '
                 f'style="width:{pl}%;background:#27ae60"></div></div>')
        rows += (f"<tr><td>{name_badge}</td>"
                 f"<td>{h}</td><td>{bar_h}</td>"
                 f"<td>{l}</td><td>{bar_l}</td>"
                 f"<td>{h+l}</td><td>{pref_cell}</td></tr>")
    return (
        '<table class="fair-table"><thead><tr>'
        "<th>רופא</th>"
        "<th>ימי כבד (1+2)</th><th>פילוג כבד</th>"
        "<th>ימי פסיבי (3)</th><th>פילוג פסיבי</th>"
        "<th>סה\"כ ימים</th>"
        "<th>העדפות שמומשו</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def build_export_df(year, month, assignment, holidays) -> pd.DataFrame:
    num_days = calendar.monthrange(year, month)[1]
    rows = []
    for day in range(1, num_days + 1):
        dtype    = get_day_type(day, year, month, holidays)
        day_name = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
        rows.append({
            "תאריך":          f"{day:02d}/{month:02d}/{year}",
            "יום":            day_name,
            "סוג":            {"fri":"שישי","sat":"שבת","hol":"חג","hol_eve":"ערב-חג","normal":"רגיל"}.get(dtype, "רגיל"),
            "טור 1 (כבד)":   assignment.get((day, 1), "—"),
            "טור 2 (כבד)":   assignment.get((day, 2), "—"),
            "טור 3 (פסיבי)": assignment.get((day, 3), "—"),
        })
    return pd.DataFrame(rows)


def build_excel(year, month, assignment, heavy, light, holidays, personal_prefs, pref_granted) -> bytes:
    df_sched = build_export_df(year, month, assignment, holidays)
    all_docs  = sorted(set(list(heavy.keys()) + list(light.keys())))
    fair_rows = [
        {
            "רופא":              d,
            "ימי כבד":            heavy.get(d, 0),
            "ימי פסיבי":          light.get(d, 0),
            "סה\"כ ימים":         heavy.get(d, 0) + light.get(d, 0),
            "העדפות שביקש":      len(personal_prefs.get(d, [])),
            "העדפות שמומשו":     pref_granted.get(d, 0),
        }
        for d in all_docs
    ]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_sched.to_excel(w, sheet_name="סידור",    index=False)
        pd.DataFrame(fair_rows).to_excel(w, sheet_name="טבלת צדק", index=False)
    return buf.getvalue()


# ══════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════

st.markdown('<div class="main-title">🏥 ניהול כוננויות – לוח חודשי</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    'חלוקה שוויונית: טור 3 פסיבי בנפרד · טורים 1+2 כבד יחד · הפרש מקסימלי 1'
    '</div>',
    unsafe_allow_html=True,
)

# ── הגדרות בסיסיות ──
with st.expander("⚙️ הגדרות בסיסיות", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        doctors_input = st.text_area(
            "👨‍⚕️ רשימת רופאים (שם אחד בכל שורה)",
            value="הרשקוביץ מ'\nטלמן ג'\nשלי ש'\nסאימן א'\nדנין י'\nד\"ר כהן\nד\"ר לוי\nד\"ר פרץ",
            height=160,
        )
    with c2:
        today     = date.today()
        sel_month = st.selectbox(
            "📅 חודש", list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: HEBREW_MONTHS[m - 1],
        )
    with c3:
        sel_year = st.selectbox(
            "📆 שנה",
            list(range(today.year - 1, today.year + 4)),
            index=1,
        )

    st.markdown(
        '<div class="info-box">חגים – פורמטים: <code>14</code> , '
        '<code>2-4</code> , <code>1-3/10</code> , '
        '<code>2-4/10,14/04</code></div>',
        unsafe_allow_html=True,
    )
    holidays_raw = st.text_input("✡️ ימי חג / ערב-חג:", value="", placeholder="2-4/10, 14/04")

doctors_preview = [d.strip() for d in doctors_input.strip().splitlines() if d.strip()]

# ── חסימות קשות ──
personal_blocks: dict = {}
with st.expander("🚫 חסימות קשות – ימים שהרופא לא יכול"):
    st.markdown(
        '<div class="info-box">פורמטים: <code>1-5</code> , '
        '<code>7,12</code> , <code>1-3,8,20-22</code></div>',
        unsafe_allow_html=True,
    )
    cols_blk = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_blk[i % 2]:
            raw = st.text_input(f"🚫 {doc}", key=f"blk_{doc}", placeholder="1-5, 14, 20-22")
            personal_blocks[doc] = parse_day_ranges(raw, sel_year, sel_month)

# ── העדפות רכות ──
personal_prefs: dict = {}
with st.expander("⭐ העדפות רכות – ימים שהרופא מעדיף"):
    st.markdown(
        '<div class="pref-box">המערכת <b>תעדיף</b> לשבץ את הרופא בימים אלה '
        '– בתנאי שזה לא פוגע בשוויון. ★ מסמן מימוש.</div>',
        unsafe_allow_html=True,
    )
    cols_prf = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_prf[i % 2]:
            raw_p = st.text_input(f"⭐ {doc}", key=f"prf_{doc}", placeholder="10-12, 20, 25")
            personal_prefs[doc] = parse_day_ranges(raw_p, sel_year, sel_month)

# ── טורים מותרים ──
shift_rules: dict = {}
with st.expander("🔧 טורים מותרים לכל רופא"):
    st.markdown(
        '<div class="info-box"><b>סל כבד</b> = טורים 1+2 · '
        '<b>סל פסיבי</b> = טור 3</div>',
        unsafe_allow_html=True,
    )
    cols_sr = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        dflt = DEFAULT_ALLOWED.get(doc, [1, 2, 3])
        allowed = st.multiselect(
            f"{doc}", options=[1, 2, 3], default=dflt,
            format_func=lambda x: SHIFT_LABELS[x],
            key=f"sr_{doc}",
        )
        shift_rules[doc] = allowed or [1, 2, 3]

# ── כפתור הרצה + זרע ──
st.markdown("---")
bc, sc = st.columns([2, 1])
with bc:
    run_btn = st.button("✨ צור סידור כוננויות")
with sc:
    seed = st.number_input("🎲 זרע אקראיות (0=אקראי)", min_value=0, value=0, step=1)

# ══════════════════════════════════════════════════════
# GENERATE & DISPLAY
# ══════════════════════════════════════════════════════
if run_btn:
    doctors = doctors_preview
    if len(doctors) < 3:
        st.error("⚠️ יש להזין לפחות 3 רופאים.")
        st.stop()

    if seed > 0:
        random.seed(seed)

    holidays  = set(parse_day_ranges(holidays_raw, sel_year, sel_month))
    color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}

    # אזהרות
    warns = [f"⚠️ {d} – אין טורים מותרים!" for d in doctors if not shift_rules.get(d)]
    if warns:
        st.markdown(
            '<div class="warn-box">' + "<br>".join(warns) + "</div>",
            unsafe_allow_html=True,
        )

    assignment, heavy, light, pref_granted = build_schedule(
        doctors, sel_year, sel_month, holidays,
        personal_blocks, personal_prefs, shift_rules,
    )

    # ── סיכום העדפות ──
    total_req     = sum(len(v) for v in personal_prefs.values() if v)
    total_granted = sum(pref_granted.values())
    if total_req > 0:
        pct = int(total_granted / total_req * 100)
        st.markdown(
            f'<div class="pref-box">⭐ <b>העדפות שמומשו:</b> '
            f'{total_granted} מתוך {total_req} ({pct}%) · '
            f'ימים שמומשו מסומנים ב-★ בלוח</div>',
            unsafe_allow_html=True,
        )

    # ── לוח שנה ──
    st.markdown(f"### 📋 לוח כוננויות – {HEBREW_MONTHS[sel_month-1]} {sel_year}")
    if holidays:
        st.markdown(
            f'<div class="info-box">ימי חג: '
            f'{", ".join(str(d) for d in sorted(holidays))}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        render_calendar(sel_year, sel_month, assignment, color_map, holidays, personal_prefs),
        unsafe_allow_html=True,
    )

    # ── טבלת צדק ──
    st.markdown("---")
    st.markdown(
        '<div class="sec-header">📊 טבלת צדק – שני סלים</div>',
        unsafe_allow_html=True,
    )

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        st.markdown(
            render_fairness(doctors, heavy, light, color_map, personal_prefs, pref_granted),
            unsafe_allow_html=True,
        )
    with fc2:
        # ── חישוב הפרשים ──
        h_vals = [heavy.get(d, 0) for d in doctors if 1 in shift_rules.get(d, []) or 2 in shift_rules.get(d, [])]
        l_vals = [light.get(d, 0) for d in doctors if 3 in shift_rules.get(d, [])]
        t_vals = [heavy.get(d, 0) + light.get(d, 0) for d in doctors]

        g1 = max(h_vals) - min(h_vals) if h_vals else 0
        g2 = max(l_vals) - min(l_vals) if l_vals else 0
        g3 = max(t_vals) - min(t_vals) if t_vals else 0

        st.metric("הפרש כבד (1+2)", str(g1), help="הפרש ימי כבד בין הרופאים")
        st.metric("הפרש פסיבי (3)", str(g2), help="הפרש ימי פסיבי בין הרופאים")
        st.metric("הפרש סה\"כ", str(g3), help="הפרש סך כל הימים")

        if g1 <= 1 and g2 <= 1 and g3 <= 1:
            st.success("✅ חלוקה הוגנת")
        else:
            st.warning("⚠️ נסה זרע אחר לאיזון טוב יותר")

    # ══════════════════════════════════════════
    # ייצוא – CSV + Excel
    # ══════════════════════════════════════════
    st.markdown("---")
    st.markdown('<div class="sec-header">📥 ייצוא</div>', unsafe_allow_html=True)

    df_export = build_export_df(sel_year, sel_month, assignment, holidays)

    ex1, ex2 = st.columns(2)

    with ex1:
        csv_bytes = df_export.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ הורד כ-CSV",
            data=csv_bytes,
            file_name=f"כוננויות_{HEBREW_MONTHS[sel_month-1]}_{sel_year}.csv",
            mime="text/csv",
        )

    with ex2:
        try:
            excel_bytes = build_excel(
                sel_year, sel_month, assignment,
                heavy, light, holidays,
                personal_prefs, pref_granted,
            )
            st.download_button(
                label="📊 הורד כ-Excel",
                data=excel_bytes,
                file_name=f"כוננויות_{HEBREW_MONTHS[sel_month-1]}_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.info("להורדת Excel: `pip install openpyxl`")
