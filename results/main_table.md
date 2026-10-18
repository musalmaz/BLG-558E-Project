# Ana tablo (LOTO decoder, konu düzeyi permütasyon p)

| Model | ACL | Grup | AUC [%95 GA] | TPR@1%FPR | Mesaj | Sızan bit/mesaj | p (konu perm.) | Kanal açık |
|---|---|---|---|---|---|---|---|---|
| gemma3 | M1_weak | behavior_nolat | 0.44 [0.30–0.57] | 0.00 | >5 | 0.000 | 0.543 | hayır |
| *gemma3* | *M1_weak* | *behavior_nolat* | *row shuffle: AUC 0.47* | | | | | |
| *gemma3* | *M1_weak* | *behavior_nolat* | *topic perm null: AUC 0.45* | | | | | |
| *gemma3* | *M1_weak* | *behavior_nolat* | *placebo rows: AUC 0.43* | | | | | |
| gemma3 | M1_weak | behavior | 0.48 [0.33–0.63] | 0.00 | >5 | 0.000 | 0.461 | hayır |
| *gemma3* | *M1_weak* | *behavior* | *row shuffle: AUC 0.47* | | | | | |
| *gemma3* | *M1_weak* | *behavior* | *topic perm null: AUC 0.46* | | | | | |
| *gemma3* | *M1_weak* | *behavior* | *placebo rows: AUC 0.42* | | | | | |
| gemma3 | M1_weak | text | 0.82 [0.75–0.91] | 0.12 | 2 | 0.116 | 0.004 | evet |
| *gemma3* | *M1_weak* | *text* | *row shuffle: AUC 0.47* | | | | | |
| *gemma3* | *M1_weak* | *text* | *topic perm null: AUC 0.47* | | | | | |
| *gemma3* | *M1_weak* | *text* | *placebo rows: AUC 0.35* | | | | | |
| gemma3 | M1_weak | behavior+text | 0.78 [0.70–0.86] | 0.00 | 3 | 0.000 | 0.006 | evet |
| *gemma3* | *M1_weak* | *behavior+text* | *row shuffle: AUC 0.49* | | | | | |
| *gemma3* | *M1_weak* | *behavior+text* | *topic perm null: AUC 0.47* | | | | | |
| *gemma3* | *M1_weak* | *behavior+text* | *placebo rows: AUC 0.40* | | | | | |
| gemma3 | M2_strong | behavior_nolat | 0.47 [0.32–0.62] | 0.00 | >5 | 0.000 | 0.489 | hayır |
| *gemma3* | *M2_strong* | *behavior_nolat* | *row shuffle: AUC 0.48* | | | | | |
| *gemma3* | *M2_strong* | *behavior_nolat* | *topic perm null: AUC 0.46* | | | | | |
| *gemma3* | *M2_strong* | *behavior_nolat* | *placebo rows: AUC 0.41* | | | | | |
| gemma3 | M2_strong | behavior | 0.46 [0.31–0.62] | 0.00 | >5 | 0.000 | 0.547 | hayır |
| *gemma3* | *M2_strong* | *behavior* | *row shuffle: AUC 0.49* | | | | | |
| *gemma3* | *M2_strong* | *behavior* | *topic perm null: AUC 0.47* | | | | | |
| *gemma3* | *M2_strong* | *behavior* | *placebo rows: AUC 0.42* | | | | | |
| gemma3 | M2_strong | text | 0.45 [0.34–0.56] | 0.00 | >5 | 0.000 | 0.563 | hayır |
| *gemma3* | *M2_strong* | *text* | *row shuffle: AUC 0.50* | | | | | |
| *gemma3* | *M2_strong* | *text* | *topic perm null: AUC 0.47* | | | | | |
| *gemma3* | *M2_strong* | *text* | *placebo rows: AUC 0.43* | | | | | |
| gemma3 | M2_strong | behavior+text | 0.48 [0.35–0.60] | 0.00 | >5 | 0.000 | 0.485 | hayır |
| *gemma3* | *M2_strong* | *behavior+text* | *row shuffle: AUC 0.50* | | | | | |
| *gemma3* | *M2_strong* | *behavior+text* | *topic perm null: AUC 0.47* | | | | | |
| *gemma3* | *M2_strong* | *behavior+text* | *placebo rows: AUC 0.42* | | | | | |
| qwen2.5 | M1_weak | behavior_nolat | 0.57 [0.38–0.76] | 0.20 | >5 | 0.054 | 0.190 | hayır |
| *qwen2.5* | *M1_weak* | *behavior_nolat* | *row shuffle: AUC 0.48* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior_nolat* | *topic perm null: AUC 0.45* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior_nolat* | *placebo rows: AUC 0.55* | | | | | |
| qwen2.5 | M1_weak | behavior | 0.58 [0.41–0.76] | 0.20 | >5 | 0.034 | 0.182 | hayır |
| *qwen2.5* | *M1_weak* | *behavior* | *row shuffle: AUC 0.49* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior* | *topic perm null: AUC 0.46* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior* | *placebo rows: AUC 0.53* | | | | | |
| qwen2.5 | M1_weak | text | 0.61 [0.48–0.72] | 0.00 | >5 | 0.000 | 0.126 | hayır |
| *qwen2.5* | *M1_weak* | *text* | *row shuffle: AUC 0.51* | | | | | |
| *qwen2.5* | *M1_weak* | *text* | *topic perm null: AUC 0.47* | | | | | |
| *qwen2.5* | *M1_weak* | *text* | *placebo rows: AUC 0.33* | | | | | |
| qwen2.5 | M1_weak | behavior+text | 0.61 [0.45–0.72] | 0.12 | >5 | 0.000 | 0.112 | hayır |
| *qwen2.5* | *M1_weak* | *behavior+text* | *row shuffle: AUC 0.51* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior+text* | *topic perm null: AUC 0.48* | | | | | |
| *qwen2.5* | *M1_weak* | *behavior+text* | *placebo rows: AUC 0.41* | | | | | |
| qwen2.5 | M2_strong | behavior_nolat | 0.43 [0.29–0.60] | 0.00 | >5 | 0.000 | 0.547 | hayır |
| *qwen2.5* | *M2_strong* | *behavior_nolat* | *row shuffle: AUC 0.46* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior_nolat* | *topic perm null: AUC 0.44* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior_nolat* | *placebo rows: AUC 0.42* | | | | | |
| qwen2.5 | M2_strong | behavior | 0.45 [0.33–0.63] | 0.02 | >5 | 0.000 | 0.591 | hayır |
| *qwen2.5* | *M2_strong* | *behavior* | *row shuffle: AUC 0.48* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior* | *topic perm null: AUC 0.46* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior* | *placebo rows: AUC 0.43* | | | | | |
| qwen2.5 | M2_strong | text | 0.42 [0.32–0.53] | 0.00 | >5 | 0.000 | 0.693 | hayır |
| *qwen2.5* | *M2_strong* | *text* | *row shuffle: AUC 0.50* | | | | | |
| *qwen2.5* | *M2_strong* | *text* | *topic perm null: AUC 0.47* | | | | | |
| *qwen2.5* | *M2_strong* | *text* | *placebo rows: AUC 0.55* | | | | | |
| qwen2.5 | M2_strong | behavior+text | 0.37 [0.28–0.47] | 0.00 | >5 | 0.000 | 0.848 | hayır |
| *qwen2.5* | *M2_strong* | *behavior+text* | *row shuffle: AUC 0.50* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior+text* | *topic perm null: AUC 0.48* | | | | | |
| *qwen2.5* | *M2_strong* | *behavior+text* | *placebo rows: AUC 0.45* | | | | | |

