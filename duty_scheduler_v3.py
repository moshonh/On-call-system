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
st.set_page_config(page_title="ניהול כוננויות - גרסה סופית ומדויקת", page_icon="🏥", layout="wide")

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

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
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
        # Start of a potential block: Friday, Holiday, or Holiday Eve
        if dtype in ("fri", "hol", "hol_eve"):
            block_days = [d]
            used.add(d)
            nxt = d + 1
            while nxt <= num_days:
                nt = get_day_type(nxt, year, month, holidays)
                # Continue block if next day is Saturday, Holiday, or Holiday Eve
                if nt in ("sat", "hol", "hol_eve"):
                    block_days.append(nxt)
                    used.add(nxt)
                    nxt += 1
                else: break
            blocks.append({"days": block_days, "coupled": len(block_days) > 1})
        else:
            blocks.append({"days": [d], "coupled": False})
            used.add(d)
        d += 1
    return blocks

# ══════════════════════════════════════════════════════
# CORE SCHEDULER (STOCHASTIC HILL CLIMBING)
# ══════════════════════════════════════════════════════

def build_schedule(
    doctors: list[str],
    year: int,
    month: int,
    holidays: set,
    personal_blocks: dict,
    personal_prefs: dict,
    shift_rules: dict,
    max_iterations: int = 20000
):
    num_days = calendar.monthrange(year, month)[1]
    blocks   = build_coupled_blocks(year, month, holidays)

    # מיפוי: יום → האם הוא חלק מבלוק צמד (שישי+שבת / ערב-חג+חג)
    day_to_coupled_block: dict[int, int] = {}   # day → block_index
    for idx, blk in enumerate(blocks):
        if blk["coupled"]:
            for day in blk["days"]:
                day_to_coupled_block[day] = idx

    def is_coupled_day(day: int) -> bool:
        return day in day_to_coupled_block

    # ── בנה שיבוץ ראשוני ──────────────────────────────────────
    def get_initial():
        assignment = {}
        # T1, T2 – לפי בלוקים (שומר צמד)
        for blk in blocks:
            days = blk["days"]
            c1 = [d for d in doctors
                  if 1 in shift_rules.get(d, [1,2,3])
                  and not any(day in personal_blocks.get(d, []) for day in days)]
            if not c1: return None
            chosen1 = random.choice(c1)
            for day in days: assignment[(day, 1)] = chosen1

            c2 = [d for d in doctors
                  if 2 in shift_rules.get(d, [1,2,3])
                  and d != chosen1
                  and not any(day in personal_blocks.get(d, []) for day in days)]
            if not c2: return None
            chosen2 = random.choice(c2)
            for day in days: assignment[(day, 2)] = chosen2

        # T3 – כל יום בנפרד (ללא צמד)
        for day in range(1, num_days + 1):
            already = {assignment.get((day, 1)), assignment.get((day, 2))}
            c3 = [d for d in doctors
                  if 3 in shift_rules.get(d, [1,2,3])
                  and d not in already
                  and day not in personal_blocks.get(d, [])]
            if not c3: return None
            assignment[(day, 3)] = random.choice(c3)
        return assignment

    # ── פונקציית ציון ──────────────────────────────────────────
    def get_score(asgn):
        active_days    = {d: 0 for d in doctors}  # ימי T1+T2 בפועל
        passive_days   = {d: 0 for d in doctors}  # ימי T3
        # ספירת בלוקי-צמד בT1/T2 לכל רופא
        coupled_active = {d: set() for d in doctors}

        for (day, shift), doc in asgn.items():
            if shift in (1, 2):
                active_days[doc] += 1
                if is_coupled_day(day):
                    coupled_active[doc].add(day_to_coupled_block[day])
            else:
                passive_days[doc] += 1

        # ── שוויון (T1/T2 לפי בלוקים) ──
        blk1_cnt = {d: 0 for d in doctors}
        blk2_cnt = {d: 0 for d in doctors}
        for blk in blocks:
            d0 = blk["days"][0]
            doc1 = asgn.get((d0, 1))
            doc2 = asgn.get((d0, 2))
            if doc1: blk1_cnt[doc1] += 1
            if doc2: blk2_cnt[doc2] += 1

        t1_pool = [d for d in doctors if 1 in shift_rules.get(d, [1,2,3])]
        t2_pool = [d for d in doctors if 2 in shift_rules.get(d, [1,2,3])]
        t3_vals = list(passive_days.values())

        g1 = (max(blk1_cnt[d] for d in t1_pool) - min(blk1_cnt[d] for d in t1_pool)) if t1_pool else 0
        g2 = (max(blk2_cnt[d] for d in t2_pool) - min(blk2_cnt[d] for d in t2_pool)) if t2_pool else 0
        g3 = max(t3_vals) - min(t3_vals) if t3_vals else 0

        fairness_score = (g1 + g2) * 500 + g3 * 500

        # ── עונש קשיח: אותו רופא בשני טורים באותו יום ──────────
        dup_penalty = 0
        for day in range(1, num_days + 1):
            docs_today = [asgn.get((day, s)) for s in [1, 2, 3] if asgn.get((day, s))]
            seen = set()
            for doc in docs_today:
                if doc in seen:
                    dup_penalty += 50000
                seen.add(doc)

        # ── עונש קשיח: יותר מבלוק-צמד אחד בT1/T2 ──────────────
        # כל בלוק-צמד נוסף מעל 1 = עונש ענק
        # (מאפשר בלוק-צמד אחד, מונע שניים)
        coupled_penalty = sum(
            max(0, len(s) - 1) * 10000
            for s in coupled_active.values()
        )

        # ── בונוס: העדפות רק בT1/T2 ────────────────────────────
        # בנוסף: אם יום הוא ימי-צמד, מעדיפים שהרופא המבקש יקבל T1/T2 (לא T3)
        pref_score = 0
        for (day, shift), doc in asgn.items():
            if day in personal_prefs.get(doc, []):
                if shift in (1, 2):
                    # בונוס גדול לT1/T2 ביום מועדף
                    pref_score -= 20.0
                # T3 ביום מועדף – בונוס קטן בלבד (לא עיקרי)
                # else: pref_score -= 2.0  # ← מוסר, כי רצינו רק T1/T2

        return fairness_score + coupled_penalty + dup_penalty + pref_score

    # ── אתחול ──────────────────────────────────────────────────
    current_assignment = None
    for _ in range(500):
        current_assignment = get_initial()
        if current_assignment:
            break

    if not current_assignment:
        return None, {}, {}, {}

    current_score = get_score(current_assignment)

    # ── Hill Climbing ──────────────────────────────────────────
    for i in range(max_iterations):
        new_assignment = current_assignment.copy()

        move = random.random()

        if move < 0.55:
            # שינוי T1 או T2 בבלוק
            blk    = random.choice(blocks)
            days   = blk["days"]
            s      = random.choice([1, 2])
            other_s = 2 if s == 1 else 1
            already_other = new_assignment.get((days[0], other_s))
            cands = [d for d in doctors
                     if s in shift_rules.get(d, [1,2,3])
                     and d != already_other
                     and not any(day in personal_blocks.get(d, []) for day in days)]
            if cands:
                chosen = random.choice(cands)
                for day in days:
                    new_assignment[(day, s)] = chosen

        elif move < 0.80:
            # שינוי T3 ביום בודד
            day    = random.randint(1, num_days)
            already = {new_assignment.get((day, 1)), new_assignment.get((day, 2))}
            cands = [d for d in doctors
                     if 3 in shift_rules.get(d, [1,2,3])
                     and d not in already
                     and day not in personal_blocks.get(d, [])]
            if cands:
                new_assignment[(day, 3)] = random.choice(cands)

        else:
            # מהלך ממוקד: נסה לשים רופא עם העדפה ב-T1/T2 ביום המועדף שלו
            # בחר רופא אקראי עם העדפות
            docs_with_prefs = [d for d in doctors if personal_prefs.get(d)]
            if docs_with_prefs:
                doc  = random.choice(docs_with_prefs)
                prefs = personal_prefs.get(doc, [])
                if prefs:
                    pref_day = random.choice(prefs)
                    if pref_day in personal_blocks.get(doc, []):
                        pass  # יום חסום, דלג
                    else:
                        # מצא את הבלוק שמכיל את pref_day
                        target_blk = next(
                            (blk for blk in blocks if pref_day in blk["days"]),
                            None
                        )
                        if target_blk:
                            # נסה לשים doc ב-T1 או T2 בבלוק זה
                            days = target_blk["days"]
                            for s in [1, 2]:
                                if s not in shift_rules.get(doc, [1,2,3]):
                                    continue
                                other_s = 2 if s == 1 else 1
                                already_other = new_assignment.get((days[0], other_s))
                                if already_other != doc:
                                    cands_ok = not any(
                                        day in personal_blocks.get(doc, [])
                                        for day in days
                                    )
                                    if cands_ok:
                                        for day in days:
                                            new_assignment[(day, s)] = doc
                                        break

        new_score = get_score(new_assignment)
        if new_score <= current_score:
            current_assignment = new_assignment
            current_score      = new_score

    # ── סיכום ──────────────────────────────────────────────────
    active_days  = defaultdict(int)
    passive_days = defaultdict(int)
    pref_granted = defaultdict(int)

    for (day, shift), doc in current_assignment.items():
        if shift in (1, 2):
            active_days[doc] += 1
            # ספירת העדפות: רק T1/T2
            if day in personal_prefs.get(doc, []):
                pref_granted[doc] += 1
        else:
            passive_days[doc] += 1

    return current_assignment, dict(active_days), dict(passive_days), dict(pref_granted)

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
                # Only show star for preferences in active duties
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

st.markdown('<div class="main-title">🏥 ניהול כוננויות - גרסה סופית ומדויקת</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">העדפות לכוננות אקטיבית בלבד · רציפות חג-סופ"ש מלאה · הגבלה קשיחה לסופ"ש אקטיבי אחד</div>', unsafe_allow_html=True)

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
            st.error("❌ לא ניתן היה ליצור סידור העונה על כל החסימות הקשות. נסה להפחית חסימות.")
        else:
            color_map = {doc: COLORS[i % len(COLORS)] for i, doc in enumerate(doctors)}
            st.markdown(f"### 📋 לוח כוננויות - {HEBREW_MONTHS[sel_month-1]} {sel_year}")
            st.markdown(render_calendar(sel_year, sel_month, assignment, color_map, holidays, personal_prefs), unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown('<div class="sec-header">📊 טבלת צדק (הפרש מקסימלי 1)</div>', unsafe_allow_html=True)
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
            st.download_button("⬇️ הורד כ-CSV", csv, f"schedule_{sel_month}_{sel_year}.csv", "text/csv")
