import streamlit as st
import pandas as pd
import calendar
import random
from datetime import date
from collections import defaultdict

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="ניהול כוננויות - גרסה יציבה לחלוטין", page_icon="🏥", layout="wide")

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
.day-num { font-size:.7rem; color:#8aa3b8; font-weight:700; display:block; margin-bottom:3px; }
.badge { display:block; padding:2px 7px; border-radius:11px; font-size:.74rem; font-weight:600; color:#fff; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:115px; }
.badge-heavy { border:2px solid rgba(255,255,255,.4); }
.badge-light { opacity:.85; font-style:italic; }
.fair-table { width:100%; border-collapse:collapse; direction:rtl; font-size:.87rem; }
.fair-table th { background:#1a3a5c; color:#fff; padding:8px 6px; text-align:center; }
.fair-table td { border:1px solid #d6e4f0; padding:6px 10px; text-align:center; }
.fair-table tr:nth-child(even) td { background:#f7fafd; }
div.stButton > button { background:#1a3a5c; color:white; border:none; border-radius:8px; padding:.5rem 1.6rem; font-family:'Heebo',sans-serif; font-size:.95rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# DATA CONVERTERS
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

def get_day_type(d: int, year: int, month: int) -> str:
    wd = date(year, month, d).weekday()
    if wd == 5: return "sat"
    if wd == 4: return "fri"
    return "normal"

# ══════════════════════════════════════════════════════
# ROBUST STAGE-BASED SCHEDULER
# ══════════════════════════════════════════════════════

def build_schedule_deterministic(doctors, year, month, personal_blocks, shift_rules):
    num_days = calendar.monthrange(year, month)[1]
    
    weekend_blocks = []
    for d in range(1, num_days):
        if get_day_type(d, year, month) == "fri" and (d+1) <= num_days:
            weekend_blocks.append((d, d+1))
            
    weekend_days = set()
    for f, s in weekend_blocks:
        weekend_days.add(f)
        weekend_days.add(s)
    weekdays = sorted(list(set(range(1, num_days + 1)) - weekend_days))

    total_slots = num_days * 3
    heavy_slots = num_days * 2
    
    max_total_cap = (total_slots // len(doctors)) + (1 if total_slots % len(doctors) != 0 else 0)
    max_heavy_cap = (heavy_slots // len(doctors)) + (1 if heavy_slots % len(doctors) != 0 else 0)
    max_light_cap = (num_days // len(doctors)) + (1 if num_days % len(doctors) != 0 else 0)

    for attempt in range(4000):
        assignment = {}
        cnt1, cnt2, cnt3 = defaultdict(int), defaultdict(int), defaultdict(int)
        heavy_weekend_assigned = defaultdict(int)
        
        success = True
        
        # שלב א': סופי שבוע כבדים (טור 1 ו-2)
        shuffled_weekends = list(weekend_blocks)
        random.shuffle(shuffled_weekends)
        
        for fri, sat in shuffled_weekends:
            for shift in [1, 2]:
                cands = []
                for d in doctors:
                    if shift not in shift_rules.get(d, [1,2,3]): continue
                    if fri in personal_blocks.get(d, []) or sat in personal_blocks.get(d, []): continue
                    if heavy_weekend_assigned[d] >= 1: continue 
                    cands.append(d)
                
                if not cands:
                    success = False
                    break
                
                min_w = min(heavy_weekend_assigned[d] for d in cands)
                best_cands = [d for d in cands if heavy_weekend_assigned[d] == min_w]
                chosen = random.choice(best_cands)
                
                assignment[(fri, shift)] = chosen
                assignment[(sat, shift)] = chosen
                if shift == 1: cnt1[chosen] += 2
                else: cnt2[chosen] += 2
                heavy_weekend_assigned[chosen] += 1
                
            if not success: break
        if not success: continue

        # שלב ב': סופי שבוע פסיביים (טור 3)
        for fri, sat in weekend_blocks:
            cands = []
            for d in doctors:
                if 3 not in shift_rules.get(d, [1,2,3]): continue
                if fri in personal_blocks.get(d, []) or sat in personal_blocks.get(d, []): continue
                if assignment.get((fri, 1)) == d or assignment.get((fri, 2)) == d: continue
                cands.append(d)
                
            if not cands:
                success = False
                break
            
            chosen = random.choice(cands)
            assignment[(fri, 3)] = chosen
            assignment[(sat, 3)] = chosen
            cnt3[chosen] += 2
            
        if not success: continue

        # שלב ג': ימי חול רגילים
        for day in weekdays:
            for shift in [1, 2, 3]:
                cands = []
                for d in doctors:
                    if shift not in shift_rules.get(d, [1,2,3]): continue
                    if day in personal_blocks.get(d, []): continue
                    if d in [assignment.get((day, s)) for s in [1,2,3] if s != shift]: continue
                    
                    if cnt1[d] + cnt2[d] + cnt3[d] >= max_total_cap: continue
                    if shift in [1, 2] and (cnt1[d] + cnt2[d]) >= max_heavy_cap: continue
                    if shift == 3 and cnt3[d] >= max_light_cap: continue
                    cands.append(d)
                    
                if not cands:
                    success = False
                    break
                
                if shift in [1, 2]:
                    min_h = min(cnt1[d] + cnt2[d] for d in cands)
                    best_cands = [d for d in cands if (cnt1[d] + cnt2
