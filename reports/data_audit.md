# Public GPU Price Data: Audit and Research Decision

Evidence cutoff: **October 28, 2026**. This is a data-feasibility report, not a forecasting paper.

## Decision

**Do not begin a full new-hardware-versus-rental backtest with the sources examined here.** Public rental records provide a substantial starting point. Physical quote histories can also be extracted, but none of the examined histories establishes new condition, seller continuity and comparable product configuration throughout the record. A long H200 physical history was not verified.

Continue with a narrower rental-data investigation. Keep the physical quotes as clearly labeled exploratory evidence. Do not manufacture a missing physical-price series or present an exploratory quote chart as a market index.

This is a bounded audit of named sources. It does not establish that suitable physical data cannot exist elsewhere. No model performance, trading return, hiring outcome or publication acceptance is claimed.

## 1. What counts as an observation?

The audit distinguishes five different quantities:

1. **Raw row:** one record in a source file. It may repeat another record.
2. **Unique capture:** one distinct source, timestamp and quoted price.
3. **Provider-month:** a provider appears for a GPU variant in a month. Regional copies count once for this coverage measure.
4. **Observed price change:** consecutive usable captures show different prices. The actual change may have happened anywhere between those captures.
5. **Executed transaction:** a documented completed purchase or rental. Posted quotes do not establish one.

None of these counts is automatically a statistical effective sample size. Providers respond to common events; sellers can share inventory; many records can reflect one pricing decision. Statistical independence has not been estimated.

## 2. Rental data

The principal input is Rahil Mittal's [gpu-price-history](https://github.com/rahilmittal1/gpu-price-history), pinned to commit `ee8820dd90d7715d8bb57cee03fb0882706d76c5` dated September 29, 2026. This project audits that published reconstruction; it does not claim to have collected its historical prices originally.

The downloaded file contains 76,351 rows. Of these, 30,161 concern A100 40GB, A100 80GB, H100 or H200 in the requested window. They include 1,226 rows explicitly labeled `effective_date_backfill`: a currently observed price was inserted into earlier months. Those records are excluded from the candidate historical observations.

After retaining the source author's `in_index=True` selection, requiring an identified SXM/PCIe/NVL form factor and removing backfills, 12,066 candidate rows remain across all market segments. Rejection reasons overlap and should not be added together. The author's selection already applies geography, source-preference and quality rules; it is not a fresh independent certification of every row.

### On-demand SXM coverage

| GPU | Observed months | Providers over the whole window | Provider-months | Months with at least 3 providers | Provider-months with a same-label price change |
|---|---:|---:|---:|---:|---:|
| A100 40GB | 45, Jan 2023–Sep 2026 | 6 | 227 | 39 | 11 |
| A100 80GB | 45, Jan 2023–Sep 2026 | 10 | 279 | 39 | 21 |
| H100 | 39, Jul 2023–Sep 2026 | 11 | 276 | 34 | 21 |
| H200 | 21, Jan 2025–Sep 2026 | 8 | 131 | 20 | 13 |

Source: local calculations in `data/derived/rental_headline.csv` from the pinned panel.

The last column is deliberately narrow. A comparison requires adjacent months, the same provider, region, source and instance-type label, and different source versions. A changed bundle, missing month or reused snapshot is not a matched comparison. Regional changes in the same provider-month are collapsed. These are candidate repricing observations, not proven independent market events. Stable instance labels do not prove unchanged CPU, memory, networking, availability or service terms.

The 913 provider-months are therefore useful coverage, but not 913 independent prices. Hyperscaler and neocloud observations are combined only in the headline coverage table. Segment-specific outputs remain separate; no blended market-price series is produced.

### Time matters: effective date is not evidence of earlier publication

One concrete example is AWS H100 on-demand in June 2025:

