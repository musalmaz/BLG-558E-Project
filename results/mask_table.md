# Maskeleme savunması (M1_weak; none = savunmasız, m2 = güçlü ACL, scoped = public-only)

| Model | Koşul | Grup | AUC [%95 GA] | p | işaretçi sızıntısı (probe) | doğrudan soru sızıntısı | Çözüm | recall util23 | recall onaylı-cümle |
|---|---|---|---|---|---|---|---|---|---|
| gemma3 | none | text | 0.82 [0.75–0.91] | 0.004 | 0.06 | 0.50 | 0.92 | 0.91 | 0.33 |
| gemma3 | none | behavior+text | 0.78 [0.70–0.86] | 0.006 | 0.06 | 0.50 | 0.92 | 0.91 | 0.33 |
| qwen2.5 | none | text | 0.61 [0.48–0.72] | 0.126 | 0.02 | 0.35 | 1.00 | 0.87 | 0.22 |
| qwen2.5 | none | behavior+text | 0.61 [0.45–0.72] | 0.112 | 0.02 | 0.35 | 1.00 | 0.87 | 0.22 |
| gemma3 | m2 | text | 0.45 [0.34–0.56] | 0.563 | 0.00 | 0.00 | 0.67 | 0.87 | 0.00 |
| gemma3 | m2 | behavior+text | 0.48 [0.35–0.60] | 0.485 | 0.00 | 0.00 | 0.67 | 0.87 | 0.00 |
| qwen2.5 | m2 | text | 0.42 [0.32–0.53] | 0.693 | 0.00 | 0.00 | 1.00 | 0.91 | 0.00 |
| qwen2.5 | m2 | behavior+text | 0.37 [0.28–0.47] | 0.848 | 0.00 | 0.00 | 1.00 | 0.91 | 0.00 |
| gemma3 | scoped | text | 0.44 [0.27–0.58] | 0.629 | 0.00 | – | 0.93 | 0.61 | 0.00 |
| gemma3 | scoped | behavior+text | 0.49 [0.34–0.62] | 0.445 | 0.00 | – | 0.93 | 0.61 | 0.00 |
| qwen2.5 | scoped | text | 0.52 [0.39–0.66] | 0.305 | 0.00 | – | 0.99 | 0.52 | 0.00 |
| qwen2.5 | scoped | behavior+text | 0.42 [0.26–0.57] | 0.689 | 0.00 | – | 0.99 | 0.52 | 0.00 |
| gemma3 | mask_oracle | text | 0.84 [0.77–0.92] | 0.002 | 0.00 | 0.00 | 0.90 | 0.91 | 0.33 |
| gemma3 | mask_oracle | behavior+text | 0.80 [0.70–0.89] | 0.006 | 0.00 | 0.00 | 0.90 | 0.91 | 0.33 |
| qwen2.5 | mask_oracle | text | 0.60 [0.44–0.74] | 0.122 | 0.00 | 0.00 | 1.00 | 0.87 | 0.28 |
| qwen2.5 | mask_oracle | behavior+text | 0.75 [0.64–0.84] | 0.014 | 0.00 | 0.00 | 1.00 | 0.87 | 0.28 |
| gemma3 | mask_rule | text | 0.69 [0.55–0.83] | 0.016 | 0.00 | 0.00 | 0.92 | 0.87 | 0.39 |
| gemma3 | mask_rule | behavior+text | 0.68 [0.55–0.81] | 0.036 | 0.00 | 0.00 | 0.92 | 0.87 | 0.39 |
| qwen2.5 | mask_rule | text | 0.59 [0.44–0.70] | 0.144 | 0.00 | 0.00 | 1.00 | 0.87 | 0.33 |
| qwen2.5 | mask_rule | behavior+text | 0.54 [0.36–0.66] | 0.261 | 0.00 | 0.00 | 1.00 | 0.87 | 0.33 |
