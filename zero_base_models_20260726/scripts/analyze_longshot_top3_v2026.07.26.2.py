"""Evaluate per-race top-3 candidates among horses at win odds >= 10.

Version: v2026.07.26.2
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

VERSION="v2026.07.26.2"

def summarize(frame, selected):
    hit_races=set(frame.loc[(frame.win_odds>=10)&(frame.is_place==1),"race_id"])
    picked=frame[selected]
    caught=set(picked.loc[picked.is_place==1,"race_id"])
    returns=np.where(picked.is_place.eq(1),picked.place_payout.fillna(0),0)
    return {"eligible_hit_races":len(hit_races),"caught_races":len(hit_races&caught),
      "capture_rate":100*len(hit_races&caught)/len(hit_races) if hit_races else 0,
      "bets":len(picked),"hits":int(picked.is_place.sum()),
      "precision":float(picked.is_place.mean()*100) if len(picked) else 0,
      "roi":float(returns.sum()/len(picked)) if len(picked) else 0,
      "avg_odds":float(picked.win_odds.mean()) if len(picked) else 0}

def main():
    p=argparse.ArgumentParser();p.add_argument("--oos",type=Path,required=True)
    p.add_argument("--market",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    d=pd.read_csv(a.oos,parse_dates=["date"]); d=d[d.win_odds>=10].copy()
    d["long_rank"]=d.groupby("race_id").p_place.rank(method="first",ascending=False)
    rules=[]
    for k in (1,2,3):
      for pmin in (0,.08,.12,.16,.20):
       for omax in (20,30,50,80,999):
        periods={}
        for y in (2024,2025,2026):
         x=d[d.date.dt.year.eq(y)]
         periods[str(y)]=summarize(x,x.long_rank.le(k)&x.p_place.ge(pmin)&x.win_odds.le(omax))
        rules.append({"top_k":k,"pmin":pmin,"odds_max":omax,"periods":periods})
    confirmed=[r for r in rules if all(r["periods"][str(y)]["roi"]>=100 for y in (2024,2025,2026))
               and r["periods"]["2025"]["bets"]>=100 and r["periods"]["2026"]["bets"]>=50]
    best=sorted(rules,key=lambda r:(r["periods"]["2024"]["capture_rate"],r["periods"]["2024"]["roi"]),reverse=True)
    a.output.write_text(json.dumps({"version":VERSION,"market":a.market,"rules":len(rules),
      "confirmed":confirmed,"top_capture":best[:20],"all_rules":rules},
      ensure_ascii=False,indent=2),encoding="utf-8")
    print(a.market,"rules",len(rules),"confirmed",len(confirmed))
if __name__=="__main__":main()