- The panel assigns a price of $6.88/GPU-hour to `2025-06`, with `snapshot_date=2025-06-01`.
- Its cited AWS file is version `20250703204906`.
- The original CSV header says **Publication Date: July 3, 2025, 20:49:06 UTC**. The local cache retains that header.
- The [official AWS announcement](https://aws.amazon.com/about-aws/whats-new/2025/06/pricing-usage-model-ec2-instances-nvidia-gpus/) was posted June 5 and says the on-demand reductions apply beginning June 1.

This is not evidence that the June effective price is false. It is evidence that the cited July artifact cannot by itself establish what a forecaster knew on June 1. The June 5 announcement also shows why the archive's publication date is not necessarily the earliest date the price was public.

The audit flags cited artifacts dated after their nominal month start and reports those dated after month end. For AWS, it uses the date encoded in the version identifier, corroborated against one publication header. For other sources it uses the panel's reported snapshot date. These are **artifact-date diagnostics**, not a fully reconstructed historical information set. Same-day timestamps, original collector logs, revisions and availability still need validation before forecasting.

### Checks against original catalogs

Four selected calculations were independently recomputed from downloaded upstream files:

| Example | Check | Result |
|---|---|---|
| Lambda A100 40GB PCIe, Feb 2023 | Instance price divided by GPU count | $1.10/GPU-hour reproduced |
| RunPod H100 SXM, Jul 2024 | The higher non-spot offer tier at a location | $4.69/GPU-hour reproduced |
| Verda H200 SXM, May 2025 | Four instance sizes divided by their GPU counts | $3.30/GPU-hour reproduced |
| GCP H100 SXM, Oct 2024 | Host price plus eight accelerators, divided by eight | $10.9791/GPU-hour reproduced at stored precision |

These are purposively selected traceability checks across three GPU families and two catalog systems. They are not a random sample or a statistical accuracy estimate. The RunPod tier follows an inference also used by the source author; matching the arithmetic does not independently prove its commercial terms. No downloaded third-party code was executed.

## 3. Physical hardware quotes

The extraction uses the public `homePageItems` JSON embedded in Glass It's HTML. Each update has a timestamp, a price and a source category. Historical condition and seller identity are absent. The extraction uses the actual array rather than page prose or displayed record totals. Record timestamps are Unix milliseconds converted to UTC.

The eight exploratory histories contain 94 `pMsg` entries whose meaning could not be verified. Many occur in regular midnight sequences. They are preserved in the raw inventory but excluded from candidate quote counts, dates, changes and overlap. This does not prove they are synthetic; it avoids asserting that undocumented messages are actual price captures. Unknown categories are also excluded. The extraction retains `pPrice` and `pIncrease` only as **candidate tracker price records**; those labels do not independently certify collection methods, condition or seller history. Categories remain attached to every exported record.

| Tracker | Candidate price records in the window | Recorded months | Distinct prices | Recorded changes | Longest record gap |
|---|---:|---:|---:|---:|---:|
| H100 Newegg | 473 | 29 | 6 | 5 | 155 days |
| H100 Viperatech | 79 | 8 | 7 | 6 | 78 days |
| H100 CDW | 24 | 6 | 3 | 2 | 390 days |
| H100 Amazon | 42 | 8 | 1 | 0 | 120 days |
| A100 40GB Newegg | 813 | 30 | 27 | 33 | 303 days |
| A100 40GB Amazon | 579 | 29 | 152 | 170 | 303 days |
| A100 40GB eBay | 667 | 30 | 164 | 215 | 305 days |
| A100 80GB eBay | 49 | 3 | 1 | 0 | 1 day |

These eight candidates contain **2,820 unique timestamp-price records in the raw extraction inventory**, after 30 exact duplicates are removed. Excluding the 94 ambiguous-category records leaves **2,726 candidate tracker price records**. These are not independent sellers, completed sales or verified new-product observations. All eight histories come through one tracker, so independent collection-method validation is also absent. They remain quarantined from a confirmatory empirical study.

The H100 Newegg title and current product page describe a new PCIe card. That is useful evidence for the current listing, but does not prove that every historical price had the same condition, seller, warranty or availability. CDW has a kit/specification ambiguity. The eBay 40GB series points to a product catalog page, which can represent changing offers. None qualifies unconditionally as a verified new-hardware history.

The extracted counts differ from some current summary fields: A100 Amazon advertises 661 records but the embedded array has 628; A100 eBay 40GB advertises 744 but contains 708. No missing records are invented. The capture-specific metadata and file hashes preserve what was actually obtained.

### Example: many captures, few changes

The strongest H100 candidate, Newegg, records these successive price levels:

| First observed at this level (UTC date) | Posted USD price |
|---|---:|
| 2023-10-25 | 41,789 |
| 2024-09-20 | 44,874 |
| 2024-10-03 | 39,879 |
| 2025-11-26 | 37,879 |
| 2026-06-24 | 29,780 |
| 2026-07-14 | 32,879 |

These are observation dates, not proven dates of the seller's price changes. A 155-day observation gap is left empty. This series is not converted into daily independent observations by forward-filling.

### Rejected and unavailable evidence

A ninth tracker currently titled "H100 New" contains prices beginning in August 2021, before the H100 existed. The audit rejects the entire history for product-identity contamination, including its later dates. Its raw data and rejected classification remain available for inspection.

No long H200 physical history was verified. A recent H200 retail cross-section is a lead for future observation, not a substitute for past prices. Geizhals charts were not obtained as machine-readable historical rows. CCIR's used sales aggregates and modeled hardware values do not satisfy a new bare-card price-history requirement. Epoch's release prices are launch observations, not repeated market observations.

**Verified comparable NEW physical histories: 0 among the examined candidates.** This means the verification standard was not met. It does not mean no new GPUs were sold, or that every tracked product was used. **Verified executed NEW sales: 0 in this audit.**

### Calendar overlap is narrower than the headline rental table

The physical candidates with the clearest form-factor labels are PCIe cards. They cannot be paired with the much wider SXM rental headline table. Matching only exact PCIe labels and observed months gives:

| Physical tracker | Months with both physical and rental records | Longest consecutive shared run | Rental providers seen across the shared window | Shared months with at least 3 rental providers |
|---|---:|---:|---:|---:|
| H100 Newegg | 29 | 17 | 4 | 3 |
| H100 Viperatech | 8 | 3 | 2 | 0 |
| A100 40GB Newegg | 28 | 19 | 1 | 0 |

This is a calendar-overlap diagnostic, not price synchronization: observations within a shared month can be on different days. Condition, seller continuity and rental service terms still prevent certifying a comparable joint panel. A100 40GB's overlap is with one rental provider. Even the best H100 candidate provides only five recorded physical price changes. The full overlap table and exact month lists are in `cross_market_overlap.csv`.

## 4. What can be researched next?

The original question remains useful: **Can GPU purchase prices help predict future rental rates?** The current physical evidence cannot support a strong general answer across all three GPU families.

A more defensible next question is:

> Can public GPU rental prices support reliable forecasts once stale records, late-published data and changes in the service package are accounted for?

This is a candidate scope, not a claim of novelty or a promised paper. Before modeling, build a small panel from original snapshots, preserve the time each price was publicly observable, and fix the exact GPU, provider, location and service package. Prefer A100 and H100 initially because their histories are longer; treat H200 as a shorter extension.

After that panel passes checks, compare simple forecasts at predeclared horizons and multiple time cutoffs. Test whether conclusions survive removing stale records, changing providers and ambiguous service bundles. Add physical prices only as an explicitly limited case study unless better historical evidence becomes available. A new contribution must be distinguished from existing GPU forecasting and price-reconstruction research.

The data gate for the original question would require multiple identifiable sellers, repeated observations of the same new product, enough shared time with rental data, and enough genuine repricing to test forecasts. Merely reaching an arbitrary row count would not pass it. Test power and the number of independent time episodes remain unresolved.

## 5. Verification and limits

- All numeric records originate in public source payloads; this project generated or interpolated no empirical price. This is not certification of each upstream collector's methods. Ambiguous tracker categories are excluded and physical candidates remain exploratory.
- Input bytes are preserved locally with SHA-256 hashes. The audit can rerun offline from those captures.
- Ten synthetic-fixture tests cover date handling, backfill rejection, duplicate captures, ambiguous tracker categories, missing months, changed bundles, regional duplication, cutoff enforcement and invalid values.
- Four selected upstream rental arithmetic checks pass. One AWS publication header is directly checked.
- Whole-panel price accuracy, historical seller/condition continuity, service comparability and true information availability are not fully verified.
- No forecast, fitted equation, profit calculation or executable trading strategy has been produced.
- No private access was requested, no vendor was contacted and no artifact was published.

The next stage should resolve the remaining rental timing and product-definition issues. The present evidence does not justify presenting a full physical-market backtest or promising a strong q-fin preprint.

## Independent review

The first implementation review found that undocumented `pMsg` entries had been included in candidate physical counts. That finding was accepted. The code now preserves all categories, inventories ambiguous entries separately, and excludes them from candidate dates, changes and overlap. A regression test covers the rule.

A fresh second reviewer found no substantive defects. The reviewer independently reconciled rental totals and the 2,820 / 94 / 2,726 physical-record counts, checked all 19 cached input hashes, compared all 2,906 exported raw tracker updates with the cached arrays, and passed all 10 tests. The 2,758 exported candidate-category quote rows include 32 explicitly rejected identity-drift rows; only 2,726 belong to the eight exploratory histories.

The audit owner separately reran the full offline audit and confirmed that all 13 derived files were byte-identical. The read-only reviewers did not rerun that file-writing command. External page claims and whole-market data accuracy were not independently certified.
