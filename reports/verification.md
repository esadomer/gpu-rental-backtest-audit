# Verification and independent-review record

## Final publication preparation, October 29, 2026

The author authorized publishing the revised preprint and full supplemental reproducibility materials to the existing repository. This supersedes the earlier local-only checkpoint. No arXiv submission is included.

- **59 unit tests passed**, including six new origin-deletion boundary tests.
- **All 94 complete-origin deletions were independently reconstructed** from the original paired case files. An independent reviewer additionally checked target month/cutoff/publication equality, omitted and retained counts, full and retained losses, percentage-point changes and concentration summaries. All checks passed.
- **Fresh independent implementation review: PASS.** No material correctness or manuscript defect was found. The reviewer independently reran all 59 tests, the origin verifier and the supplemental verifier, and checked the publication wording. The review did not certify the later package, remote-publishing or CI steps.
- **Final manuscript:** 13 pages compiled with Tectonic 0.17.0 and visually checked. Version labels were removed while preserving the date and explicit post-result disclosures. The benchmark caption explains that percentage comparisons use unrounded scores. No overfull boxes or unresolved references remain; the existing two underfull bibliography and environment fontconfig warnings do not affect the inspected rendering.
- **Final clean-directory reproduction passed:** all 26 numerical CSVs reproduced byte for byte after rerunning the original experiment, supplemental diagnostics and origin deletions in a fresh output directory using registered local archives. All three independent output verifiers passed. Network retrieval was not repeated for this final check; the earlier public-download reproduction remains recorded below. See `reports/publication_reproducibility_checks.json`.
- **Scientific interpretation:** all individual-origin deletions preserve a positive timing reduction, but July 2025 supplies 45.5% of the signed one-month on-demand loss difference. The paper reports 28.9–51.1% single-deletion estimates without treating them as confidence bounds or evidence against joint concentration.

The original empirical protocol, original code and all prior numerical result CSVs remain unchanged. The new influence diagnostic has a separate post-result plan and fingerprint; it does not refit or select a forecasting model. Earlier verification records follow.

## Earlier supplemental checkpoint: local revision, October 29, 2026

At this earlier checkpoint the supplement remained local at the author's request; no upload or remote workflow was performed. A subsequent explicit instruction authorized the revised publication documented separately below. The earlier records below describe the original experiment and its prior public release.

- **53 unit tests passed**, including 19 supplemental boundary tests for paired matching, calendar endpoints/gaps, zero-baseline bootstrap draws, original-weight conditional decomposition, eligible-weight attrition, future-record exclusion, frequency-history reconciliation and permissible reproduction-metadata changes.
- **Independent original-output verification passed again:** 122,938 primary/sensitivity eligible cases, 93,035 observed targets and 170 summary rows. Original research scripts, protocols, source manifests and numerical CSVs are unchanged from V2.
- **Independent V3 verification passed:** every one of 22,868 frequency forecasts was reconstructed from the extracted source history; 108 conditional-loss rows, 90 timing slices, 24 paired-bootstrap cells, 429 attrition rows and 2,574 feature-summary rows were checked. The verifier uses separate explicit weighting loops and vectorized bootstrap indexes rather than importing the implementation.
- **Clean-directory offline reproduction passed:** copied only the registered local archives and required configuration/source scripts into a new output directory, reran the complete original experiment and supplement, then ran both independent verifiers. All **24 numerical CSVs** (16 original plus eight supplemental) match byte for byte. This repeated the complete computation, not network retrieval; the original clean public-download check is recorded below. See `reports/v3_reproducibility_checks.json`.
- **V3 PDF:** 13 pages compiled with Tectonic 0.17.0 and all final pages visually checked. The corrected timing figure has no clipped annotation, tables fit, references resolve, repository links are clickable, and no authorial we/our remains. Two nonfatal underfull bibliography warnings and the existing fontconfig environment warning remain; no overfull boxes were reported.
- **Independent plan review completed** before supplemental evaluation. It required horizon-aware primary blocks, full protocol-calendar endpoints and explicit undefined-ratio handling; all were adopted. The supplement was specified after V2 results were known and is explicitly exploratory.
- **Fresh independent implementation review completed** after implementation and initial verification. No unresolved material correctness defect was found. Two reporting errors were fixed: the benchmark excess-error range is 7.0-30.1%, and absent/on-time is labeled an absent-key rate. The reviewer reran all 53 tests and the V3 verifier and confirmed that original scientific artifacts were unchanged. The reviewer did not perform the separate clean-directory run or PDF visual inspection; those were performed in the primary workflow.
- **Reproduction-boundary correction:** a fresh original run legitimately changes runtime/timestamp metadata and lists the added scripts. The V3 loader authenticates an exact preserved original-run reference against the frozen hash and permits only those operational differences. Scientific fields, original code and empirical input bytes remain pinned. Tests reject altered scientific counts, missing/changed original code and unexpected fields. The correction changes no numerical output.

The same-data block intervals are exploratory stability diagnostics, not guaranteed population confidence coverage. Changed-target strata are defined after outcomes and are not a deployable selection rule. Missing-outcome performance and novelty relative to the unavailable predecessor manuscript remain unidentified.

