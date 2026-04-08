"""
ניהול כוננויות – גרסה 3
חידושים:
  • פענוח טווחי תאריכים (1-10/04)
  • שני סלים נפרדים: כבד (טור 1+2) ופסיבי (טור 3)
  • חוק צמד: שישי⟹שבת, ערב-חג⟹חג (נספר ×2)
  • ביטול הגבלת יומיים ברצף
"""

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
.sec-header  { font-size:1.05rem; font-weight:700; color:#1a3a5c;
               border-right:4px solid #2980b9; padding-right:10px; margin:1rem 0 .5rem; }

/* ── לוח שנה ── */
.cal-wrap { overflow-x:auto; }
.cal-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.8rem; min-width:720px; }
.cal-table th { background:#1a3a5c; color:#fff; padding:8px 4px;
                text-align:center; font-weight:700; border:1px solid #15304e; }
.cal-table td { border:1px solid #ccdde9; vertical-align:top;
                padding:5px 6px; background:#fff; min-width:105px; }
.cal-table td.empty  { background:#f0f4f8; }
.cal-table td.fri-td { background:#fef9ec !important; }
.cal-table td.sat-td { background:#fdf0f0 !important; }
.cal-table td.hol-td { background:#f5f0ff !important; }
.day-num { font-size:.7rem; color:#8aa3b8; font-weight:700; display:block; margin-bottom:3px; }

.badge { display:block; padding:2px 7px; border-radius:11px; font-size:.74rem;
         font-weight:600; color:#fff; margin-bottom:2px; white-space:nowrap;
         overflow:hidden; text-overflow:ellipsis; max-width:115px; }
.badge-heavy { border:2px solid rgba(255,255,255,.4); }
.badge-light { opacity:.85; font-style:italic; }

/* ── טבלת צדק ── */
.fair-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.87rem; }
.fair-table th { background:#1a3a5c; color:#fff; padding:8px 6px; text-align:center; }
.fair-table td { border:1px solid #d6e4f0; padding:6px 10px; text-align:center; }
.fair-table tr:nth-child(even) td { background:#f7fafd; }
.bar-wrap { background:#e8f0f8; border-radius:5px; height:13px; width:100%; }
.bar-fill { border-radius:5px; height:13px; }

/* ── כפתורים ── */
div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:8px;
    padding:.5rem 1.6rem; font-family:'Heebo',sans-serif; font-size:.95rem; font-weight:600; }
div.stButton > button:hover { background:#2a5a8c; }

.stTextArea textarea, .stTextInput input { direction:rtl; font-family:'Heebo',sans-serif; }

.info-box { background:#e8f4fd; border:1px solid #aed6f1; border-radius:8px;
            padding:.6rem 1rem; font-size:.83rem; color:#1a5276; margin:.4rem 0; }
.warn-box { background:#fff8e1; border:1px solid #ffe082; border-radius:8px;
            padding:.6rem 1rem; font-size:.83rem; color:#7a5800; margin:.4rem 0; }
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

SHIFT_LABELS = {1:"טור 1 (כבד)", 2:"טור 2 (כבד)", 3:"טור 3 (פסיבי)"}
HEAVY_SHIFTS  = {1, 2}   # סל כבד
LIGHT_SHIFTS  = {3}       # סל פסיבי

DEFAULT_ALLOWED = {
    "הרשקוביץ מ'": [1, 3],
    "טלמן ג'":      [1, 3],
    "שלי ש'":       [1, 3],
    "סאימן א'":     [2, 3],
    "דנין י'":      [2, 3],
}

# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════
st.markdown('<div class="main-title">🏥 ניהול כוננויות – לוח חודשי</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">שני סלים · חוק צמד · טווחי חסימה · ייצוא Excel</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# ① DATE-RANGE PARSER
# ══════════════════════════════════════════════════════
def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    """
    מפענח קלט חופשי של ימים/טווחים בפורמטים:
      • מספר בודד:   7
      • טווח:        1-10
      • עם חודש:     1-10/04   (רק אם החודש תואם)
      • מופרדים בפסיק: 3,7,1-5,12-15/04
    מחזיר רשימת ימים (int) ייחודיים בחודש הנבחר.
    """
    num_days = calendar.monthrange(year, month)[1]
    result: set[int] = set()

    for token in raw.replace(" ", "").split(","):
        if not token:
            continue
        # הסר הגדרת חודש (DD/MM או D-D/MM)
        month_filter = None
        if "/" in token:
            parts = token.rsplit("/", 1)
            token = parts[0]
            try:
                month_filter = int(parts[1])
            except ValueError:
                continue
            if month_filter != month:
                continue  # חודש אחר – מדלג

        # טווח או יום בודד
        if "-" in token:
            bounds = token.split("-", 1)
            try:
                lo, hi = int(bounds[0]), int(bounds[1])
                for d in range(lo, hi + 1):
                    if 1 <= d <= num_days:
                        result.add(d)
            except ValueError:
                pass
        else:
            try:
                d = int(token)
                if 1 <= d <= num_days:
                    result.add(d)
            except ValueError:
                pass

    return sorted(result)


def parse_holidays(raw: str, year: int, month: int) -> set[int]:
    """מפענח חגים (תומך בטווחים ובפורמט DD/MM)."""
    return set(parse_day_ranges(raw, year, month))


# ══════════════════════════════════════════════════════
# ② DAY-TYPE & BLOCK BUILDER
# ══════════════════════════════════════════════════════
def get_day_type(d: int, year: int, month: int, holidays: set[int]) -> str:
    wd = date(year, month, d).weekday()  # 0=Mon … 5=Sat, 6=Sun
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    if d in holidays: return "hol"
    return "normal"


def build_coupled_blocks(year: int, month: int, holidays: set[int]) -> list[dict]:
    """
    בונה רשימת בלוקים. כל בלוק:
      { "days": [d, ...], "coupled": bool }
    coupled=True ⟹ אותו רופא בכל ימי הבלוק, נספר ×len(days) במכסה.
    חוקי צימוד:
      • שישי + שבת שאחריו
      • ערב-חג + חג/ים שאחריו (כולל שבת צמודה)
    """
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
            # אסוף ימים צמודים
            block_days = [d]
            nxt = d + 1
            while nxt <= num_days:
                nt = get_day_type(nxt, year, month, holidays)
                if nt in ("sat", "hol"):
                    block_days.append(nxt)
                    used.add(nxt)
                    nxt += 1
                else:
                    break
            # גם שבת אחרי חג נצמדת
            if nxt <= num_days and get_day_type(nxt, year, month, holidays) == "sat" and nxt not in used:
                block_days.append(nxt)
                used.add(nxt)
            blocks.append({"days": block_days, "coupled": len(block_days) > 1})
        else:
            blocks.append({"days": [d], "coupled": False})

        used.add(d)
        d += 1

    return blocks


# ══════════════════════════════════════════════════════
# ③ SCHEDULER  (two-pool fair assignment)
# ══════════════════════════════════════════════════════
def eligible(doc: str, shift: int, block_days: list[int],
             personal_blocks: dict, shift_rules: dict) -> bool:
    """האם הרופא רשאי לקבל את הטור בבלוק זה?"""
    if shift not in shift_rules.get(doc, [1, 2, 3]):
        return False
    blocked = personal_blocks.get(doc, [])
    return not any(day in blocked for day in block_days)


def pick_doctor(candidates: list[str], pool_count: dict) -> str:
    """בוחר את הרופא עם הכי פחות כוננויות בסל, עם הגרלה בשוויון."""
    if not candidates:
        return ""
    min_c = min(pool_count.get(d, 0) for d in candidates)
    tied  = [d for d in candidates if pool_count.get(d, 0) == min_c]
    return random.choice(tied)


def build_schedule(
    doctors: list[str],
    year: int, month: int,
    holidays: set[int],
    personal_blocks: dict,
    shift_rules: dict,
) -> tuple[dict, dict, dict]:
    """
    מחזיר:
      assignment : dict[(day, shift)] -> doctor
      heavy_count: dict[doctor] -> int  (כוננויות כבדות, כולל צמד×2)
      light_count: dict[doctor] -> int  (כוננויות פסיביות, כולל צמד×2)
    """
    blocks = build_coupled_blocks(year, month, holidays)
    assignment: dict = {}
    heavy_count: dict = defaultdict(int)
    light_count: dict = defaultdict(int)

    for blk in blocks:
        days    = blk["days"]
        coupled = blk["coupled"]
        weight  = len(days)   # כמה נספר במכסה (1 או 2+)

        for shift in [1, 2, 3]:
            pool_count = heavy_count if shift in HEAVY_SHIFTS else light_count

            # מועמדים: רשאים לעשות את הטור בכל ימי הבלוק
            cands = [d for d in doctors if eligible(d, shift, days, personal_blocks, shift_rules)]

            # אם אין – הסר הגבלת הגבלות אישיות בלבד (שמור טורים)
            if not cands:
                cands = [d for d in doctors
                         if shift in shift_rules.get(d, [1, 2, 3])]
            # גיבוי אחרון
            if not cands:
                cands = doctors

            # אם צמד – אסור שאותו רופא יופיע בשני טורים שונים באותו בלוק
            already_in_block = {
                assignment.get((days[0], s))
                for s in [1, 2, 3] if s != shift
            } - {None}
            clean_cands = [d for d in cands if d not in already_in_block]
            if clean_cands:
                cands = clean_cands

            chosen = pick_doctor(cands, pool_count)
            if not chosen:
                chosen = random.choice(doctors)

            for day in days:
                assignment[(day, shift)] = chosen

            # עדכון מכסה: ×weight (יום רגיל=1, צמד שישי+שבת=2, וכו')
            if shift in HEAVY_SHIFTS:
                heavy_count[chosen] += weight
            else:
                light_count[chosen] += weight

    return assignment, dict(heavy_count), dict(light_count)


# ══════════════════════════════════════════════════════
# ④ CALENDAR RENDERER
# ══════════════════════════════════════════════════════
def render_calendar(year, month, assignment, color_map, holidays) -> str:
    cal  = calendar.Calendar(firstweekday=6)
    head = "".join(f"<th>{d}</th>" for d in HEBREW_DAYS)
    body = ""

    for week in cal.monthdayscalendar(year, month):
        row = "<tr>"
        for day in week:
            if day == 0:
                row += '<td class="empty"></td>'
                continue
            dtype = get_day_type(day, year, month, holidays)
            td_cls = {"fri":"fri-td","sat":"sat-td","hol":"hol-td"}.get(dtype, "")
            day_lbl = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
            hol_ico = " ✡" if dtype == "hol" else ("🕯" if dtype == "fri" else "")

            cells = ""
            for shift, badge_cls in [(1,"badge-heavy"),(2,"badge-heavy"),(3,"badge-light")]:
                doc = assignment.get((day, shift), "—")
                col = color_map.get(doc, "#aaa")
                label = SHIFT_LABELS[shift].split()[0]  # "טור 1" בלבד
                cells += (
                    f'<span class="badge {badge_cls}" style="background:{col}">'
                    f'{label}: {doc}</span>'
                )
            row += (
                f'<td class="{td_cls}">'
                f'<span class="day-num">{day} {day_lbl}{hol_ico}</span>'
                f'{cells}</td>'
            )
        body += row + "</tr>"

    return (
        '<div class="cal-wrap">'
        f'<table class="cal-table"><thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody></table></div>'
    )


# ══════════════════════════════════════════════════════
# ⑤ FAIRNESS TABLE
# ══════════════════════════════════════════════════════
def render_fairness(doctors, heavy, light, color_map) -> str:
    max_h = max((heavy.get(d, 0) for d in doctors), default=1)
    max_l = max((light.get(d, 0) for d in doctors), default=1)
    rows  = ""
    for doc in sorted(doctors, key=lambda d: -(heavy.get(d,0) + light.get(d,0))):
        h = heavy.get(doc, 0)
        l = light.get(doc, 0)
        col = color_map.get(doc, "#999")
        ph  = int(h / max_h * 100) if max_h else 0
        pl  = int(l / max_l * 100) if max_l else 0
        name_badge = f'<span style="background:{col};color:#fff;padding:2px 9px;border-radius:10px;font-weight:600">{doc}</span>'
        bar_h = f'<div class="bar-wrap"><div class="bar-fill" style="width:{ph}%;background:#2980b9"></div></div>'
        bar_l = f'<div class="bar-wrap"><div class="bar-fill" style="width:{pl}%;background:#27ae60"></div></div>'
        rows += f"<tr><td>{name_badge}</td><td>{h}</td><td>{bar_h}</td><td>{l}</td><td>{bar_l}</td></tr>"

    return (
        '<table class="fair-table">'
        "<thead><tr>"
        "<th>רופא</th>"
        "<th>סל כבד (טור 1+2)</th><th>פילוג כבד</th>"
        "<th>סל פסיבי (טור 3)</th><th>פילוג פסיבי</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


# ══════════════════════════════════════════════════════
# ⑥ EXCEL EXPORT
# ══════════════════════════════════════════════════════
def build_excel(year, month, assignment, heavy, light, holidays) -> bytes:
    num_days = calendar.monthrange(year, month)[1]
    sched_rows = []
    for day in range(1, num_days + 1):
        dtype    = get_day_type(day, year, month, holidays)
        day_name = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
        sched_rows.append({
            "תאריך":       f"{day:02d}/{month:02d}/{year}",
            "יום":         day_name,
            "סוג":         {"fri":"שישי","sat":"שבת","hol":"חג","normal":"רגיל"}.get(dtype,"רגיל"),
            "טור 1 (כבד)": assignment.get((day, 1), "—"),
            "טור 2 (כבד)": assignment.get((day, 2), "—"),
            "טור 3 (פסיבי)": assignment.get((day, 3), "—"),
        })

    all_docs = sorted(set(list(heavy.keys()) + list(light.keys())))
    fair_rows = [
        {"רופא": d, "סל כבד": heavy.get(d, 0), "סל פסיבי": light.get(d, 0),
         "סה\"כ": heavy.get(d, 0) + light.get(d, 0)}
        for d in all_docs
    ]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(sched_rows).to_excel(w, sheet_name="סידור",   index=False)
        pd.DataFrame(fair_rows ).to_excel(w, sheet_name="טבלת צדק", index=False)
    return buf.getvalue()


# ══════════════════════════════════════════════════════
# UI  — INPUT PANELS
# ══════════════════════════════════════════════════════
with st.expander("⚙️ הגדרות בסיסיות", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        doctors_input = st.text_area(
            "👨‍⚕️ רשימת רופאים (שם אחד בכל שורה)",
            value="הרשקוביץ מ'\nטלמן ג'\nשלי ש'\nסאימן א'\nדנין י'\nד\"ר כהן\nד\"ר לוי\nד\"ר פרץ",
            height=180,
        )
    with c2:
        today = date.today()
        sel_month = st.selectbox("📅 חודש", list(range(1,13)),
                                 index=today.month-1,
                                 format_func=lambda m: HEBREW_MONTHS[m-1])
    with c3:
        sel_year = st.selectbox("📆 שנה",
                                list(range(today.year-1, today.year+4)), index=1)

    st.markdown('<div class="sec-header">✡️ ימי חג / ערב-חג</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">תמיכה בטווחים: <code>2-4/10</code> , ימים בודדים: <code>14/04</code> , מעורב: <code>2-4/10,14/04,21/04</code></div>',
        unsafe_allow_html=True,
    )
    holidays_raw = st.text_input("הזן תאריכי חג:", value="", placeholder="2-4/10, 14/04, 21-23/04")

# ── הגבלות אישיות ──
doctors_preview = [d.strip() for d in doctors_input.strip().splitlines() if d.strip()]
personal_blocks: dict = {}

with st.expander("🚫 הגבלות אישיות – ימים לא זמינים"):
    st.markdown(
        '<div class="info-box">תמיכה בטווחים: <code>1-5</code> , בודדים: <code>7,12</code> , מעורב: <code>1-3,8,20-22</code></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols[i % 2]:
            raw = st.text_input(f"🚫 {doc}", key=f"blk_{doc}", placeholder="1-5, 14, 20-22")
            personal_blocks[doc] = parse_day_ranges(raw, sel_year, sel_month)

# ── הגדרת טורים לכל רופא ──
shift_rules: dict = {}

with st.expander("🔧 טורים מותרים לכל רופא"):
    st.markdown(
        '<div class="info-box"><b>סל כבד</b> = טורים 1 ו-2 (מחושב יחד). <b>סל פסיבי</b> = טור 3 (חישוב עצמאי).</div>',
        unsafe_allow_html=True,
    )
    cols2 = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        dflt = DEFAULT_ALLOWED.get(doc, [1, 2, 3])
        with cols2[i % 2]:
            allowed = st.multiselect(
                f"{doc}", options=[1, 2, 3], default=dflt,
                format_func=lambda x: SHIFT_LABELS[x], key=f"sr_{doc}",
            )
            shift_rules[doc] = allowed or [1, 2, 3]

# ══════════════════════════════════════════════════════
# RUN BUTTON
# ══════════════════════════════════════════════════════
st.markdown("---")
bc, sc = st.columns([2, 1])
with bc:
    run_btn = st.button("✨ צור סידור כוננויות")
with sc:
    seed = st.number_input("🎲 זרע אקראיות (0 = אקראי)", min_value=0, value=0, step=1)

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

    holidays = parse_holidays(holidays_raw, sel_year, sel_month)
    color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}

    # אזהרות
    warns = [f"⚠️ {d} – אין טורים מותרים!" for d in doctors if not shift_rules.get(d)]
    if warns:
        st.markdown('<div class="warn-box">' + "<br>".join(warns) + "</div>", unsafe_allow_html=True)

    assignment, heavy, light = build_schedule(
        doctors, sel_year, sel_month, holidays, personal_blocks, shift_rules
    )

    # ── לוח שנה ──
    st.markdown(f"### 📋 לוח כוננויות – {HEBREW_MONTHS[sel_month-1]} {sel_year}")
    if holidays:
        st.markdown(
            f'<div class="info-box">ימי חג שהוגדרו: {", ".join(str(d) for d in sorted(holidays))}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(render_calendar(sel_year, sel_month, assignment, color_map, holidays),
                unsafe_allow_html=True)

    # ── טבלת צדק ──
    st.markdown("---")
    st.markdown('<div class="sec-header">📊 טבלת צדק – שני סלים</div>', unsafe_allow_html=True)

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        st.markdown(render_fairness(doctors, heavy, light, color_map), unsafe_allow_html=True)
    with fc2:
        h_vals = [heavy.get(d, 0) for d in doctors]
        l_vals = [light.get(d, 0) for d in doctors]
        h_std  = pd.Series(h_vals).std()
        l_std  = pd.Series(l_vals).std()
        st.metric("סטיית תקן – סל כבד",  f"{h_std:.2f}")
        st.metric("סטיית תקן – סל פסיבי", f"{l_std:.2f}")
        overall = (h_std + l_std) / 2
        if overall < 1.5:
            st.success("✅ חלוקה הוגנת מאוד")
        elif overall < 3.0:
            st.warning("⚠️ חלוקה סבירה")
        else:
            st.error("❌ חלוקה לא מאוזנת – נסה זרע אחר")

    # ── ייצוא ──
    st.markdown("---")
    st.markdown('<div class="sec-header">📥 ייצוא</div>', unsafe_allow_html=True)
    num_days = calendar.monthrange(sel_year, sel_month)[1]
    csv_rows = []
    for day in range(1, num_days + 1):
        dtype    = get_day_type(day, sel_year, sel_month, holidays)
        day_name = HEBREW_DAYS[(date(sel_year, sel_month, day).weekday() + 1) % 7]
        csv_rows.append({
            "תאריך":         f"{day:02d}/{sel_month:02d}/{sel_year}",
            "יום":           day_name,
            "סוג":           {"fri":"שישי","sat":"שבת","hol":"חג","normal":"רגיל"}.get(dtype,"רגיל"),
            "טור 1 (כבד)":  assignment.get((day,1),"—"),
            "טור 2 (כבד)":  assignment.get((day,2),"—"),
            "טור 3 (פסיבי)": assignment.get((day,3),"—"),
        })
    df_exp = pd.DataFrame(csv_rows)

    ex1, ex2 = st.columns(2)
    with ex1:
        st.download_button(
            "⬇️ הורד כ-CSV",
            data=df_exp.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"כוננויות_{HEBREW_MONTHS[sel_month-1]}_{sel_year}.csv",
            mime="text/csv",
        )
    with ex2:
        try:
            st.download_button(
                "📊 הורד כ-Excel",
                data=build_excel(sel_year, sel_month, assignment, heavy, light, holidays),
                file_name=f"כוננויות_{HEBREW_MONTHS[sel_month-1]}_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.info("להורדת Excel: `pip install openpyxl`")
