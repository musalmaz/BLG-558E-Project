# Deneylerden çıkan sayılar ve kaynakları (yalnızca veri)

Tüm sayılar `docs/ilerleme_raporu.md` ve `results/` içindeki dosyalardan alındı. Makalede kullanmadan önce ilgili dosyadan tekrar kontrol et.

| Ne | Değer | Nerede |
|---|---|---|
| Doküman / chunk | 2030 (2000 Enron + 30 kanarya) / 7520 | ilerleme_raporu.md bölüm 2 |
| Konu sayısı | 20 (10 gizli belgeli, 10 belgesiz); konu başına 3 gizli belge | bölüm 2 |
| Ana matris | 800 çağrı = 20 konu × 2 tür × 5 varyant × 2 mod × 2 model | bölüm 5 |
| Doğrudan soru sızıntısı M1 / M2 | gemma3 16/20 ve 0/20; qwen2.5 13/20 ve 0/20 | bölüm 5 |
| gemma3, M1, metin | AUC 0,82 [0,75–0,91], p = 0,004 | bölüm 6, `results/decoder_results.csv` |
| gemma3, M1, davranış | AUC 0,48, p = 0,46 (anlamlı değil) | aynı |
| gemma3, M2, metin | AUC 0,45, p = 0,56 | aynı |
| qwen2.5, M1, metin / davranış | 0,61 (p 0,13) / 0,58 (p 0,18) | aynı |
| Maskeleme analizi (kelime maskesi) | 0,83 → 0,82 | bölüm 6.x |
| Üslup işaretleri (gemma3, M1) | "we/our" 0,050 vs 0,017; "I" 0,009 vs 0,032; "unfortunately" 0 vs 0,14 | bölüm 6.x |
| k taraması, gemma3 metin AUC | k=1: 0,71; k=2: 0,64; k=3: 0,82 | bölüm 7.2, `results/ratio_table.md` |
| Savunmalar (gemma3 metin AUC / fayda kaybı) | none 0,82 / 0; behavior_norm 0,82 / 0,04; decision_hiding 0,82 / 0; scoped_context 0,44 / 0,30; M2 0,45 / 0,04 | bölüm 8, `results/defense_table.md` |
| Maskeleme savunması (gemma3) | oracle AUC 0,84; rule 0,69; doğrudan sızıntı 0,50 → 0,00; çözüm oranı 0,92 / 0,90 / 0,92 (M2: 0,67) | bölüm 8.1, `results/mask_table.md` |
| Çok kullanıcılı ek çalışma, A'nın verisi B'ye sızma | X1: gemma3 %72, qwen2.5 %52; X3: %70, %56; X2 (izole): %2, %0 | bölüm 9, `results/xuser_leak.csv` |
| Mevcut şekiller | `results/figures/auc_m1_vs_m2.png`, `auc_vs_docs_per_topic.png`, `leaked_bits_m1_vs_m2.png`, `security_utility.png` | `results/figures/` |

Sınırlar (makalede dürüstçe belirtmelisin): 10+10 konu, 5 varyant, çoğu analizde tek tekrar; iki küçük yerel model; kanarya, mesaj ve "sır" tanımı tek yazarlı; çoklu test düzeltmesi yok; davranış kanalı için "bulunamadı", "yok" demek değil.
