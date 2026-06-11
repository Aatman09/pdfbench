# Document Extraction — Analysis Report

_Generated: 2026-06-08 09:17:08_

## 1. Overview

- **Documents:** 12
- **Tools:** 5 (Docling, Granite Docling, MinerU, OpenDataLoader, PaddleOCR VL 1.6)
- **Total tool runs:** 38
- **Overall success rate:** 100.0%  (38/38)

## 2. Coverage Matrix (document × tool)

✓ = success · ✗ = error/failed · — = not run

| Document | Docling | Granite Docling | MinerU | OpenDataLoader | PaddleOCR VL 1.6 |
|---|---|---|---|---|---|
| 080B042_BMR-17 1 | — | ✓ | ✓ | — | ✓ |
| 22201549-Ptd.Leaf.Potass.Phos-CS | — | — | ✓ | ✓ | ✓ |
| Leaflet Brimonidine TartrateTimolol Maleate Ophthalmic Solution - Caplin | — | — | ✓ | ✓ | ✓ |
| Leaflet Nicard inj -CS. 1 | — | — | ✓ | ✓ | ✓ |
| Leaflet- Ketorolac Trome Inj USP | — | — | ✓ | ✓ | ✓ |
| Shakti Agro Chem & Fertilizers | ✓ | ✓ | ✓ | — | ✓ |
| Technical Proposal Part 1 | — | ✓ | ✓ | — | ✓ |
| Transporter Page 11 | — | ✓ | ✓ | — | ✓ |
| Transporter Page 2 | — | ✓ | ✓ | — | ✓ |
| Transporter Page 3 | — | ✓ | ✓ | — | ✓ |
| drylab | ✓ | ✓ | ✓ | — | ✓ |
| invoice_DHL - LGWR009675986 (1) 1 | — | ✓ | ✓ | — | ✓ |

## 3. Output Coverage per Tool

| Tool | Docs | Success | Direct MD | JSON | MD-from-JSON | Avg runtime (s) |
|------|------|---------|-----------|------|--------------|-----------------|
| Docling | 2 | 2/2 | 1 | 2 | 0 | 31.3 |
| Granite Docling | 8 | 8/8 | 7 | 8 | 0 | 467.2 |
| MinerU | 12 | 12/12 | 12 | 12 | 0 | 40.1 |
| OpenDataLoader | 4 | 4/4 | 4 | 4 | 0 | 1.9 |
| PaddleOCR VL 1.6 | 12 | 12/12 | 12 | 12 | 0 | 495.0 |

## 4. Success Rate per Tool

**Success rate** = the percentage of documents a tool processed *without error*. For each document the tool either finishes and returns output (success) or raises an error / times out (failure). The rate is `successful documents ÷ documents attempted × 100`. It measures **reliability** (did the tool run end-to-end), not the *quality* of the extracted text. A bar reaching the far right means 100% — the tool completed on every document it was given.

```
Docling            ████████████████████████████████████████ 100%  (2/2)
Granite Docling    ████████████████████████████████████████ 100%  (8/8)
MinerU             ████████████████████████████████████████ 100%  (12/12)
OpenDataLoader     ████████████████████████████████████████ 100%  (4/4)
PaddleOCR VL 1.6   ████████████████████████████████████████ 100%  (12/12)
```

## 5. Average Runtime per Tool

**Average runtime** = mean wall-clock seconds the tool took per document (model load + inference). Lower is faster. Bars are scaled relative to the slowest tool.

```
Docling            ███····································· 31.3s
Granite Docling    ██████████████████████████████████████·· 467.2s
MinerU             ███····································· 40.1s
OpenDataLoader     ········································ 1.9s
PaddleOCR VL 1.6   ████████████████████████████████████████ 495.0s
```

## 6. Runtime per Document (seconds)

| Document | Docling | Granite Docling | MinerU | OpenDataLoader | PaddleOCR VL 1.6 |
|---|---|---|---|---|---|
| 080B042_BMR-17 1 | — | 157.2 | 37.0 | — | 167.9 |
| 22201549-Ptd.Leaf.Potass.Phos-CS | — | — | 41.4 | 1.6 | 469.5 |
| Leaflet Brimonidine TartrateTimolol Maleate Ophthalmic Solution - Caplin | — | — | 38.5 | 1.5 | 479.9 |
| Leaflet Nicard inj -CS. 1 | — | — | 40.8 | 2.1 | 1033.6 |
| Leaflet- Ketorolac Trome Inj USP | — | — | 50.4 | 2.3 | 856.9 |
| Shakti Agro Chem & Fertilizers | 56.9 | 895.0 | 47.1 | — | 643.8 |
| Technical Proposal Part 1 | — | 1595.7 | 58.6 | — | 1060.8 |
| Transporter Page 11 | — | 218.3 | 32.4 | — | 37.6 |
| Transporter Page 2 | — | 209.8 | 29.8 | — | 27.2 |
| Transporter Page 3 | — | 221.2 | 39.0 | — | 607.5 |
| drylab | 5.6 | 201.0 | 28.7 | — | 134.3 |
| invoice_DHL - LGWR009675986 (1) 1 | — | 239.8 | 37.4 | — | 421.1 |

## 7. Failures

_No failures recorded._
