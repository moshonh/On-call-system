import streamlit as st
import pandas as pd
import calendar
import random
from datetime import date, timedelta
from collections import defaultdict

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="ניהול כוננויות - חסימת כפל סופ''ש קשיחה", page_icon="🏥", layout="wide")

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght=300;400;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'Heebo',sans-serif; direction:rtl; }
.main-title  { text-align:center; font-size:2.2rem; font-weight:800; color:#1a3a5c; margin-bottom:.1rem; }
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
.fair-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.87rem; }
.fair-table th { background:#1a3a5c; color:#fff; padding:8px 6px; text-align:center; }
.fair-table td { border:1px solid #d6e4f0; padding:6px 10px; text-align:center; }
.fair-table tr:nth-child(even) td { background:#f7fafd; }
.bar-wrap { background:#e8f0f8; border-radius:5px; height:13px; width:100%; }
.bar-fill { border-radius:5px; height:13px; }
div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:8px; padding:.5rem 1.6rem; font-family:'Heebo',sans-serif; font-size:.95rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════
HEBREW_DAYS   = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
HEBREW_MONTHS = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                 "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
SHIFT_LABELS  = {1:"טור 1 (כבד)", 2:"טור 2 (כבד)", 3:"טור 3 (פסיבי)"}
COLORS = ["#2980b9","#27ae60","#8e44ad","#e67e22","#c0392b","#16a085","#d35400","#1a5276","#1abc9c","#922b21","#607d8b"]

DEFAULT_DOCTORS = [
    "הרשקוביץ מ'", "דנין י'", "דומני א:", "סאימן א'", "שלי ש'", 
    "הלר א'", "טלמן ג'", "שיפרין-בונ", "רוזנברג א'", "חטיב מ'", "ווינר ר'"
]

DEFAULT_SHIFT_RULES = {
    "הרשקוביץ מ'": [1, 3], "טלמן ג'": [1, 3], "שלי ש'": [1, 3],
    "סאימן א'": [2, 3], "דנין י'": [2, 3],
}

def parse_day_ranges(raw: str, year: int, month: int) -> list[int]:
    if not raw or not raw.strip(): return []
    num_days = calendar.monthrange(year, month)[1]
    result = set()
    for token in raw.replace(" ", "").split(","):
        if not token: continue
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
    return "normal"

# ══════════════════════════════════════════════════════
# NEW BLOCK-BASED STRICT SCHEDULER
# ══════════════════════════════════════════════════════

def build_schedule(doctors, year, month, holidays, personal_blocks, personal_prefs, shift_rules):
    num_days = calendar.monthrange(year, month)[1]
    num_docs = len(doctors)
    
    total_slots = num_days * 3
    heavy_slots = num_days * 2
    light_slots = num_days
    
    max_total_cap = (total_slots // num_docs) + (1 if total_slots % num_docs != 0 else 0)
    max_heavy_cap = (heavy_slots // num_docs) + (1 if heavy_slots % num_docs != 0 else 0)
    max_light_cap = (light_slots // num_docs) + (1 if light_slots % num_docs != 0 else 0)

    # מיפוי סופי השבוע והחגים כבלוקים קשיחים מראש
    # סופ"ש מוגדר כצמד: [(שישי, shift), (שבת, shift)]
    weekend_blocks = []
    for d in range(1, num_days):
        if get_day_type(d, year, month, holidays) == "fri" and (d+1) <= num_days:
            weekend_blocks.append((d, d+1))
            
    # ימי חול רגילים וימי חג בודדים שאינם סופ"ש
    all_days = set(range(1, num_days + 1))
    weekend_days = set()
    for f, s in weekend_blocks:
        weekend_days.add(f)
        weekend_days.add(s)
    weekday_list = sorted(list(all_days - weekend_days))

    for attempt in range(2000):
        assignment = {}
        cnt1 = defaultdict(int)
        cnt2 = defaultdict(int)
        cnt3 = defaultdict(int)
        
        # מוודא שכל רופא מקבל לכל היותר סופ"ש כבד *אחד* בלבד (שישי+שבת בטור 1 או 2)
        heavy_weekend_count = defaultdict(int)
        success = True

        # שלב 1: שיבוץ סופי שבוע (טור 1 וטור 2 כבדים) - כבלוקים מחוברים לחלוטין
        # נבלבל את סדרי הסופ"שים כדי למנוע הטיה
        shuffled_weekends = list(weekend_blocks)
        random.shuffle(shuffled_weekends)
        
        for fri, sat in shuffled_weekends:
            for shift in [1, 2]:
                # מחפשים רופא אחד שיעשה את כל הסופ"ש (שישי + שבת) באותו הטור
                cands = []
                for d in doctors:
                    if shift not in shift_rules.get(d, [1,2,3]): continue
                    if fri in personal_blocks.get(d, []) or sat in personal_blocks.get(d, []): continue
                    
                    # חסימה קשיחה! אם הוא כבר קיבל סופ"ש כבד החודש, הוא נפסל מיידית
                    if heavy_weekend_count[d] >= 1: continue
                    
                    # בדיקת מכסות כבדות (סופ"ש תופס 2 ימים מהמכסה)
                    if (cnt1[d] + cnt2[d] + 2) > max_heavy_cap: continue
                    if (cnt1[d] + cnt2[d] + cnt3[d] + 2) > max_total_cap: continue
                    
                    cands.append(d)
                
                if not cands:
                    success = False
                    break
                
                # העדפת רופאים עם פחות משמרות כבדות כרגע
                chosen = min(cands, key=lambda d: (cnt1[d] + cnt2[d], cnt1[d] + cnt2[d] + cnt3[d]))
                
                # שיבוץ יומיים רצופים
                assignment[(fri, shift)] = chosen
                assignment[(sat, shift)] = chosen
                if shift == 1: cnt1[chosen] += 2
                else: cnt2[chosen] += 2
                
                heavy_weekend_count[chosen] += 1
                
            if not success: break
        if not success: continue

        # שלב 2: שיבוץ סופי שבוע בטור 3 (פסיבי) - מותר גם למי שכבר עשה סופ"ש כבד!
        for fri, sat in weekend_blocks:
            cands = []
            for d in doctors:
                if 3 not in shift_rules.get(d, [1,2,3]): continue
                if fri in personal_blocks.get(d, []) or sat in personal_blocks.get(d, []): continue
                if assignment.get((fri, 1)) == d or assignment.get((fri, 2)) == d: continue
                if assignment.get((sat, 1)) == d or assignment.get((sat, 2)) == d: continue
                
                if (cnt3[d] + 2) > max_light_cap: continue
                if (cnt1[d] + cnt2[d] + cnt3[d] + 2) > max_total_cap: continue
                cands.append(d)
                
            if not cands:
                success = False
                break
            chosen = min(cands, key=lambda d: (cnt3[d], cnt1[d] + cnt2[d] + cnt3[d]))
            assignment[(fri, 3)] = chosen
            assignment[(sat, 3)] = chosen
            cnt3[chosen] += 2
            
        if not success: continue

        # שלב 3: שיבוץ ימי חול שנותרו (יום אחרי יום, טור אחר טור)
        for day in weekday_list:
            for shift in [1, 2, 3]:
                cands = []
                for d in doctors:
                    if shift not in shift_rules.get(d, [1,2,3]): continue
                    if day in personal_blocks.get(d, []): continue
                    
                    # מניעת כפל משמרות באותו יום חול
                    if d in [assignment.get((day, s)) for s in [1,2,3] if s != shift]: continue
                    
                    # בדיקת מכסות
                    if cnt1[d] + cnt2[d] + cnt3[d] >= max_total_cap: continue
                    if shift in [1, 2] and (cnt1[d] + cnt2[d]) >= max_heavy_cap: continue
                    if shift == 3 and cnt3[d] >= max_light_cap: continue
                    
                    cands.append(d)
                    
                if not cands:
                    success = False
                    break
                
                # העדפה לפי חוסר בשיבוצים
                if shift in [1, 2]:
                    chosen = min(cands, key=lambda d: (cnt1[d] + cnt2[d], cnt1[d] + cnt2[d] + cnt3[d]))
                    if shift == 1: cnt1[chosen] += 1
                    else: cnt2[chosen] += 1
                else:
                    chosen = min(cands, key=lambda d: (cnt3[d], cnt1[d] + cnt2[d] + cnt3[d]))
                    cnt3[chosen] += 1
                    
                assignment[(day, shift)] = chosen
            if not success: break
            
        if success:
            # וידוא שוויוניות מתמטית סופית מוחלטת (הפרשים של לכל היותר יום 1)
            heavy_counts = [cnt1[d] + cnt2[d] for d in doctors]
            light_counts = [cnt3[d] for d in doctors]
            total_counts = [cnt1[d] + cnt2[d] + cnt3[d] for d in doctors]
            
            if (max(heavy_counts) - min(heavy_counts) <= 1 and 
                max(light_counts) - min(light_counts) <= 1 and 
                max(total_counts) - min(total_counts) <= 1):
                
                active_days = {d: cnt1[d] + cnt2[d] for d in doctors}
                passive_days = {
