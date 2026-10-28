"""Independent output invariants and artifact fingerprints; no data generation."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def verify():
    frame = pd.read_csv(ROOT / "results/forecast_cases.csv", keep_default_na=True)
    observed = frame[frame.target_price.notna()]
    assert not frame.duplicated(["mode", "origin", "horizon", "key"]).any()
    assert (frame.last_published <= frame.origin).all()
    assert (frame.quote_age_days.between(0,45)).all()
    assert (observed.target_published <= observed.target_cutoff).all()
    assert (observed.target_published > observed.origin).all()
    assert (observed.target_status == "observed").all()
    assert (frame.loc[frame.target_price.isna(), "target_status"] != "observed").all()
    assert (frame.ridge_latest_target.fillna("") <= frame.origin).all()
    assert not (frame.provider == "verda").any()
    assert (frame.history_count >= np.where(frame["mode"] == "six_observation_history", 6, 12)).all()
    for model in ("persistence", "drift", "local_trend", "damped_trend", "pooled_ridge"):
        assert np.isfinite(frame[model]).all() and (frame[model] > 0).all()
        ratio = frame[model] / frame.last_price
        assert ratio.between(.1-1e-10,10+1e-10).all()
    assert np.allclose(frame.persistence, frame.last_price)
    # Independently resolve every retained target against the extracted source panel.
    panel = pd.read_csv(ROOT / "data/research/catalog_panel.csv")
    for mode, cases in observed.groupby("mode"):
        key = "strict_key" if mode == "strict_identity" else "key"
        target = panel[[key,"month","price","member_repeated"]].rename(columns={key:"key","month":"target_month","price":"verified_target"})
        joined = cases.merge(target,on=["key","target_month"],validate="many_to_one")
        assert len(joined) == len(cases)
        assert np.allclose(joined.target_price,joined.verified_target,rtol=1e-10)
        if mode == "provider_member_freshness": assert not joined.member_repeated.any()
    # Reconstruct headline losses independently, using explicit nested loops.
    summary = pd.read_csv(ROOT / "results/forecast_summary.csv")
    for _, record in summary.iterrows():
        cases=observed[(observed["mode"]==record["mode"])&(observed.market==record.market)&(observed.horizon==record.horizon)]
        means=[]
        for _, origin in cases.groupby("origin"):
            means.append(np.mean([np.abs(np.log(p[record.model]/p.target_price)).mean() for _,p in origin.groupby("provider")]))
        assert np.isclose(np.mean(means),record.male,rtol=1e-9,atol=1e-12)
    manifest=json.loads((ROOT/"results/run_manifest.json").read_text())
    def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    assert manifest["protocol_sha256"]==sha(ROOT/"config/study_protocol.json")
    assert manifest["protocol_amendment_sha256"]==sha(ROOT/"config/protocol_amendment_01.json")
    for path,checksum in manifest["code_hashes"].items():
        assert sha(ROOT/Path(path))==checksum, f"Code changed since run: {path}"
    result=dict(status="passed",forecast_cases=len(frame),observed_cases=len(observed),
                headline_cells_checked=len(summary),checks=["unique cases","historical inputs","matured training labels",
                "unfilled missing targets","positive bounded forecasts","exact source targets","no duplicate provider alias",
                "independent nested-loss reconstruction","locked protocol and code fingerprints"])
    print(json.dumps(result,indent=2))
    return result


if __name__=="__main__": verify()
