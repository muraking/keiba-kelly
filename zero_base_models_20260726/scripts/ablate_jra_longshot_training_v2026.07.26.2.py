"""Test race-specific JRA workout features in longshot top-3 ranking.

Version: v2026.07.26.2
"""
import argparse,json,sqlite3
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
VERSION="v2026.07.26.2"
EX={"race_id","date","venue","horse_id","is_win","is_place","tan_payout","place_payout","finish_pos","is_iruka","win_odds","popularity"}
GRADE={"A":3,"B":2,"C":1,"D":0};LOAD={"一杯":3,"強め":2,"馬なり":1}
def workout(path):
 raw=json.loads(path.read_text(encoding="utf8"));rows=[]
 for horse,entries in raw.items():
  for e in entries:
   works=e.get("works") or [];last=[w.get("last1f") for w in works if isinstance(w.get("last1f"),(int,float))]
   rows.append({"horse_id":str(horse),"race_id":str(e.get("race_id")),"tr_n":e.get("n_works",len(works)),
    "tr_last_min":min(last) if last else np.nan,"tr_last_mean":np.mean(last) if last else np.nan,
    "tr_fast":sum(float(w.get("fast_n") or 0) for w in works),
    "tr_grade":max((GRADE.get(str(w.get("grade")),0) for w in works),default=0),
    "tr_load":max((LOAD.get(str(w.get("load")),0) for w in works),default=0)})
 return pd.DataFrame(rows).drop_duplicates(["race_id","horse_id"],keep="last")
def model():return HistGradientBoostingClassifier(max_iter=180,learning_rate=.055,max_leaf_nodes=31,min_samples_leaf=80,l2_regularization=2,random_state=20260726)
def met(d,p,k):
 x=d.copy();x["s"]=p;x["r"]=x.groupby("race_id").s.rank(method="first",ascending=False);hit=set(x.loc[x.is_place.eq(1),"race_id"]);q=x[x.r.le(k)];caught=set(q.loc[q.is_place.eq(1),"race_id"]);ret=np.where(q.is_place.eq(1),q.place_payout.fillna(0),0)
 return {"capture":100*len(hit&caught)/len(hit),"precision":100*float(q.is_place.mean()),"roi":float(ret.sum()/len(q))}
def main():
 p=argparse.ArgumentParser();p.add_argument("--db",type=Path,required=True);p.add_argument("--training",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--predictions",type=Path);a=p.parse_args()
 with sqlite3.connect(a.db) as c:d=pd.read_sql_query("select * from features",c)
 d.race_id=d.race_id.astype(str);d.horse_id=d.horse_id.astype(str);d=d.merge(workout(a.training),on=["race_id","horse_id"],how="left");d["date"]=pd.to_datetime(d.date)
 for c in d.columns:
  if c not in {"race_id","date","venue","horse_id"}:d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d[d.win_odds.ge(10)&d.is_place.notna()].copy();trcols=["tr_n","tr_last_min","tr_last_mean","tr_fast","tr_grade","tr_load"]
 base=[c for c in d if c not in EX and c not in trcols and pd.api.types.is_numeric_dtype(d[c])]
 variants={"ability":base,"training":base+trcols,"market":base+["win_odds","popularity"],"training_market":base+trcols+["win_odds","popularity"]}
 folds=[];predictions=[]
 for y in (2024,2025,2026):
  tr=d[d.date.dt.year.lt(y)];te=d[d.date.dt.year.eq(y)];out={}
  variant_predictions={}
  for n,cols in variants.items():
   med=tr[cols].replace([np.inf,-np.inf],np.nan).median().fillna(0);x=tr[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32");z=te[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
   m=model();m.fit(x,tr.is_place.astype(int));pred=m.predict_proba(z)[:,1];variant_predictions[n]=pred;out[n]={str(k):met(te,pred,k) for k in (1,2,3)}
  folds.append({"year":y,"variants":out})
  saved=te[["race_id","date","venue","umaban","field_size","finish_pos","is_win","is_place","win_odds","popularity","tan_payout","place_payout"]].copy()
  for n,pred in variant_predictions.items():saved["p_"+n]=pred
  predictions.append(saved)
 a.output.write_text(json.dumps({"version":VERSION,"folds":folds},ensure_ascii=False,indent=2),encoding="utf8")
 if a.predictions:pd.concat(predictions,ignore_index=True).to_csv(a.predictions,index=False)
if __name__=="__main__":main()
