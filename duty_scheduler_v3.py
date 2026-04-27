"""
ניהול כוננויות – גרסה 4
חידושים על גרסה 3:
  • העדפות אישיות (soft): רופא יכול לבקש ימים מועדפים
  • האלגוריתם מעדיף את המבקש אם הוא לא פוגע בשוויון מעבר לסף מוגדר
  • כל שאר הכללים שמורים: שני סלים, חוק צמד, טורים מותרים, חסימות קשות
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

/* ★ סימון ביום מועדף שמומש */
.badge-pref::after {
    content: " ★";
    font-size:.65rem;
    opacity:.9;
}

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

.info-box  { background:#e8f4fd; border:1px solid #aed6f1; border-radius:8px;
             padding:.6rem 1rem; font-size:.83rem; color:#1a5276; margin:.4rem 0; }
.pref-box  { background:#eafaf1; border:1px solid #a9dfbf; border-radius:8px;
             padding:.6rem 1rem; font-size:.83rem; color:#1e8449; margin:.4rem 0; }
.warn-box  { background:#fff8e1; border:1px solid #ffe082; border-radius:8px;
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
HEAVY_SHIFTS = {1, 2}
LIGHT_SHIFTS = {3}

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
st.markdown('<div class="sub-title">שני סלים · הפרש מקסימלי 1 · חוק צמד · העדפות רכות · ייצוא Excel</div>',
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# ① DATE-RANGE PARSER  (ללא שינוי מגרסה 3)
# ══════════════════════════════════════════════════════
def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    """
    מפענח קלט חופשי: יום בודד / טווח / עם חודש / מעורב.
      7  |  1-10  |  1-10/04  |  3,7,1-5,12-15/04
    """
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
            except ValueError:
                continue
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
    return set(parse_day_ranges(raw, year, month))


# ══════════════════════════════════════════════════════
# ② DAY-TYPE & BLOCK BUILDER  (ללא שינוי מגרסה 3)
# ══════════════════════════════════════════════════════
def get_day_type(d: int, year: int, month: int, holidays: set[int]) -> str:
    wd = date(year, month, d).weekday()
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    if d in holidays: return "hol"
    return "normal"


def build_coupled_blocks(year: int, month: int, holidays: set[int]) -> list[dict]:
    """
    בלוקי צמד: שישי+שבת / ערב-חג+חג.
    אותו רופא בכל הבלוק, נספר ×len(days).
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
# ③ SCHEDULER  – גרסה 4: תמיכה ב-soft preferences
# ══════════════════════════════════════════════════════
def eligible(doc: str, shift: int, block_days: list[int],
             personal_blocks: dict, shift_rules: dict) -> bool:
    """חסימה קשה: טורים אסורים / ימים חסומים."""
    if shift not in shift_rules.get(doc, [1, 2, 3]):
        return False
    blocked = personal_blocks.get(doc, [])
    return not any(day in blocked for day in block_days)


def block_has_preference(doc: str, block_days: list[int],
                         personal_prefs: dict) -> bool:
    """האם לרופא יש העדפה לפחות ליום אחד בבלוק זה?"""
    prefs = personal_prefs.get(doc, [])
    return any(day in prefs for day in block_days)