# M1 vs M2

| Model | Grup | AUC M1 | AUC M2 | ΔAUC | bit M1 | bit M2 | Δbit | p M1 | p M2 |
|---|---|---|---|---|---|---|---|---|---|
| gemma3 | behavior_nolat | 0.44 | 0.47 | -0.02 | 0.000 | 0.000 | 0.000 | 0.543 | 0.489 |
| gemma3 | behavior | 0.48 | 0.46 | 0.02 | 0.000 | 0.000 | 0.000 | 0.461 | 0.547 |
| gemma3 | text | 0.82 | 0.45 | 0.38 | 0.116 | 0.000 | 0.116 | 0.004 | 0.563 |
| gemma3 | behavior+text | 0.78 | 0.48 | 0.30 | 0.000 | 0.000 | 0.000 | 0.006 | 0.485 |
| qwen2.5 | behavior_nolat | 0.57 | 0.43 | 0.14 | 0.054 | 0.000 | 0.054 | 0.190 | 0.547 |
| qwen2.5 | behavior | 0.58 | 0.45 | 0.13 | 0.034 | 0.000 | 0.034 | 0.182 | 0.591 |
| qwen2.5 | text | 0.61 | 0.42 | 0.19 | 0.000 | 0.000 | 0.000 | 0.126 | 0.693 |
| qwen2.5 | behavior+text | 0.61 | 0.37 | 0.24 | 0.000 | 0.000 | 0.000 | 0.112 | 0.848 |
