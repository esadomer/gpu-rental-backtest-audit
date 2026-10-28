# Source Register

Audit cutoff: October 28, 2026. Exact cached-download provenance is in `data/source_manifest.json`. Access to a public page does not establish unrestricted redistribution rights.

## Rental sources

| Source | Evidence and access | Use in this project |
|---|---|---|
| [Mittal, gpu-price-history](https://github.com/rahilmittal1/gpu-price-history/tree/ee8820dd90d7715d8bb57cee03fb0882706d76c5) | Public CSV and documentation; immutable revision captured locally | Principal derived input; quoted prices, not executed rentals |
| [SkyPilot catalog](https://github.com/skypilot-org/skypilot-catalog) | Public versioned catalog files | Two historical files downloaded; Lambda and GCP calculations independently checked |
| [dstack gpuhunt](https://github.com/dstackai/gpuhunt) | Public historical catalog archives in the dstack-gpu-pricing S3 bucket | Two explicitly identified ZIP files downloaded; RunPod and Verda sample calculations checked |
| [AWS historical version index](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json) | Public JSON | Effective-period metadata inspected; not treated as proof of earliest publication |
| [AWS July 3, 2025 price file](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20250703204906/us-east-1/index.csv) | First 4,096 bytes downloaded with an HTTP range request | Publication header verified; the full price file was not downloaded |
| [AWS June 5, 2025 announcement](https://aws.amazon.com/about-aws/whats-new/2025/06/pricing-usage-model-ec2-instances-nvidia-gpus/) | Public dated provider announcement, inspected on the web | Shows the distinction between announced, effective and archive publication dates |
| [GetDeploying weekly dataset](https://getdeploying.com/dataset/gpu-prices) | Public weekly aggregates, CC BY 4.0 stated | Alternative source lead; not counted as another independent observation of the same provider |

The pinned compilation states CC BY 4.0 for its own data work, while expressly retaining third-party source restrictions and uncertainties. See the captured `rental_license.md`. This project does not grant a new license over raw provider material, and that material is not republished.

## Physical tracker captures

Every row below was downloaded as public HTML. The embedded JSON contains tracker price records. Current product names and availability are metadata, not historical condition evidence. `pMsg` and unknown update categories are excluded from candidate quote counts pending semantic validation; the full raw inventory preserves them.

| Local source ID | Tracker | Underlying product | Decision |
|---|---|---|---|
| `glassit_h100_newegg` | [1695946793](https://glassit.co/price-history/newegg/nvidia-h100-80gb-hbm2e-pcie-express-gpu-graphics-card-new/1695946793) | [Newegg 1VK-0066-00022](https://www.newegg.com/p/1VK-0066-00022) | Exploratory PCIe quotes; current/title New evidence only |
| `glassit_h100_viperatech` | [1695947500](https://glassit.co/price-history.jsp?url=1695947500) | [Viperatech H100](https://www.viperatech.com/product/nvidia-h100-tensor-core-gpu/?currency=USD) | Short quote history; underlying product page failed access during audit |
| `glassit_h100_cdw` | [1695948660](https://glassit.co/price-history.jsp?url=1695948660) | [CDW 7367181](https://www.cdw.com/product/nvidia-h100-gpu-computing-processor-nvidia-h100-tensor-core-80-gb/7367181) | Sparse history; kit and specification ambiguity |
| `glassit_h100_amazon` | [1695947998](https://glassit.co/price-history.jsp?url=1695947998) | Exact product URL preserved in `physical_metadata.json` | Constant quote; historical seller and condition unverified |
| `glassit_a100_newegg` | [1691864652](https://glassit.co/price-history.jsp?url=1691864652) | [Newegg 900-21001-0000-000](https://www.newegg.com/nvidia-900-21001-0000-000/p/N82E16814132090) | 40GB PCIe quote history; historical seller and condition unverified |
| `glassit_a100_amazon` | [1691858914](https://glassit.co/price-history.jsp?url=1691858914) | [Amazon B0BGZJ27SL](https://www.amazon.com/NVIDIA-Tesla-A100-Ampere-Graphics/dp/B0BGZJ27SL) | Marketplace quotes; summary-count discrepancy |
| `glassit_a100_ebay` | [1697499059](https://glassit.co/price-history/ebay/nvidia-a100-40gb-hbm2-data-center-graphics-card/1697499059) | [eBay product 14046138204](https://www.ebay.com/p/14046138204) | Product-level quotes; not a stable identified seller listing |
| `glassit_a100_80_ebay` | [1691859184](https://glassit.co/price-history.jsp?url=1691859184) | [eBay listing 235092334717](https://www.ebay.com/itm/235092334717) | Short constant quote history; historical condition unverified |
| `glassit_h100_identity_drift` | [1627821634](https://glassit.co/price-history.jsp?url=1627821634) | Current title claims H100 | Reject entire series: history begins in 2021, before H100 existed |

All tracker observations are price offers, not executed sales. No historical seller/condition field was recovered. No redistribution permission beyond public access was established for the tracker data; raw captures remain local.

## Sources that do not establish the required physical panel

| Source | What was found | Why it does not pass |
|---|---|---|
| [Epoch hardware documentation](https://epoch.ai/data/machine-learning-hardware-documentation/records) | Release prices and technical specifications | A release price is not a time series of market sales |
| [CCIR hardware](https://ccir.io/hardware) | Used sold-listing aggregates, current asks, model-implied values and some fleet transactions | Individual sales records are not public; condition, units and modeling differ from the requested new bare-card panel |
| [Geizhals A100](https://geizhals.de/nvidia-a100-v209908.html) | Product variants and chart interface | Direct historical access returned 403; no machine-readable history verified |
| [Geizhals H100](https://geizhals.de/nvidia-h100-900-21010-0000-000-a3264418.html) | Current comparison-page lead | Historical data could not be verified through the attempted access |
| [GPU Economy H200](https://gpueconomy.com/gpu/h200) | Recent new-labeled retail offers, mainly Sep–Oct 2026 | Recent cross-section, mixed or unspecified forms and indirect product links; no long matched history |
| [ASA H200 NVL kit](https://www.asacomputers.com/nvidia-h200-141gb-nvh200nvltcgpu-gpu-card.html) | Current PCIe NVL kit quote | A current kit quote cannot stand in for a historical SXM bare-card price |
| [United-Compute tracker](https://github.com/United-Compute/gpu-price-tracker) | Examined target-GPU JSON files had empty `prices` objects | Repository description alone does not establish observations |

The physical-source search and primary product-identity checks were performed as a separate read-only research pass. Downloaded tracker arrays were then independently extracted by the local audit code. Some primary-page and negative-access checks are documented web observations rather than locally archived datasets; they do not contribute numeric empirical rows.