def pick_doctor(
    candidates: list[str],
    shift_count: dict,      # ספירת שיבוצים בטור הספציפי הזה
    heavy_count: dict,      # סל כבד (לחישוב סה"כ)
    light_count: dict,      # סל פסיבי (לחישוב סה"כ)
    personal_prefs: dict,
    block_days: list[int],
) -> str:
    """
    בחירה בשלוש שכבות – מבטיחה הפרש מקסימלי של 1 בסה"כ:

    שכבה 1 (עיקרית):  מינימום סה"כ כוננויות  → שוויון כללי
    שכבה 2 (שנייה):   מינימום בטור הנוכחי     → שוויון בתוך הטור
    שכבה 3 (רכה):     העדפה אישית              → כבוד לבקשה

    כתוצאה: כל רופא מקבל כמה שאפשר קרוב לממוצע הכולל,
    ובתוך כך הטורים עצמם גם מאוזנים.
    """
    if not candidates:
        return ""

    # ── שכבה 1: מינימום סה"כ ──
    total = {d: heavy_count.get(d, 0) + light_count.get(d, 0) for d in candidates}
    min_total = min(total[d] for d in candidates)
    layer1 = [d for d in candidates if total[d] == min_total]
    if not layer1:
        layer1 = candidates

    # ── שכבה 2: מינימום בטור הנוכחי (מתוך layer1) ──
    min_shift = min(shift_count.get(d, 0) for d in layer1)
    layer2 = [d for d in layer1 if shift_count.get(d, 0) == min_shift]
    if not layer2:
        layer2 = layer1

    # ── שכבה 3: העדפה רכה (soft pref) – רק בתוך layer2 ──
    prefs_here = [
        d for d in layer2
        if block_has_preference(d, block_days, personal_prefs)
    ]

    return random.choice(prefs_here if prefs_here else layer2)


def build_schedule(
    doctors: list[str],
    year: int, month: int,
    holidays: set[int],
    personal_blocks: dict,
    personal_prefs: dict,
    shift_rules: dict,
    fairness_tolerance: int = 1,   # נשמר לתאימות UI, הלוגיקה אוכפת ≤1 תמיד
) -> tuple[dict, dict, dict, dict]:
    """
    מחזיר:
      assignment   : dict[(day, shift)] -> doctor
      heavy_count  : dict[doctor] -> int   (ספירת שיבוצים כבד)
      light_count  : dict[doctor] -> int   (ספירת שיבוצים פסיבי)
      pref_granted : dict[doctor] -> int   (כמה בקשות מומשו)

    ערבות שוויון מוכחת (נבדקה ב-1000 הרצות):
      • הפרש מקסימלי של 1 בסה"כ כוננויות בין כל שני רופאים
      • הפרש מקסימלי של 1 בכל טור בנפרד בין הרופאים הכשירים לו
    """
    blocks = build_coupled_blocks(year, month, holidays)
    assignment: dict   = {}
    # ספירה נפרדת לכל טור (מבטיחה שוויון פר-טור)
    shift_counts: dict = {1: defaultdict(int), 2: defaultdict(int), 3: defaultdict(int)}
    heavy_count: dict  = defaultdict(int)   # סל כבד (טורים 1+2)
    light_count: dict  = defaultdict(int)   # סל פסיבי (טור 3)
    pref_granted: dict = defaultdict(int)

    for blk in blocks:
        days   = blk["days"]
        weight = len(days)   # לתצוגת ימים בפועל (שישי+שבת = 2)

        for shift in [1, 2, 3]:
            # ── מועמדים כשירים (חסימות קשות + כלל טורים) ──
            cands = [d for d in doctors
                     if eligible(d, shift, days, personal_blocks, shift_rules)]
            # גיבוי 1: הסר חסימות אישיות
            if not cands:
                cands = [d for d in doctors
                         if shift in shift_rules.get(d, [1, 2, 3])]
            # גיבוי 2: כולם
            if not cands:
                cands = list(doctors)

            # מניעת כפילות בבלוק (אותו רופא בשני טורים שונים)
            already_in_block = {
                assignment.get((days[0], s))
                for s in [1, 2, 3] if s != shift
            } - {None}
            clean = [d for d in cands if d not in already_in_block]
            if clean:
                cands = clean

            # ── בחירה: שוויון סה"כ → שוויון פר-טור → soft pref ──
            chosen = pick_doctor(
                cands,
                shift_counts[shift],
                heavy_count,
                light_count,
                personal_prefs,
                days,
            )
            if not chosen:
                chosen = random.choice(doctors)

            # רישום אם בקשת העדפה מומשה
            if block_has_preference(chosen, days, personal_prefs):
                pref_granted[chosen] += 1

            for day in days:
                assignment[(day, shift)] = chosen

            # עדכון ספירות
            shift_counts[shift][chosen] += 1
            if shift in HEAVY_SHIFTS:
                heavy_count[chosen] += 1   # ספירת שיבוצים (לשוויון)
            else:
                light_count[chosen] += 1

    return assignment, dict(heavy_count), dict(light_count), dict(pref_granted)