## Original experiment and V2 record


The empirical implementation and English working-paper draft passed the checks below. A later author-authorized editorial update removes authorial plurals, foregrounds the paired 42.0% timing result, adds the public repository link and records a deeper prior-work comparison. The numerical protocol, code and result CSVs are unchanged. No arXiv submission has occurred.

## Executed checks

- **34 unit tests passed.** Fixtures cover date availability, missing targets, exact numeric identity, duplicate/conflicting records, member repetition, nested loss/rate weights, training-label maturity, conditional provider holdout, future-label invariance, bootstrap calendar gaps and registered-download restoration. Synthetic values are confined to these tests.
- **Independent output validation passed** for 122,938 eligible cases across primary and sensitivity specifications, 93,035 observed targets and 170 summary rows. These totals are not independent samples. Every retained target was rejoined to its extracted source price; headline losses were recomputed using explicit nested loops.
- **Full offline regeneration:** all 16 result/research CSVs reproduced byte for byte.
- **Clean-directory end-to-end reproduction:** without copying any raw cache, restored three pinned source files and all 37 original catalog archives, verified their saved hashes and publication proxies, reran the entire study, and passed result validation. All 16 generated CSVs and both input manifests match the original workspace byte for byte. The final run manifest comes from this actual clean run. See `reports/reproducibility_checks.json`.
- **PDF:** nine pages compiled with the verified official Tectonic 0.17.0 binary; all nine final pages were rendered and visually inspected. No clipped/overlapping content, missing references or overfull boxes remain. The compiler reports two non-fatal underfull bibliography boxes and an environment fontconfig warning; the document's inspected font descriptors contain embedded fonts and the rendered text/figures are legible.

The packaged LaTeX source was also unpacked into a clean directory and compiled successfully: nine pages with exactly the same extracted text as the delivered PDF and no overfull boxes.

## Review findings and disposition

A separate plan review required explicit handling of repeated provider files, exact decimal identity normalization, nested weights and calendar-preserving uncertainty. These changes preceded forecast evaluation.

The first implementation review identified two material issues: duplicated DataCrunch/Verda provider records and raw-row diagnostic proportions presented beside provider-balanced losses. Both were corrected. The alias correction is a disclosed amendment after the initial run; initial results and the original lock form are preserved. Final outputs contain both balanced and explicitly labeled raw diagnostic proportions.

A fresh final independent read-only review identified a fresh-package restoration defect: manifest entries were incorrectly assumed to have local raw files. Both fetchers now restore missing files only if the registered hashes match, preserve original provenance, and reject corrupt caches. A source-selection option separates immutable rental inputs from unrelated live physical pages. Six targeted tests and the actual clean-directory run verified the repair.

The final independent verdict is **PASS: no remaining significant implementation or manuscript defect found**. The reviewer independently checked all 20,377 retained source-record payloads and price normalization, all 810 duplicate alias records, all balanced diagnostic rates, the primary and sensitivity claims, and 2,328 ridge predictions from six fits using a separate augmented least-squares implementation. The reviewer also reran all 34 tests and inspected the final clean-run artifacts. The reviewer did not personally perform the network downloads; the primary workflow did.

## What was not established

- Historical public access rights or first market knowledge are not proved by S3 Last-Modified metadata.
- The data do not certify provider freshness, execution access, capacity, counterparty terms or transaction prices.
- No sufficient historical new-hardware panel was established, so the original purchase-price predictor hypothesis remains untested.
- The review is not journal peer review, an exhaustive novelty certification, or a promise of arXiv acceptance/category assignment.
- arXiv server-side compilation, author account/endorsement, final author approval, disclosure and public-release license decisions remain outstanding.
- The app's built-in LaTeX preview compiler encountered a local access error; the delivered PDF was successfully built and checked with the separate verified local compiler.

The original empirical verification took place before Git publication, using file contents, registered hashes and regenerated artifacts. The author subsequently authorized a new public repository, https://github.com/esadomer/gpu-rental-backtest-audit. The release uses an explicit allowlist, omits raw and personal material, and preserves exact file bytes for locked fingerprints.

## Editorial and public-repository update

The single-author revision contains no authorial we/our in the extracted PDF. It foregrounds the matched-case 42.0% log-error reduction, explicitly retains the provider-balanced 90.7% unchanged-target rate and four-case H200 limit, and links directly to the public repository on the opening page and in the reproduction appendix. All nine revised pages were rendered and visually checked; no overfull boxes or unresolved references were reported.

A bounded independent prior-work audit inspected Mittal's current/pinned revision and all 44 public Python scripts. Its wording review corrected an accuracy-versus-error phrasing and one evidence URL. The inspected predecessor already covers timing, identity, staleness, rigidity and some publication-aware analysis. The revised claim is the controlled future-rental forecast experiment and matched-case diagnostic; the unavailable manuscript remains a novelty limit.

All 34 tests and independent result validation passed again. Research code, protocol fingerprints and numerical CSV outputs were unchanged. The public GitHub workflow runs these behavioral tests without downloading raw data. Registered protocol/source bytes are preserved in Git to avoid newline normalization invalidating hashes.
