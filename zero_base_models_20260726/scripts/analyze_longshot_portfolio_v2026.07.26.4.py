"""Search race filters and ticket roles around OOS longshot candidates.

2024 ranks fixed rules; 2025 and 2026 are untouched confirmations.
Version: v2026.07.26.4
"""
from __future__ import annotations
import argparse,json,sqlite3
from itertools import permutations
from pathlib import Path
import numpy as np,pandas as pd

VERSION="v2026.07.26.4"
KINDS=("tan","fuku","umaren","wide","sanfuku","santan1","santan2","santan3")
def pair(a,b):return "-".join(map(str,sorted((a,b))))
def trio(a,b,c):return "-".join(map(str,sorted((a,b,c))))
def tickets(kind,axis,partners):
 if kind in ("tan","fuku"):return [str(axis)]
 if kind in ("umaren","wide"):return [pair(axis,partners[0])] if partners else []
 if kind=="sanfuku":return [trio(axis,*partners[:2])] if len(partners)>=2 else []
 if kind.startswith("santan") and len(partners)>=2:
  pos=int(kind[-1]);out=[]
  for a,b in permutations(partners[:2],2):
   order=(axis,a,b) if pos==1 else ((a,axis,b) if pos==2 else (a,b,axis))
   out.append(">".join(map(str,order)))
  return out
 return []
def build(oos,db):
 d=pd.read_csv(oos,parse_dates=["date"]);d=d[d.win_odds.ge(10)].copy()
 d["hole_rank"]=d.groupby("race_id").p_place.rank(method="first",ascending=False)
 d=d[d.hole_rank.le(3)].copy()
 with sqlite3.connect(db) as c:p=pd.read_sql_query("select race_id,bet_type,comb,payout from payouts",c)
 p.race_id=p.race_id.astype(str);pay={(x.race_id,x.bet_type,str(x.comb)):float(x.payout) for x in p.itertuples()}
 covered={(x.race_id,x.bet_type) for x in p.itertuples()}
 rows=[]
 full=pd.read_csv(oos,parse_dates=["date"])
 hole_groups={str(race):group for race,group in d.groupby(d.race_id.astype(str),sort=False)}
 for race,g in full.groupby("race_id",sort=False):
  holes=hole_groups.get(str(race))
  if holes is None:continue
  order=g.sort_values("p_win",ascending=False)
  fav=float(order.p_win.iloc[0]);favodds=float(order.win_odds.iloc[0]);field=int(g.field_size.iloc[0])
  tan_covered=g.tan_payout.notna().any()
  fuku_covered=g.place_payout.notna().any()
  for h in holes.itertuples():
   axis=int(h.umaban);partners=[int(x) for x in order.umaban if int(x)!=axis][:2]
   row={"race_id":str(race),"date":h.date,"venue":h.venue,"axis":axis,"hole_rank":h.hole_rank,
        "p_place":h.p_place,"odds":h.win_odds,"popularity":h.popularity,"field":field,
        "fav_p":fav,"fav_odds":favodds}
   for kind in KINDS:
    ts=tickets(kind,axis,partners);ptype=kind.rstrip("123")
    if kind=="tan":
     row[kind+"_covered"]=bool(tan_covered)
     row[kind+"_bets"]=1
     row[kind+"_return"]=float(h.tan_payout) if h.is_win==1 and pd.notna(h.tan_payout) else 0
    elif kind=="fuku":
     row[kind+"_covered"]=bool(fuku_covered)
     row[kind+"_bets"]=1
     row[kind+"_return"]=float(h.place_payout) if h.is_place==1 and pd.notna(h.place_payout) else 0
    else:
     row[kind+"_covered"]=(str(race),ptype) in covered
     row[kind+"_bets"]=len(ts);row[kind+"_return"]=sum(pay.get((str(race),ptype,t),0) for t in ts)
   rows.append(row)
 return pd.DataFrame(rows)
def summary(x,kind):
 x=x[x[kind+"_covered"]]
 bets=int(x[kind+"_bets"].sum())
 if not bets:return {"races":0,"bets":0,"hits":0,"roi":0,"lcb90":-999}
 ret=x[kind+"_return"].to_numpy();units=ret/(x[kind+"_bets"].to_numpy()*100)
 se=units.std(ddof=1)/np.sqrt(len(units)) if len(units)>1 else 999;total=ret.sum()
 return {"races":len(x),"bets":bets,"hits":int((ret>0).sum()),"hit_rate":float((ret>0).mean()*100),
  "roi":float(total/(bets*100)*100),"lcb90":float(units.mean()-1.2816*se),
  "max_share":float(ret.max()/total) if total else None}
def main():
 p=argparse.ArgumentParser();p.add_argument("--oos",type=Path,required=True);p.add_argument("--db",type=Path,required=True)
 p.add_argument("--market",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 d=build(a.oos,a.db);rules=[]
 for hr in (1,2,3):
  for lo,hi in ((10,20),(10,30),(15,50),(20,80),(10,80)):
   for pmin in (.08,.12,.16,.20):
    for fmin in (0,.25,.35):
     for fsmin in (0,8,10):
      mask=d.hole_rank.le(hr)&d.odds.between(lo,hi)&d.p_place.ge(pmin)&d.fav_p.ge(fmin)&d.field.ge(fsmin)
      for kind in KINDS:
       periods={str(y):summary(d[mask&d.date.dt.year.eq(y)],kind) for y in (2024,2025,2026)}
       rules.append({"hole_rank":hr,"odds":[lo,hi],"pmin":pmin,"fav_pmin":fmin,"field_min":fsmin,
                     "bet_type":kind,"periods":periods})
 discovery=sorted([r for r in rules if r["periods"]["2024"]["bets"]>=100],
  key=lambda r:(r["periods"]["2024"]["lcb90"],r["periods"]["2024"]["roi"]),reverse=True)
 confirmed=[r for r in discovery if all(r["periods"][str(y)]["roi"]>=100 for y in (2024,2025,2026))
  and r["periods"]["2025"]["bets"]>=100 and r["periods"]["2026"]["bets"]>=50
  and r["periods"]["2025"]["max_share"] is not None and r["periods"]["2025"]["max_share"]<=.20]
 a.output.write_text(json.dumps({"version":VERSION,"market":a.market,"candidate_rows":len(d),
  "rules_tested":len(rules),"confirmed":confirmed,"top_2024":discovery[:50],
  "all_rules":rules},ensure_ascii=False,indent=2),encoding="utf-8")
 print(a.market,"candidates",len(d),"rules",len(rules),"confirmed",len(confirmed))
if __name__=="__main__":main()
