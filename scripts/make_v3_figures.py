"""Create supplemental publication tables and figure from verified V3 outputs."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_figures import tex_table

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v3"
LABELS = {"persistence": "Persistence", "drift": "Drift", "local_trend": "Local trend",
          "damped_trend": "Damped trend", "pooled_ridge": "Pooled ridge",
          "frequency_damped_trend": "Frequency-shrunk trend"}
PROVIDERS = {"aws": "AWS", "azure": "Azure", "datacrunch": "DataCrunch",
             "lambdalabs": "Lambda", "nebius": "Nebius", "oci": "OCI"}


def main():
    timing = pd.read_csv(OUT / "timing_sensitivity.csv")
    selected = timing[(timing.market == "on_demand") & (timing.horizon == 1)]
    rows = []
    for r in selected.itertuples():
        if r.slice_type == "single_provider": continue
        label = ("Full sample" if r.slice_type == "full" else
                 "Omit " + PROVIDERS[r.slice_value] if r.slice_type == "leave_one_provider_out" else
                 r.slice_value + " origins")
        rows.append([label, f"{r.paired_cases:,}", r.origins, f"{r.actual_loss:.4f}",
                     f"{r.nominal_loss:.4f}", f"{100*r.relative_reduction:.1f}\\%"])
    tex_table("v3_timing_stability.tex", ["Population", "Cases", "Months", "Actual", "Nominal", "Reduction"], rows, "lrrrrr")

    conditional = pd.read_csv(OUT / "conditional_losses.csv")
    rows = []
    for model, label in LABELS.items():
        r = [label]
        for market in ("on_demand", "spot"):
            for subgroup in ("changed", "unchanged"):
                value = conditional[(conditional.market == market) & (conditional.horizon == 1) &
                                    (conditional.model == model) & (conditional.subgroup == subgroup)].iloc[0]
                r.append(f"{value.male:.4f}")
        rows.append(r)
    tex_table("v3_conditional.tex", ["Model", "OD changed", "OD same", "Spot changed", "Spot same"], rows, "lrrrr")

    attrition = pd.read_csv(OUT / "attrition_summary.csv")
    attrition = attrition[attrition.group_type == "all"]
    rows = []
    for (market, horizon), group in attrition.groupby(["market", "horizon"]):
        g = group.set_index("target_status")
        total = int(g.iloc[0].eligible_cases)
        late = int(g.loc["target_archive_late", "status_cases"])
        absent = int(g.loc["target_key_absent", "status_cases"])
        rows.append([market.replace("_", " ").title(), horizon, f"{total:,}", f"{late:,}",
                     f"{absent:,}", f"{100*absent/(total-late):.1f}\\%"])
    tex_table("v3_attrition.tex", ["Market", "$h$", "Eligible", "Late archive", "Absent key", "Absent / on-time"], rows, "lrrrrr")

    benchmark = pd.read_csv(OUT / "benchmark_summary.csv")
    rows = []
    for (market, horizon), group in benchmark.groupby(["market", "horizon"]):
        g = group.set_index("model")
        rows.append([market.replace("_", " ").title(), horizon,
                     f"{g.loc['persistence', 'male']:.4f}", f"{g.loc['damped_trend', 'male']:.4f}",
                     f"{g.loc['frequency_damped_trend', 'male']:.4f}",
                     f"{100*(-g.loc['frequency_damped_trend', 'skill']):.1f}\\%"])
    tex_table("v3_benchmark.tex", ["Market", "$h$", "Persistence", "Damped", "Freq.-shrunk", "Excess error"], rows, "lrrrrr")

    boot = pd.read_csv(OUT / "timing_bootstrap.csv")
    b = boot[(boot.market == "on_demand") & (boot.horizon == 1) & boot.primary_length].iloc[0]
    loo = selected[selected.slice_type == "leave_one_provider_out"]
    macros = {"TimingBlockLower": 100*b.relative_reduction_ci_low,
              "TimingBlockUpper": 100*b.relative_reduction_ci_high,
              "TimingLooLower": 100*loo.relative_reduction.min(),
              "TimingLooUpper": 100*loo.relative_reduction.max()}
    (ROOT / "paper/tables/v3_macros.tex").write_text("\n".join(
        "\\newcommand{\\" + key + "}{" + f"{value:.1f}" + "}" for key, value in macros.items()) + "\n")

    deletion = pd.read_csv(ROOT / "results/origin_sensitivity/summary.csv")
    rows = []
    for r in deletion.itertuples():
        rows.append([r.market.replace("_", " ").title(), r.horizon, r.deletion_runs,
                     f"{100*r.minimum_reduction:.1f}\\%", r.minimum_omitted_origin,
                     f"{100*r.maximum_reduction:.1f}\\%", r.maximum_omitted_origin])
    tex_table("origin_sensitivity.tex", ["Market", "$h$", "Runs", "Minimum", "Omitted", "Maximum", "Omitted"], rows, "lrrrlrl")

    # Keep missing calendar months as NaNs, rather than joining across absent origins.
    origins = pd.read_csv(OUT / "paired_timing_origins.csv")
    origin = origins[(origins.market == "on_demand") & (origins.horizon == 1)]
    dates = pd.to_datetime(origin.origin_month)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.1), layout="constrained")
    axes[0].plot(dates, origin.actual_loss, "o-", label="Archived availability", color="#183f59", markersize=3)
    axes[0].plot(dates, origin.nominal_loss, "o-", label="Nominal-label lookahead", color="#b56f24", markersize=3)
    axes[0].set(title="Paired one-month on-demand losses", ylabel="Origin-level mean absolute log error", xlabel="Forecast origin")
    ticks = pd.to_datetime(["2025-01", "2025-07", "2026-01", "2026-07"])
    axes[0].set_xticks(ticks, ["Jan 2025", "Jul 2025", "Jan 2026", "Jul 2026"])
    axes[0].legend(frameon=False, fontsize=8)
    single = selected[selected.slice_type == "single_provider"]
    y = np.arange(len(single))
    axes[1].scatter(100*single.relative_reduction, y, color="#183f59", zorder=3)
    axes[1].set_yticks(y, [f"{PROVIDERS[r.slice_value]} ({r.origins} months)" for r in single.itertuples()])
    axes[1].set_ylim(len(single) - .5, -.5)
    axes[1].set(title="Each provider on its own observed origins", xlabel="Apparent MALE reduction (%)", xlim=(-4, 80))
    for yy, r in zip(y, single.itertuples()):
        if np.isnan(r.relative_reduction): axes[1].text(3, yy, "Undefined: both losses zero", va="center", fontsize=8)
    for ax in axes: ax.grid(alpha=.2)
    for extension in ("pdf", "png"):
        fig.savefig(ROOT / f"paper/figures/v3_timing_stability.{extension}", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Generated five supplemental tables, macros and one scientific figure.")


if __name__ == "__main__":
    main()
