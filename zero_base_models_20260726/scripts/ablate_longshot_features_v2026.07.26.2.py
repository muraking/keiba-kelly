"""Ablate feature groups for odds-10-plus top-3 candidate ranking.

Version: v2026.07.26.2
"""
import argparse,json,sqlite3
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

VERSION="v2026.07.26.2"
EX={"race_id","date","venue","horse_id","is_win","is_place","tan_payout","place_payout",
    "finish_pos","is_iruka","obstacle_time","win_odds","popularity"}
ANA_PREFIX="ana_"
ADV={"h_venue_n","h_venue_winrate","h_venue_avg_rel","h_avg_spd3","h_best_spd5",
     "h_avg_rtop3","h_rank_std","dir_x_umaban"}
def fit():
 return HistGradientBoostingClassifier(max_iter=180,learning_rate=.055,max_leaf_nodes=31,
  min_samples_leaf=80,l2_regularization=2,random_state=20260726)
def score(d,p,k):
 x=d.copy();x["s"]=p;x["r"]=x.groupby("race_id").s.rank(method="first",ascending=False)
 hit=set(x.loc[x.is_place.eq(1),"race_id"]);q=x[x.r.le(k)];caught=set(q.loc[q.is_place.eq(1),"race_id"])
 ret=np.where(q.is_place.eq(1),q.place_payout.fillna(0),0)
 return {"capture":100*len(hit&caught)/len(hit) if hit else 0,"bets":len(q),
  "precision":100*float(q.is_place.mean()),"roi":float(ret.sum()/len(q)) if len(q) else 0}
def main():
 p=argparse.ArgumentParser();p.add_argument("--db",type=Path,required=True);p.add_argument("--market",required=True)
 p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 with sqlite3.connect(a.db) as c:d=pd.read_sql_query("select * from features",c)
 d["date"]=pd.to_datetime(d.date,errors="coerce")
 for c in d.columns:
  if c not in {"race_id","date","venue","horse_id"}:d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d[d.win_odds.ge(10)&d.is_place.notna()].copy();d.race_id=d.race_id.astype(str)
 allnum=[c for c in d if c not in EX and pd.api.types.is_numeric_dtype(d[c])]
 core=[c for c in allnum if not c.startswith(ANA_PREFIX) and c not in ADV]
 variants={"core":core,"core_ana":core+[c for c in allnum if c.startswith(ANA_PREFIX)],
           "core_advanced":core+[c for c in allnum if c in ADV],"full_ability":allnum,
           "full_market":allnum+["win_odds","popularity"]}
 folds=[]
 for y in (2024,2025,2026):
  tr=d[d.date.dt.year.lt(y)];te=d[d.date.dt.year.eq(y)].copy();vr={}
  for name,cols in variants.items():
   med=tr[cols].replace([np.inf,-np.inf],np.nan).median().fillna(0)
   x=tr[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
   z=te[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
   m=fit();m.fit(x,tr.is_place.astype(int));pred=m.predict_proba(z)[:,1]
   vr[name]={str(k):score(te,pred,k) for k in (1,2,3)}
  folds.append({"year":y,"variants":vr})
 a.output.write_text(json.dumps({"version":VERSION,"market":a.market,
  "variant_features":variants,"folds":folds},ensure_ascii=False,indent=2),encoding="utf-8")
 print(a.market,{k:len(v) for k,v in variants.items()})
if __name__=="__main__":main()
