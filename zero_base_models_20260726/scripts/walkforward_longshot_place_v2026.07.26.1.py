"""Dedicated OOS model for top-3 finishes among horses at win odds >= 10.

Version: v2026.07.26.1
"""
import argparse,json,sqlite3
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

VERSION="v2026.07.26.1"
EX={"race_id","date","venue","horse_id","is_win","is_place","tan_payout",
     "place_payout","finish_pos","is_iruka","obstacle_time","win_odds","popularity"}
def model(): return HistGradientBoostingClassifier(max_iter=200,learning_rate=.05,max_leaf_nodes=31,
 min_samples_leaf=80,l2_regularization=2,random_state=20260726)
def metrics(d,k,score):
 d=d.copy();d["score"]=score;d["r"]=d.groupby("race_id").score.rank(method="first",ascending=False)
 hit=set(d.loc[d.is_place.eq(1),"race_id"]);p=d[d.r.le(k)]
 caught=set(p.loc[p.is_place.eq(1),"race_id"]);ret=np.where(p.is_place.eq(1),p.place_payout.fillna(0),0)
 return {"hit_races":len(hit),"caught":len(hit&caught),"capture":100*len(hit&caught)/len(hit) if hit else 0,
 "bets":len(p),"hits":int(p.is_place.sum()),"precision":100*float(p.is_place.mean()),
 "roi":float(ret.sum()/len(p)) if len(p) else 0}
def main():
 p=argparse.ArgumentParser();p.add_argument("--db",type=Path,required=True);p.add_argument("--market",required=True)
 p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 with sqlite3.connect(a.db) as c:d=pd.read_sql_query("select * from features",c)
 d["date"]=pd.to_datetime(d.date,errors="coerce")
 for x in d.columns:
  if x not in {"race_id","date","venue","horse_id"}:d[x]=pd.to_numeric(d[x],errors="coerce")
 d=d[d.win_odds.ge(10)&d.is_place.notna()].copy();d.race_id=d.race_id.astype(str)
 base=[x for x in d if x not in EX and pd.api.types.is_numeric_dtype(d[x])]
 folds=[]
 for y in (2024,2025,2026):
  tr=d[d.date.dt.year.lt(y)];te=d[d.date.dt.year.eq(y)].copy()
  med=tr[base].replace([np.inf,-np.inf],np.nan).median().fillna(0)
  xb=tr[base].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
  xt=te[base].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
  ability=model();ability.fit(xb,tr.is_place.astype(int));pa=ability.predict_proba(xt)[:,1]
  market_features=base+["win_odds","popularity"]
  medm=tr[market_features].replace([np.inf,-np.inf],np.nan).median().fillna(0)
  xm=tr[market_features].replace([np.inf,-np.inf],np.nan).fillna(medm).astype("float32")
  xmt=te[market_features].replace([np.inf,-np.inf],np.nan).fillna(medm).astype("float32")
  residual=model();residual.fit(xm,tr.is_place.astype(int));pr=residual.predict_proba(xmt)[:,1]
  folds.append({"year":y,"ability":{str(k):metrics(te,k,pa) for k in (1,2,3)},
   "market_residual":{str(k):metrics(te,k,pr) for k in (1,2,3)}})
 a.output.write_text(json.dumps({"version":VERSION,"market":a.market,"rows":len(d),"features":base,
  "folds":folds},ensure_ascii=False,indent=2),encoding="utf-8")
 print(a.market,len(d))
if __name__=="__main__":main()
