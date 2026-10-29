# Version 3: exploratory supplemental analysis plan

Author: H. Esad Kay. Specified October 29, 2026, after the V2 results were known and before calculating the additional results below. This is not a preregistration or an independent confirmation sample. The original five-model protocol and original numerical outputs remain unchanged. The supplement and its input fingerprints are frozen in `config/v3_supplement.json` and `config/v3_supplement_lock.json`.

## Timing-result stability

Reconstruct the exact observed day-one actual/nominal intersection, requiring unique service/origin/horizon identities and identical target prices, target publication times and target cutoffs. Use persistence throughout. Average losses within provider-origin and then across providers and origins, exactly as in the original comparison.

Resample paired actual/nominal origin losses together using circular contiguous calendar blocks, 2,000 draws and seed 27826. Retain every calendar month from January 2025 through September 2026 minus the horizon, including missing endpoints and interior months. Recalculate both the absolute error reduction (actual minus nominal MALE) and relative reduction (one minus nominal MALE divided by actual MALE) in every draw. The primary block length is max(3, horizon); lengths 2, 3, 4 and 6 are additional descriptive sensitivities, not a search for a favorable interval. Blocks shorter than a forecast horizon do not adequately accommodate horizon overlap and are not primary evidence.

Suppress intervals when fewer than four block-length equivalents of observed origins remain. Export attempted, usable and zero-baseline draw counts. A zero actual loss makes a relative reduction undefined: suppress its interval if any otherwise usable draw has a zero denominator, retaining an absolute-difference interval where possible. Resampling does not create synthetic price series or increase the number of economic observations. With few months and potentially changing regimes, intervals are descriptive stability diagnostics, not guaranteed confidence coverage or population significance.

Report full-sample, single-provider, leave-one-provider-out and fixed 2025/2026 origin-year comparisons. Recalculate nested weights for each of these different populations, disclose represented and lost origins, and leave undefined/empty statistics missing. Year slices are by forecast origin, not target year. Provider/year changes also change time support and composition; they are not causal decompositions. Only the full cells receive bootstrap intervals.

## Changed-price targets and loss decomposition

Partition each primary observed market/horizon cell into changed and unchanged outcomes using the original numerical tolerance (relative 1e-10, absolute 1e-12). Compute the complete cell's origin/provider/key weights **once**. If the subgroup has mass s, its conditional loss is the weighted loss contribution divided by s. Changed and unchanged contributions must sum to the original overall loss for each model, in both log and dollar units.

These are conditional losses in the original weighted evaluation population, not newly balanced subgroup scores. Report raw subgroup rows, services, provider-origin groups and origin months. Subgroup membership uses the realized target and is therefore an explanatory, ex-post diagnostic; it cannot be used to select a deployable forecast sample. Empty subgroup losses remain missing. No changed-only significance test is claimed.

## Missing targets and selection

Keep every original eligible primary case. Separate observed targets, late target archives, absent target keys and any other original status. Lateness takes precedence in the original target rules: when an archive is late, these records do not establish whether its service key would otherwise exist. An absent key likewise does not certify permanent delisting or lost physical capacity.

Report counts by market/horizon, provider, GPU/VRAM, origin year and provider/GPU. Give raw proportions and proportions derived from original eligible-cell nested weights, with denominators clearly identified. Include distinct origins, target months and provider-origin groups; thousands of missing rows can arise from a few shared archive events. Compare raw-case means of last price, quote age, history length, absolute last return, return volatility and historical change frequency by target status. These lagged variables are observable at the forecast origin. Differences are descriptive composition evidence, not estimates of selection effects after conditioning on every confounder.

No target is filled, no missing return is guessed, and no inverse-probability adjustment is presented as a remedy for outcomes that cannot be observed. Observed-case accuracy cannot identify accuracy for absent services. The direction of selection bias remains unknown without those outcomes.

## One fixed additional benchmark

Use the last 12 same-key records actually published by each primary origin. Reconcile the full admissible history count, latest publication date and latest price with the original saved forecast case. Count only pairs in consecutive nominal months; exclude pairs spanning missing months. Let f be the fraction of eligible pairs whose price changes under the original tolerance. Define the nominal-horizon shrinkage factor q_h = 1 - (1-f)^h and:

`forecast = last_price * exp(q_h * log(original_damped_trend / last_price))`.

This blends the existing bounded damped-trend forecast with persistence in log-price space. A history with no usable pair falls back explicitly to persistence and has undefined f. At f=0 it equals persistence; at f=1 it equals damped trend. It stays within the original forecast bounds. No target, future record or fitted future-event model enters the rule.

The factor is a fixed heuristic, not a calibrated probability of repricing. In particular, the underlying damped trend uses elapsed time from the last publication to the target cutoff, whereas h is the nominal horizon from the forecast origin. No threshold, window or coefficient is selected after viewing this benchmark's accuracy. Report all six market/horizon comparisons on the same original targets, retaining the original five-model results separately. Lack of improvement would be a legitimate outcome.

## Verification and reporting

Behavioral tests must cover duplicate/mismatched timing joins, paired bootstrap indexing, missing calendar endpoints, undefined ratios, subgroup contribution identities, eligible-weight attrition, empty provider exclusions, history gaps and invariance to future prices. Validate aggregate outputs independently against saved cases, fingerprint inputs and code, and regenerate the supplement deterministically. A fresh independent implementation review follows initial verification.

V3 adds these findings and their limitations to the English paper, preserves the single-author voice, and retains the H200, service-identity and unavailable-predecessor-manuscript caveats. The supplement was initially delivered locally. Its publication to the existing repository was subsequently authorized together with the separate origin-deletion diagnostic. No arXiv submission is part of this update.

The fixed-block resampling design is consistent with the multivariate time-series resampling interface described in the official [R boot documentation](https://stat.ethz.ch/R-manual/R-devel/library/boot/html/tsboot.html); this project implements its own calendar/missingness and paired-statistic rules in Python.
