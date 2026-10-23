"""Seed realistic demo data: python seed.py"""
import json, datetime as dt
from pathlib import Path
t = dt.date.today()
def day(n): return (t - dt.timedelta(days=n)).isoformat()
moods = [4, 4, 3, 4, 3, 2, 2]
ck = [{"date": day(6 - i), "mood": m, "meds_taken": ["BP tablet", "Vitamin D"] if i < 4 else ["Vitamin D"],
       "symptoms": "dizzy in the morning" if i >= 5 else ""} for i, m in enumerate(moods)]
mem = [
 {"date": day(5), "theme": "love", "year": "1962", "people": ["Raman"],
  "story": "I met Raman at my cousin's wedding in Madurai. He spilled sambar on my silk saree and apologised for an hour."},
 {"date": day(3), "theme": "food", "year": "1970s", "people": ["children"],
  "story": "My pongal on festival mornings. The secret was a spoon of ghee and black pepper roasted in the pot."},
 {"date": day(1), "theme": "festival", "year": "1960s", "people": ["Amma"],
  "story": "Amma drew kolam at dawn and let me pick the colours. I was never allowed to touch the rice flour."}]
Path("data.json").write_text(json.dumps({"people": {"paati": {"name": "Paati", "meds": ["BP tablet", "Vitamin D"],
                                         "checkins": ck, "memories": mem}}}, indent=2), encoding="utf-8")
print("seeded: person 'Paati'")
