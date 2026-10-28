# Data provenance and access boundaries

The empirical project reads real public records. Synthetic fixtures occur only in `tests/`; no empirical script imports them.

## Archive selection

Rahil Mittal, `gpu-price-history`, revision `ee8820dd90d7715d8bb57cee03fb0882706d76c5`, supplies the monthly archive identifiers. Its generated dataset is credited under its stated CC BY 4.0 terms. The repository's own source-license inventory explicitly distinguishes generated data from original third-party material. The original gpuhunt ZIPs, not the cleaned panel's price values, supply this study's forecasts.

Source: https://github.com/rahilmittal1/gpu-price-history

Infrastructure: https://github.com/dstackai/gpuhunt

The 37 explicit ZIP URLs, Last-Modified timestamps, retrieval times and SHA-256 hashes are in `data/catalog_manifest.json`. Every extracted retained row contains the archive version/hash, member name, CSV line and raw source record. `data/research/provider_members.csv` contains both byte-level and semantic fingerprints. These counts do not make a repeated file an independent market observation.

## Provider alias correction

DataCrunch's November 5, 2025 announcement identifies its change of name to Verda and continuity of the legal entity. All nine overlapping sampled provider members have identical normalized core tables; all 810 target Verda records duplicate DataCrunch's configuration and price. The longer DataCrunch history is retained. The duplicate alias remains in the raw evidence and member inventory but is excluded from modeling. See `config/protocol_amendment_01.json` and the initial-run archive for the correction's timing.

Official source: https://verda.com/blog/datacrunch-is-changing-its-name-to-verda

## Distribution

The local research folder preserves raw and row-level evidence for verification. The manuscript-source and reproducibility ZIPs omit raw catalogs and extracted raw source records. They include public URLs, checksums, scripts, protocols and aggregate research results. No blanket downstream license is claimed over third-party provider prices or archives. Public accessibility and software repository licensing should not be confused with an explicit license for the underlying quote feeds.

The author authorized the public research repository at https://github.com/esadomer/gpu-rental-backtest-audit. It contains the manuscript, code, registered-source metadata and aggregate results, not raw third-party catalogs or extracted raw records. No project-wide reuse license has been selected; public accessibility does not grant additional rights. No arXiv submission has been made.