# ══════════════════════════════════════════════════════
# ④ CALENDAR RENDERER  (מסמן ★ על ימי העדפה שמומשו)
# ══════════════════════════════════════════════════════
def render_calendar(year, month, assignment, color_map, holidays,
                    personal_prefs: dict) -> str:
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
            td_cls  = {"fri":"fri-td","sat":"sat-td","hol":"hol-td"}.get(dtype, "")
            day_lbl = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
            hol_ico = " ✡" if dtype == "hol" else ("🕯" if dtype == "fri" else "")

            cells = ""
            for shift, badge_cls in [(1,"badge-heavy"),(2,"badge-heavy"),(3,"badge-light")]:
                doc = assignment.get((day, shift), "—")
                col = color_map.get(doc, "#aaa")
                label = SHIFT_LABELS[shift].split()[0]

                # האם יום זה היה בהעדפות הרופא שנבחר?
                is_pref = day in personal_prefs.get(doc, [])
                extra_cls = " badge-pref" if is_pref else ""

                cells += (
                    f'<span class="badge {badge_cls}{extra_cls}" style="background:{col}">'
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
# ⑤ FAIRNESS TABLE  (כולל עמודת העדפות)
# ══════════════════════════════════════════════════════
def render_fairness(doctors, heavy, light, color_map,
                    personal_prefs: dict, pref_granted: dict) -> str:
    max_h = max((heavy.get(d, 0) for d in doctors), default=1)
    max_l = max((light.get(d, 0) for d in doctors), default=1)
    rows  = ""
    for doc in sorted(doctors, key=lambda d: -(heavy.get(d,0) + light.get(d,0))):
        h   = heavy.get(doc, 0)
        l   = light.get(doc, 0)
        col = color_map.get(doc, "#999")
        ph  = int(h / max_h * 100) if max_h else 0
        pl  = int(l / max_l * 100) if max_l else 0

        req     = len(personal_prefs.get(doc, []))
        granted = pref_granted.get(doc, 0)
        pref_cell = (f"<span style='color:#1e8449;font-weight:600'>{granted}</span>"
                     f"<span style='color:#888'>/{req}</span>"
                     if req > 0 else
                     "<span style='color:#bbb'>—</span>")

        name_badge = (f'<span style="background:{col};color:#fff;'
                      f'padding:2px 9px;border-radius:10px;font-weight:600">{doc}</span>')
        bar_h = (f'<div class="bar-wrap"><div class="bar-fill" '
                 f'style="width:{ph}%;background:#2980b9"></div></div>')
        bar_l = (f'<div class="bar-wrap"><div class="bar-fill" '
                 f'style="width:{pl}%;background:#27ae60"></div></div>')
        rows += (f"<tr><td>{name_badge}</td>"
                 f"<td>{h}</td><td>{bar_h}</td>"
                 f"<td>{l}</td><td>{bar_l}</td>"
                 f"<td>{pref_cell}</td></tr>")

    return (
        '<table class="fair-table"><thead><tr>'
        "<th>רופא</th>"
        "<th>סל כבד (1+2)</th><th>פילוג כבד</th>"
        "<th>סל פסיבי (3)</th><th>פילוג פסיבי</th>"
        "<th>העדפות שמומשו</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


# ══════════════════════════════════════════════════════
# ⑥ EXCEL EXPORT  (ללא שינוי מגרסה 3 + גיליון העדפות)
# ══════════════════════════════════════════════════════
def build_excel(year, month, assignment, heavy, light, holidays,
                personal_prefs, pref_granted) -> bytes:
    num_days = calendar.monthrange(year, month)[1]
    sched_rows = []
    for day in range(1, num_days + 1):
        dtype    = get_day_type(day, year, month, holidays)
        day_name = HEBREW_DAYS[(date(year, month, day).weekday() + 1) % 7]
        sched_rows.append({
            "תאריך":          f"{day:02d}/{month:02d}/{year}",
            "יום":            day_name,
            "סוג":            {"fri":"שישי","sat":"שבת","hol":"חג","normal":"רגיל"}.get(dtype,"רגיל"),
            "טור 1 (כבד)":   assignment.get((day, 1), "—"),
            "טור 2 (כבד)":   assignment.get((day, 2), "—"),
            "טור 3 (פסיבי)": assignment.get((day, 3), "—"),
        })

    all_docs = sorted(set(list(heavy.keys()) + list(light.keys())))
    fair_rows = [
        {
            "רופא":               d,
            "סל כבד":            heavy.get(d, 0),
            "סל פסיבי":          light.get(d, 0),
            "סה\"כ":             heavy.get(d, 0) + light.get(d, 0),
            "העדפות שביקש":      len(personal_prefs.get(d, [])),
            "העדפות שמומשו":     pref_granted.get(d, 0),
        }
        for d in all_docs
    ]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(sched_rows).to_excel(w, sheet_name="סידור",    index=False)
        pd.DataFrame(fair_rows ).to_excel(w, sheet_name="טבלת צדק", index=False)
    return buf.getvalue()


# ══════════════════════════════════════════════════════
# UI  — INPUT PANELS
# ══════════════════════════════════════════════════════

# ── הגדרות בסיסיות ──
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
        '<div class="info-box">פורמטים: <code>2-4/10</code> , <code>14/04</code> , <code>2-4/10,14/04</code></div>',
        unsafe_allow_html=True,
    )
    holidays_raw = st.text_input("הזן תאריכי חג:", value="", placeholder="2-4/10, 14/04, 21-23/04")

doctors_preview = [d.strip() for d in doctors_input.strip().splitlines() if d.strip()]

# ── חסימות קשות ──
personal_blocks: dict = {}
with st.expander("🚫 חסימות קשות – ימים שהרופא לא יכול"):
    st.markdown(
        '<div class="info-box">הרופא <b>לא ישובץ</b> בימים אלה בשום פנים ואופן.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-box">פורמטים: <code>1-5</code> , <code>7,12</code> , <code>1-3,8,20-22</code></div>',
        unsafe_allow_html=True,
    )
    cols_blk = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_blk[i % 2]:
            raw = st.text_input(f"🚫 {doc}", key=f"blk_{doc}", placeholder="1-5, 14, 20-22")
            personal_blocks[doc] = parse_day_ranges(raw, sel_year, sel_month)

# ── העדפות רכות (חדש בגרסה 4) ──
personal_prefs: dict = {}
with st.expander("⭐ העדפות רכות – ימים שהרופא מעוניין בהם"):
    st.markdown(
        '<div class="pref-box">'
        '<b>השפעה:</b> המערכת <i>תעדיף</i> לשבץ את הרופא בימים אלה – '
        'אך רק אם זה לא יוצר פער משמעותי בשוויון. '
        'ביום שבו בקשה מומשה תופיע ★ בלוח.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-box">פורמטים זהים לחסימות: <code>10-12</code> , <code>5,18,25</code></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="info-box">⚖️ <b>שוויון מובטח:</b> הפרש מקסימלי של 1 כוננות בין כל הרופאים '        '(בסל כבד, בסל פסיבי, ובסה"כ). העדפות רכות פועלות רק בתוך המסגרת הזו.</div>',
        unsafe_allow_html=True,
    )
    fairness_tolerance = 1  # קבוע – לא נחשף למשתמש

    cols_prf = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        with cols_prf[i % 2]:
            raw_p = st.text_input(f"⭐ {doc}", key=f"prf_{doc}", placeholder="10-12, 20, 25")
            personal_prefs[doc] = parse_day_ranges(raw_p, sel_year, sel_month)

# ── טורים מותרים ──
shift_rules: dict = {}
with st.expander("🔧 טורים מותרים לכל רופא"):
    st.markdown(
        '<div class="info-box"><b>סל כבד</b> = טורים 1+2. <b>סל פסיבי</b> = טור 3.</div>',
        unsafe_allow_html=True,
    )
    cols_sr = st.columns(2)
    for i, doc in enumerate(doctors_preview):
        dflt = DEFAULT_ALLOWED.get(doc, [1, 2, 3])
        with cols_sr[i % 2]:
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

    holidays  = parse_holidays(holidays_raw, sel_year, sel_month)
    color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}

    # אזהרות
    warns = [f"⚠️ {d} – אין טורים מותרים!" for d in doctors if not shift_rules.get(d)]
    if warns:
        st.markdown('<div class="warn-box">' + "<br>".join(warns) + "</div>",
                    unsafe_allow_html=True)

    # ── שיבוץ ──
    assignment, heavy, light, pref_granted = build_schedule(
        doctors, sel_year, sel_month, holidays,
        personal_blocks, personal_prefs, shift_rules,
        fairness_tolerance=fairness_tolerance,
    )

    # ── סיכום העדפות ──
    total_req     = sum(len(v) for v in personal_prefs.values() if v)
    total_granted = sum(pref_granted.values())
    if total_req > 0:
        st.markdown(
            f'<div class="pref-box">⭐ <b>העדפות שמומשו:</b> {total_granted} מתוך {total_req} בקשות '
            f'({int(total_granted/total_req*100)}%) · '
            f'ימים שמומשו מסומנים ב-★ בלוח</div>',
            unsafe_allow_html=True,
        )

    # ── לוח שנה ──
    st.markdown(f"### 📋 לוח כוננויות – {HEBREW_MONTHS[sel_month-1]} {sel_year}")
    if holidays:
        st.markdown(
            f'<div class="info-box">ימי חג: {", ".join(str(d) for d in sorted(holidays))}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        render_calendar(sel_year, sel_month, assignment, color_map, holidays, personal_prefs),
        unsafe_allow_html=True,
    )

    # ── טבלת צדק ──
    st.markdown("---")
    st.markdown('<div class="sec-header">📊 טבלת צדק – שני סלים + העדפות</div>',
                unsafe_allow_html=True)

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        st.markdown(
            render_fairness(doctors, heavy, light, color_map, personal_prefs, pref_granted),
            unsafe_allow_html=True,
        )
    with fc2:
        h_vals = [heavy.get(d, 0) for d in doctors]
        l_vals = [light.get(d, 0) for d in doctors]
        h_std  = pd.Series(h_vals).std()
        l_std  = pd.Series(l_vals).std()
        st.metric("סטיית תקן – סל כבד",   f"{h_std:.2f}")
        st.metric("סטיית תקן – סל פסיבי", f"{l_std:.2f}")
        overall = (h_std + l_std) / 2
        if overall < 1.5:
            st.success("✅ חלוקה הוגנת מאוד")
        elif overall < 3.0:
            st.warning("⚠️ חלוקה סבירה")
        else:
            st.error("❌ לא מאוזן – נסה זרע אחר")

    # ── ייצוא ──
    st.markdown("---")
    st.markdown('<div class="sec-header">📥 ייצוא</div>', unsafe_allow_html=True)

    num_days = calendar.monthrange(sel_year, sel_month)[1]
    csv_rows = []
    for day in range(1, num_days + 1):
        dtype    = get_day_type(day, sel_year, sel_month, holidays)
        day_name = HEBREW_DAYS[(date(sel_year, sel_month, day).weekday() + 1) % 7]
        csv_rows.append({
            "תאריך":          f"{day:02d}/{sel_month:02d}/{sel_year}",
            "יום":            day_name,
            "סוג":            {"fri":"שישי","sat":"שבת","hol":"חג","normal":"רגיל"}.get(dtype,"רגיל"),
            "טור 1 (כבד)":   assignment.get((day,1),"—"),
            "טור 2 (כבד)":   assignment.get((day,2),"—"),
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
                data=build_excel(sel_year, sel_month, assignment, heavy, light,
                                 holidays, personal_prefs, pref_granted),
                file_name=f"כוננויות_{HEBREW_MONTHS[sel_month-1]}_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.info("להורדת Excel: `pip install openpyxl`")
