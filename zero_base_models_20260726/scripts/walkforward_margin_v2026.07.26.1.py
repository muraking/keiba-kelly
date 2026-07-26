"""Walk-forward distance-corrected margin model and calibrated probabilities.

Version: v2026.07.26.1
"""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import log_loss, mean_absolute_error

VERSION = "v2026.07.26.1"
EXCLUDE = {"race_id","date","venue","horse_id","is_win","is_place","win_odds",
           "popularity","tan_payout","place_payout","finish_pos","is_iruka",
           "obstacle_time"}

def softmax(scores, races, t):
    x=pd.Series(scores/t,index=races.index); x-=x.groupby(races).transform("max")
    e=np.exp(x); return (e/e.groupby(races).transform("sum")).to_numpy()

def temperature(scores,races,y):
    return float(minimize_scalar(lambda t:log_loss(y,np.clip(softmax(scores,races,t),1e-8,1-1e-8)),
                                 bounds=(.05,10),method="bounded").x)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--features-db",type=Path,required=True)
    p.add_argument("--runs-db",type=Path,required=True); p.add_argument("--market",required=True)
    p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    with sqlite3.connect(a.features_db) as c: f=pd.read_sql_query("select * from features",c)
    with sqlite3.connect(a.runs_db) as c:
        r=pd.read_sql_query("select race_id,umaban,finish_time from runs",c)
    for d in (f,r): d["race_id"]=d["race_id"].astype(str)
    f["date"]=pd.to_datetime(f["date"],errors="coerce")
    f=f.merge(r,on=["race_id","umaban"],how="left")
    for col in f.columns:
        if col not in {"race_id","date","venue","horse_id"}: f[col]=pd.to_numeric(f[col],errors="coerce")
    winner=f.groupby("race_id")["finish_time"].transform("min")
    f["margin1000"]=((f["finish_time"]-winner)*1000/f["distance"].clip(lower=1)).clip(0,8)
    f=f[f["margin1000"].notna()&f["is_win"].notna()].copy()
    feats=[c for c in f if c not in EXCLUDE|{"finish_time","margin1000"} and pd.api.types.is_numeric_dtype(f[c])]
    folds=[]
    for year in (2024,2025,2026):
        tr=f[f.date.dt.year<year].sort_values(["race_id","umaban"]).copy()
        te=f[f.date.dt.year==year].sort_values(["race_id","umaban"]).copy()
        med=tr[feats].replace([np.inf,-np.inf],np.nan).median().fillna(0)
        xtr=tr[feats].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
        xte=te[feats].replace([np.inf,-np.inf],np.nan).fillna(med).astype("float32")
        calyear=int(tr.date.dt.year.max()); cal=tr.date.dt.year.eq(calyear)
        base=~cal
        if not base.any():
            cut=tr.date.quantile(.8); cal=tr.date.ge(cut); base=~cal
        tmp=HistGradientBoostingRegressor(max_iter=180,learning_rate=.055,max_leaf_nodes=31,
                min_samples_leaf=80,l2_regularization=2,random_state=20260726)
        tmp.fit(xtr[base],tr.loc[base,"margin1000"])
        t=temperature(-tmp.predict(xtr[cal]),tr.loc[cal,"race_id"],tr.loc[cal,"is_win"].astype(int).to_numpy())
        model=HistGradientBoostingRegressor(max_iter=180,learning_rate=.055,max_leaf_nodes=31,
                min_samples_leaf=80,l2_regularization=2,random_state=20260726)
        model.fit(xtr,tr.margin1000); pred=model.predict(xte)
        prob=softmax(-pred,te.race_id,t)
        folds.append({"year":year,"rows":len(te),"temperature":t,
            "margin_mae":float(mean_absolute_error(te.margin1000,pred)),
            "probability_logloss":float(log_loss(te.is_win.astype(int),prob)),
            "probability_sum_max_error":float(pd.Series(prob).groupby(te.race_id.reset_index(drop=True)).sum().sub(1).abs().max())})
    a.output.write_text(json.dumps({"version":VERSION,"market":a.market,"features":feats,"folds":folds},
                                  ensure_ascii=False,indent=2),encoding="utf-8")
    print(a.market,folds)
if __name__=="__main__": main()
