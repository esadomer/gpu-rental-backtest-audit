"""Generate publication figures and TeX tables directly from computed outputs."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "paper/figures"
TABLE = ROOT / "paper/tables"
LABELS = dict(persistence="Persistence", drift="Drift", local_trend="Local trend",
              damped_trend="Damped trend", pooled_ridge="Pooled ridge")
COLORS = {"persistence":"#183f59", "drift":"#b56f24", "local_trend":"#b74545", "damped_trend":"#648b48", "pooled_ridge":"#8063a4"}


def export(fig, name):
    fig.savefig(FIG / (name + ".pdf"), bbox_inches="tight")
    fig.savefig(FIG / (name + ".png"), dpi=180, bbox_inches="tight")
    plt.close(fig)


def tex_table(filename, columns, rows, alignment):
    text = "\\begin{tabular}{" + alignment + "}\n\\toprule\n"
    text += " & ".join(columns) + " \\\\\n\\midrule\n"
    text += "\n".join(" & ".join(map(str, row)) + " \\\\" for row in rows)
    text += "\n\\bottomrule\n\\end{tabular}\n"
    (TABLE / filename).write_text(text)


def main():
    FIG.mkdir(parents=True, exist_ok=True); TABLE.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size":10, "axes.spines.top":False, "axes.spines.right":False,
                         "axes.titleweight":"bold", "pdf.fonttype":42})
    summary = pd.read_csv(ROOT / "results/forecast_summary.csv")
    run = json.loads((ROOT / "results/run_manifest.json").read_text())
    primary = summary[summary["mode"] == "primary"]
    fig, axes = plt.subplots(1,2,figsize=(10,3.4),layout="constrained")
    for ax, market in zip(axes, ["on_demand","spot"]):
        for model in LABELS:
            frame = primary[(primary.market==market)&(primary.model==model)].sort_values("horizon")
            ax.plot(frame.horizon, frame.male, "o-", label=LABELS[model],color=COLORS[model],linewidth=2 if model=="persistence" else 1.3)
        ax.set(title=market.replace("_"," ").title(), xlabel="Nominal forecast horizon (months)", xticks=[1,3,6],ylim=(0,None))
        ax.grid(axis="y",alpha=.2)
    axes[0].set_ylabel("Mean absolute log error")
    axes[1].legend(frameon=False,fontsize=8)
    export(fig,"forecast_errors")

    fig, axes = plt.subplots(1,2,figsize=(10,3.4),layout="constrained")
    base = primary[primary.model=="persistence"]
    for ax, market in zip(axes,["on_demand","spot"]):
        f=base[base.market==market]; x=np.arange(len(f)); width=.23
        for offset, col, label, color in [(-1,"attrition","Missing targets","#b56f24"),(0,"unchanged_fraction","Unchanged quotes","#183f59"),(1,"repeated_member_fraction","Repeated member","#8063a4")]:
            ax.bar(x+offset*width,100*f[col],width,label=label,color=color)
        ax.set(title=market.replace("_"," ").title(),xticks=x,xticklabels=f.horizon,xlabel="Nominal forecast horizon (months)",ylim=(0,100))
        ax.grid(axis="y",alpha=.2)
    axes[0].set_ylabel("Share (%)")
    axes[1].legend(frameon=False,fontsize=8,loc="upper right")
    export(fig,"coverage_limits")

    timing=pd.read_csv(ROOT / "results/timing_paired_origin_losses.csv")
    timing=timing[timing.model=="persistence"].groupby(["market","horizon"])[["actual","nominal"]].mean().reset_index()
    fig,axes=plt.subplots(1,2,figsize=(10,3.2),layout="constrained")
    for ax,market in zip(axes,["on_demand","spot"]):
        f=timing[timing.market==market];x=np.arange(len(f)); w=.35
        ax.bar(x-w/2,f.actual,w,color="#183f59",label="Archived availability")
        ax.bar(x+w/2,f.nominal,w,color="#b56f24",label="Nominal-label lookahead")
        ax.set(title=market.replace("_"," ").title(),xticks=x,xticklabels=f.horizon,xlabel="Nominal forecast horizon (months)",ylim=(0,None))
        ax.grid(axis="y",alpha=.2)
    axes[0].set_ylabel("Persistence mean absolute log error")
    axes[1].legend(frameon=False,fontsize=8)
    export(fig,"timing_diagnostic")

    rows=[]
    for market in ["on_demand","spot"]:
        for h in [1,3,6]:
            g=primary[(primary.market==market)&(primary.horizon==h)].set_index("model")
            rows.append([market.replace("_"," ").title(),h]+[f"{g.loc[m,'male']:.4f}" for m in LABELS])
    tex_table("accuracy.tex",["Market","$h$","Persist.","Drift","Trend","Damped","Ridge"],rows,"lr"+"r"*5)
    rows=[]
    for _,r in base.iterrows():
        rows.append([r.market.replace("_"," ").title(),int(r.horizon),f"{r.eligible_cases:,}",f"{r.observed_cases:,}",int(r.origins),int(r.providers),f"{100*r.attrition:.1f}\\%",f"{100*r.unchanged_fraction:.1f}\\%"])
    tex_table("coverage.tex",["Market","$h$","Eligible","Observed","Months","Prov.","Missing","Same"],rows,"lr"+"r"*6)
    rows=[]
    for _,r in timing.iterrows():
        rows.append([r.market.replace("_"," ").title(),int(r.horizon),f"{r.actual:.4f}",f"{r.nominal:.4f}",f"{100*(1-r.nominal/r.actual):.1f}\\%"])
    tex_table("timing.tex",["Market","$h$","Actual timing","Nominal label","Apparent reduction"],rows,"lrrrr")
    modes=[("primary","Primary"),("provider_member_freshness","Repeated members removed"),("six_observation_history","Six observations"),("strict_identity","Strict identity"),("ridge_provider_holdout","Provider holdout")]
    rows=[]
    for mode,label in modes:
        for market in ["on_demand","spot"]:
            f=summary[(summary["mode"]==mode)&(summary.market==market)&(summary.horizon==1)].set_index("model")
            if len(f): rows.append([label,market.replace("_"," ").title(),int(f.iloc[0].observed_cases),int(f.iloc[0].origins),f"{f.loc['persistence','male']:.4f}",f"{f.loc['pooled_ridge','male']:.4f}"])
    tex_table("sensitivity.tex",["Specification","Market","Cases","Months","Persist.","Ridge"],rows,"llrrrr")
    macros = {"PanelRows":f"{run['panel']['rows']:,}", "PanelKeys":f"{run['panel']['keys']:,}",
              "EligibleCases":f"{run['primary_eligible_cases']:,}", "ObservedCases":f"{run['primary_observed_cases']:,}",
              "RepricingRows":f"{run['repricing_records']:,}", "RepricingProviderMonths":str(run['repricing_provider_months']),
              "TimingMatches":f"{run['timing']['matched_observed']:,}",
              "TimingFuturePercent":f"{100*run['timing']['nominal_future_predictor_fraction']:.1f}"}
    for market,prefix in [("on_demand","Demand"),("spot","Spot")]:
        for h,suffix in [(1,"One"),(3,"Three"),(6,"Six")]:
            row=base[(base.market==market)&(base.horizon==h)].iloc[0]
            macros[prefix+suffix+"Error"]=f"{row.male:.4f}"
            macros[prefix+suffix+"USD"]=f"{row.mae_usd:.3f}"
            macros[prefix+suffix+"Same"]=f"{100*row.unchanged_fraction:.1f}"
            macros[prefix+suffix+"Repeat"]=f"{100*row.repeated_member_fraction:.1f}"
    (TABLE / "macros.tex").write_text("\n".join("\\newcommand{\\"+key+"}{"+value+"}" for key,value in macros.items())+"\n")
    print("Generated three figures and four tables from result CSVs")


if __name__=="__main__": main()
