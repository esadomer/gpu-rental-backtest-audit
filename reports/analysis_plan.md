# Analysis plan: forecasting posted GPU rental quotes

Author: H. Esad Kay. This plan is specified after the source audit and before evaluating model performance. It is not a public preregistration. The machine-readable protocol and its SHA-256 fingerprint accompany every result run.

## Question and contribution

How accurately can a future posted rental quote be predicted from admissible earlier catalog records? The intended contribution is a reproducible forecastability audit that separates information timing, observable service identity, missing targets, persistence and provider concentration. It is not a claim of first GPU price forecasting, a novel catalog history, executable arbitrage, or universal financial predictability.

The original new-hardware-versus-rental question remains unsupported by the physical data. No physical-price predictor enters this study.

## Evidence and identity

Use the 37 original gpuhunt ZIP snapshots located through Mittal's pinned public reconstruction, August 2023 through September 2026. The source panel locates archives; its cleaned prices and future-dependent filters are not model inputs. Verify every archive hash. S3 Last-Modified is an archived-object publication proxy, not proof of a historical public ACL, provider refresh or earliest market knowledge.

Use exact A100, H100 and H200 labels, preserving VRAM and service market. GH200 and H100NVL are different products and excluded. Retain AWS, Azure, Lambda, DataCrunch, Nebius, OCI and Verda as separate source labels; do not merge DataCrunch/Verda histories. Exclude GCP and RunPod for the metadata problems documented in the audit, without filtering on future prices. Exclude nonempty flags and invalid/nonpositive essential numeric fields. Deduplicate identical same-archive records; if a core identity has conflicting prices, exclude that identity in that archive and record it.

The primary key is provider, location, instance name, GPU name, VRAM, GPU count, CPU count, RAM and spot/on-demand status. These fields exist in the earliest schema. Optional disk size and CPU architecture have changing reporting coverage. A strict sensitivity adds both, treating missing values literally, with no inferred continuity. Primary-key continuity is not a claim that unrecorded networking, availability, support or contract terms are identical. Where optional fields disagree within a snapshot, exclude the ambiguous core key. Price is instance hourly USD divided by GPU count; it includes the host bundle. No currency conversion or bare-GPU interpretation.

## Forecast schedule and missingness

Primary forecast origins are the eighth day of each month, 00:00 UTC, beginning January 2025. This allows a first-week snapshot to become observable. A source is admissible only after its archived publication proxy. The latest earlier quote may be used as an explicitly aged predictor only if no more than 45 days old; earlier quotes are never inserted as targets. Require 12 historical observations, allowing calendar gaps and using elapsed time in regressions. A six-observation sensitivity describes shorter histories, including H200 when eligible.

Forecast horizons are one, three and six calendar months. The target is the same key's quote in the selected nominal target-month archive, only if published by that target month's eighth day. It is a monthly catalog quote, not an average rental cost over the holding period. A late or absent target is missing. Export every origin-eligible case even if its target later disappears. Restrict origins to horizons ending by September 2026 to avoid mechanical end-of-sample attrition. Report target attrition, quote ages and actual publication-to-origin lead times.

## Fixed model menu

All forecasts are positive. All extrapolated log returns are bounded at plus/minus log(10) relative to the last observed price; report bound activations. No validation search or model selection follows evaluation.

1. Persistence: retain the last price.
2. Drift: extrapolate the first-to-last log-price change per elapsed month through the target cutoff.
3. Local trend: OLS log price on elapsed months over the last 12 observations, anchored at the last price.
4. Damped trend: half the local-trend extrapolated log return.
5. Pooled ridge: direct horizon-specific log return from the last quote to the target. Fixed penalty 0.1 under a weighted mean-squared-error objective, standardized training features and unpenalized intercept. Features: last log return per elapsed month, local log trend, standard deviation of log returns per elapsed month, log current price, log GPU count, log VRAM, spot indicator. Training examples may use four observations, but evaluated primary cases require twelve. Only training targets already published AND with target cutoff no later than the current origin are admissible. Require six distinct matured training-origin months and 30 examples; otherwise explicitly fall back to persistence. Equalize training origin/provider group weights; do not tune the penalty. Fit separately by horizon, pool GPU families and markets, report results separately. Provider holdout removes that provider's training labels but permits its own observed lag features; it is conditional transfer, not cold start.

## Comparisons and uncertainty

