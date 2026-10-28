# Verification and independent-review record

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
