"""Test leakage-safe sire and broodmare-sire rates in longshot ranking.

Version: v2026.07.26.1
"""
import argparse,json,sqlite3
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
VERSION="v2026.07.26.1"
EX={"race_id","date","venue","horse_id","is_win","is_place","tan_payout","place_payout",
 "finish_pos","is_iruka","obstacle_time","win_odds","popularity"}
def model():return HistGradientBoostingClassifier(max_iter=180,learning_rate=.055,max_leaf_nodes=31,min_samples_leaf=80,l2_regularization=2,random_state=20260726)
def rank_metrics(d,p,k=1):
 x=d.copy();x["s"]=p;x["r"]=x.groupby("race_id").s.rank(method="first",ascending=False)
 hit=set(x.loc[x.is_place.eq(1),"race_id"]);q=x[x.r.le(k)];caught=set(q.loc[q.is_place.eq(1),"race_id"])
 ret=np.where(q.is_place.eq(1),q.place_payout.fillna(0),0)
 return {"capture":100*len(hit&caught)/len(hit),"precision":100*float(q.is_place.mean()),"roi":float(ret.sum()/len(q))}
def rates(train,test,col):
 base=float(train.is_place.mean());g=train.groupby(col).is_place.agg(["sum","count"])
 rate=(g["sum"]+30*base)/(g["count"]+30)
 return test[col].map(rate).fillna(base),test[col].map(g["count"]).fillna(0)
def main():
 p=argparse.ArgumentParser();p.add_argument("--db",type=Path,required=True);p.add_argument("--pedigree",type=Path,required=True)
 p.add_argument("--market",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 with sqlite3.connect(a.db) as c:d=pd.read_sql_query("select * from features",c)
 ped=json.loads(a.pedigree.read_text(encoding="utf8"));pm={str(k):v for k,v in ped.items()}
 d["date"]=pd.to_datetime(d.date,errors="coerce");d["horse_id"]=d.horse_id.astype(str)
 d["sire"]=d.horse_id.map(lambda h:pm.get(h,{}).get("father",""))
 d["bms"]=d.horse_id.map(lambda h:pm.get(h,{}).get("mother_father",""))
 for c in d.columns:
  if c not in {"race_id","date","venue","horse_id","sire","bms"}:d[c]=pd.to_numeric(d[c],errors="coerce")
 d=d[d.win_odds.ge(10)&d.is_place.notna()].copy();d.race_id=d.race_id.astype(str)
 feats=[c for c in d if c not in EX|{"sire","bms"} and pd.api.types.is_numeric_dtype(d[c])]
 folds=[]
 for y in (2024,2025,2026):
  tr=d[d.date.dt.year.lt(y)].copy();te=d[d.date.dt.year.eq(y)].copy()
  for col in ("sire","bms"):
   tr[col+"_rate"],tr[col+"_n"]=rates(tr,tr,col);te[col+"_rate"],te[col+"_n"]=rates(tr,te,col)
  variants={"ability":feats,"pedigree":feats+["sire_rate","sire_n","bms_rate","bms_n"],
   "pedigree_market":feats+["sire_rate","sire_n","bms_rate","bms_n","win_odds","popularity"]}
  out={}
  for name,cols in variants.items():
   med=tr[cols].replace([np.inf,-np.inf],np.nan).median().fillna(0)
   x=tr[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32");z=te[cols].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
   m=model();m.fit(x,tr.is_place.astype(int));pred=m.predict_proba(z)[:,1]
   out[name]={str(k):rank_metrics(te,pred,k) for k in (1,2,3)}
  folds.append({"year":y,"variants":out})
 a.output.write_text(json.dumps({"version":VERSION,"market":a.market,"folds":folds},ensure_ascii=False,indent=2),encoding="utf8")
 print(a.market)
if __name__=="__main__":main()