For each GPU/VRAM, market, horizon and origin, average absolute log errors within provider, then equally across represented providers, then across origins. Also provide USD-per-GPU-hour MAE. Aggregate headline results balance providers within market/origin before time averaging; do not weight by number of regional rows. Compare all models on the same target-observed cases. Count forecasts, distinct keys, providers, origins, provider-origin groups, unchanged target shares and actual observed repricing events. A percentage improvement is undefined when the baseline loss is zero.

Export paired per-origin alternative-minus-persistence losses. Exploratory 95% circular moving-block bootstrap intervals retain the entire origin cross-section; block length max(3,horizon), 2,000 replicates, seed 27826. Report the small number of blocks and provider leave-one-out sensitivity. Intervals are descriptive stability diagnostics, not strong population inference or independent-trade standard errors. Multiple comparisons are descriptive; do not advertise a selected winner as confirmed.

Sensitivity runs: six historical observations; strict optional-field identity; publication plus 24 hours; conditional provider holdout for ridge. A separate day-one diagnostic compares actual archived availability with naive nominal-month labels on the exact same forecast-origin/key/horizon/target cases. Targets always follow the same day-eight target rule. The nominal-label variant deliberately accesses later records and is not an admissible forecast. Report coverage and paired loss effects separately; do not assume hindsight necessarily improves error.

## Completion and limitations

Deliver traced inputs, reproducible scripts, behavioral tests for timing/missingness/training maturity/weights, result tables, scientific figures, an English LaTeX/PDF manuscript and a concise desk note. Do not claim availability to transact, capacity, executable profit, accepted arXiv classification or verified novelty over an unavailable prior manuscript. The author must review the final manuscript and approve publication and required submission disclosures separately.

## Pre-evaluation plan review amendments

An independent plan review identified repeated provider-member files, ambiguous aggregate weights and numeric-key normalization. All three were accepted before model evaluation. Numeric identity uses finite positive Decimal canonical strings (80 and 80.0 agree); counts must be integers. Text identifiers are trimmed without case or alias matching; raw records remain traceable.

The primary estimand is future **published aggregate-catalog state**, which may repeat stale provider information. Preserve raw member SHA-256 and an order-invariant normalized fingerprint of the entire provider's core offer table (instance, location, price, CPU, RAM, GPU count/name/VRAM and market). Ignore optional schema additions in this fingerprint. Compare with the previous observed member for that provider, including across missing months. Report repeated-member targets separately. A provider_member_freshness sensitivity excludes every repeated semantic member from both histories and targets; a changed member does not prove that every offer was refreshed. This is a conservative diagnostic, not a corrected ground truth.

Headline tables remain separate for on-demand and spot at each horizon. Within each origin, each represented provider has equal weight, and each key within that provider has equal weight. Origins then have equal weight. GPU-specific cells use the same nesting and are reported separately; no single cross-market score is a primary estimand. Ridge training weights use the identical origin/provider/example nesting, including weighted standardization.

Bootstrap blocks run on the full monthly calendar with missing origins retained as missing, not compressed. Suppress intervals if fewer than four block-length equivalents of observed origins are available. Give raw paired differences even when intervals are suppressed.

Implementation clarification before evaluation: the day-one timing diagnostic evaluates the four univariate methods only; it does not fit a deliberately contaminated pooled learner. Its nominal-label availability rule is month-start, while actual publication dates still define elapsed-time regressions. Any negative quote age is explicit lookahead.

## Amendment 01: factual provider-identity correction after the first run

The first evaluation exposed a duplicated economic provider: DataCrunch and Verda are the same company. Their nine overlapping whole-provider core tables are semantically identical; all 810 target Verda rows match DataCrunch exactly. The official November 5, 2025 rebrand notice confirms continuity. The instruction above to retain them as separate modeling providers is superseded by `config/protocol_amendment_01.json`: keep DataCrunch's longer source history, exclude duplicate Verda modeling records, and retain the member inventory and exclusion reason. No history is stitched. A nonidentical alias member is a hard error in this fixed study. This correction removes potential duplicate training labels and six-observation evaluation cases, rather than changing the model menu or selecting outcomes. Initial summaries are preserved in `results/initial_v1/`; the original locked protocol remains unchanged, and final runs fingerprint both documents. Persistence had won all six headline cells before the correction; that first-run result is disclosed rather than concealed.

Implementation review also required unchanged-price and repeated-member rates to use the same origin/provider/key weights as the losses. Final outputs report these balanced rates and retain explicitly named raw-row counterparts. Target attrition remains the raw eligible-case missing fraction. The lock's original status field has been clarified as a statement about the moment of freezing, rather than the current project state; its earlier form is preserved with the first-run outputs.
