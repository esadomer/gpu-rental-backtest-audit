# Prior-work overlap audit

Checked October 28, 2026. Scope: the public repository, release metadata, described manuscript and accessible author/publication pages. No author was contacted and no downloaded source code was executed.

## Version and manuscript access

The current public `main` of [Rahil Mittal's gpu-price-history repository](https://github.com/rahilmittal1/gpu-price-history) equals the revision used to locate this study's archives: [`ee8820dd90d7715d8bb57cee03fb0882706d76c5`](https://github.com/rahilmittal1/gpu-price-history/commit/ee8820dd90d7715d8bb57cee03fb0882706d76c5), dated September 29, 2026. No newer public implementation was available in this check.

The companion manuscript is titled **Reconstructing Cloud GPU Price Histories from Versioned Public Sources: A Pipeline, an Open Dataset, and a Decade of Measurements**. Its [CITATION.cff](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/CITATION.cff) reports `submitted` and "Under review." Those are author-reported statuses, not independently verified editorial decisions.

The 538-entry public tree contains figure PDFs but no manuscript PDF or TeX. The two [public releases](https://github.com/rahilmittal1/gpu-price-history/releases) have no attached assets. Exact-title, author/title and arXiv searches and the [author's public website](https://rahilmittal1.github.io/) did not locate a full manuscript. This search does not prove that no copy exists elsewhere. The full paper's possible additional experiments remain unknown.

## What is already covered

| Topic | Public evidence | Consequence for this study |
|---|---|---|
| Historical reconstruction and provenance | [Rental-data documentation](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/data/rent/README.md) records a larger multi-source panel, versions, dates and quality flags. | The 37 archive identifiers originate from that reconstruction. Independent reparsing is reproducibility work, not discovery of the historical dataset. |
| Publication versus nominal/effective dates | [SYSEVAL.md, V.4](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/analysis/syseval/SYSEVAL.md#v4-known-event-alignment), lines 917-933, explains the June 2025 AWS event and its later observability. V.5, lines 963-987, quantifies late snapshots. | The timing warning itself is not new. The narrower result here is its measured effect on a fixed matched-case forecast comparison. |
| DataCrunch/Verda duplication | [data/rent/README.md](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/data/rent/README.md), lines 350-351, identifies identical copies; [build_rent_panel.py](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/data/rent/build_rent_panel.py), lines 633-635, removes one. | The correction in this project repairs its own initial parser; it is not a new market discovery. |
| Service matching and survivor selection | [Index construction](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/data/rent/README.md#index-construction), lines 493-504, defines matched-item indexes and identifies spot-offer survival bias. | Neither service identity preservation nor concern about disappearing offers is claimed as an original concept. |
| Price rigidity | [RESULTS_v2.md, section 5](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/analysis/out/RESULTS_v2.md#5-how-often-prices-change-like-for-like-b4) measures like-for-like repricing frequency. | Persistence is an economically plausible benchmark given existing evidence; unchanged quotes are not a separate novelty claim. |
| Point-in-time analysis | [analysis/decision.py](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/analysis/decision.py), lines 1-10, restricts throughput information by publication date; [mlperf_cost.py](https://github.com/rahilmittal1/gpu-price-history/blob/ee8820dd90d7715d8bb57cee03fb0882706d76c5/analysis/mlperf_cost/mlperf_cost.py), function `asof`, implements publication matching. | This project does not claim the first information-admissible compute analysis. Contemporaneous service selection differs from forecasting future rental quotes. |

## What differs from the inspected public implementation

The present project evaluates future same-service catalog quotes at rolling origins and one-, three- and six-month horizons. It uses matured training labels, five fixed models, explicit eligible/missing target accounting and a paired month-start diagnostic. On identical matched cases, granting nominal-month information lowers one-month on-demand persistence mean absolute log error by 42.0%. This quantifies a forecasting consequence of an already documented temporal issue.

A static scan of all 44 public Python scripts and their analysis function inventories did not locate an equivalent future-rental rolling forecast pipeline or the exact matched forecast-loss comparison. The inspected implementation focuses on reconstruction, indexes, descriptive measurement and cost-normalized contemporaneous choices. Absence from these inspected files is evidence about the public repository, not proof about the unavailable manuscript or the whole literature.

The whole-provider normalized-state repetition exclusion and optional-field identity sensitivity are additional operational controls in this forecast experiment. They extend existing staleness and entity-resolution concerns. Their changed samples cannot identify causal staleness effects; strict optional-field identity leaves no six-month evaluation.

## Defensible positioning

The contribution is **incremental methodological evidence about the validity of public-catalog forecast evaluation**. The clearest result is the exact-matched timing diagnostic. The work does not introduce GPU price-history reconstruction, service matching, staleness analysis, price rigidity, or point-in-time reasoning. It does not establish priority over the unavailable full manuscript, an independent economic discovery, or publication acceptance.
