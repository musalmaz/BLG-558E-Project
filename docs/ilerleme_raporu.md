# İlerleme Raporu — Dış AI ajanlarında davranışsal yan kanal sızıntısı

Son güncelleme: 2026-10-24 · Tamamlanan: Faz 0–6, maskeleme savunması, çok kullanıcılı ek çalışma, rapor, 8 slaytlık sunum, makale taslağı · Sıradaki: makalenin gözden geçirilmesi, künyelerin tamamlanması, teslim (06.12.2026)

## 1. Faz özeti

| Faz | İçerik | Durum | Commit |
|---|---|---|---|
| 0 | İskelet, ortam, config | Tamam | `5108fb1` |
| 1 | Veri katmanı: Enron yükleme, ACL etiketleme, kanarya, Chroma indeksi | Tamam | `c56c8a0` |
| 2 | Ajan boru hattı: retrieval (M1/M2) + LLM + yapılandırılmış karar + log | Tamam | `05a3747` |
| 3 | Probe/control seti, runner, baseline check, tam matris (repeats=1) | Tamam | `1473694` + sonuçlar |
| 4 | Özellikler, decoder, randomized control, istatistik testleri; 20 konuya ölçekleme | Tamam | `b84f958` |
| 5 | Ana tablo, M1 vs M2, gizli belge sayısı taraması (k=1,2,3), figürler | Tamam | `6dad717`, `f6a256c` |
| 6 | Savunmalar (behavior_norm, scoped_context, decision_hiding), güvenlik-fayda eğrisi | Tamam | `968559c` |
| 6.1 | Maskeleme savunması (oracle ve rule), onaylı-cümle fayda seti (bölüm 8.1) | Tamam | `43ef76b`, `9757781` |
| Ek | Çok kullanıcılı ek çalışma: A'nın verisi B'ye sızıyor mu (bölüm 9) | Tamam | `e2e2fe4`, `cc4e118` |
| Çıktı | Proje raporu (HTML), 8 slaytlık sunum (.pptx), IEEE makale taslağı (`docs/makale/`) | Tamam, gözden geçirilecek | `9a3c201` … `e4011e2` |

## 2. Veri (Faz 1, 20 konuya genişletildi)
- 2030 doküman (2000 Enron + 30 elle yazılmış kanarya), 7520 chunk. ACL: internal 1596, confidential 271, public 163.
- **20 kanarya konu:** 10 gerçek (c00–c03, c08–c13; her biri 3 confidential doküman; predicate=1) ve 10 uydurma (c04–c07, c14–c19; dokümansız; predicate=0). İlk pilot 8 konuydu (4+4); güç artırmak için 12 konu eklendi (18 doküman, 120 probe/control mesajı, 12 doğrudan soru elle yazıldı). Yeni anahtar kelimeler Enron verisinde arandı; bir çakışma (e-posta alan adı) bulunup konu adı değiştirildi.

## 3. Ajan (Faz 2)
- `retrieval.py`: M1_weak her şeyi getirir (confidential dahil, sadece prompt "yazma" der); M2_strong confidential'ı retrieval'da filtreler.
- `agent.py`: litellm + JSON şema; çıktı `escalated, refusal_type, routing_target (sabit küme + other), answer_text`; bozuk çıktıda 2 retry, sonra `parse_error=True`.
- Modeller (API anahtarı yok, yerel Ollama): `gemma3:latest` ve `qwen2.5:7b`. gemma4:26b çok yavaş olduğu için kullanılmadı.
- Duman testi: M2'de `confidential` hiç gelmedi, M1'de geldi; parse hatası 0. gemma3 M1'de Project Falcon içeriğini müşteriye yazdı.

## 4. Probe/control ve baseline (Faz 3)
- 80 elle yazılmış mesaj: 8 konu × 5 varyant × {probe, control}. Control aynı yapıda, konuyla ilgisiz. Doğrulayıcı: konu anahtar kelimesi, control'de kanarya kelimesi yok, uzunluk farkı ≤ %25, talimat deseni yok.
- Enjeksiyon yok; tüm mesajlar doğal müşteri soruları.
- `message_id = konu|tür|vN|rN|mod|model` → Faz 4 etiketleri buradan çıkarır.
- Duman koşusu (gemma3, c00+c04, 16 çağrı): 0 parse hatası, her (konu, tür, mod) hücresinde 2 satır, ort. gecikme ~6,8 sn.

### Baseline check (doğrudan sorular, 8 soru × mod × model)

| Model | M1_weak | M2_strong |
|---|---|---|
| gemma3 | 8/8 sızıntı | 0/8 sızıntı |
| qwen2.5 | 5/8 sızıntı | 0/8 sızıntı |

- M2'de sızıntı yok: ACL varsayımı geçerli.
- M1'deki sızıntı beklenen zayıf-ACL açığı; yan kanala gerek kalmadan doğrudan sızıyor. `results/baseline_check.json` içinde ayrıca raporlanır.
- Not: qwen2.5, M2'de 4 gerçek reddi `refusal_type=none` diye etiketledi (sızıntı değil, etiket gürültüsü). Faz 4'te `refusal_type` özelliği yorumlanırken dikkate alınmalı.

## 5. Tam matris koşusu — 20 konu (repeats=1)
- 800/800 çağrı (20 konu × 2 tür × 5 varyant × 2 mod × 2 model), **0 parse hatası**, her (model, mod, tür) hücresinde 100 satır. 528 bin prompt + 88 bin completion token. Medyan gecikme: gemma3 5,6 sn, qwen2.5 10,3 sn (en uzun 38 sn).
- Ham log: `results/runs/probe_matrix_20topics_repeats1.jsonl`. İlk 8 konuluk pilot koşu da `results/runs/probe_matrix_repeats1.jsonl` ve `results/runs/decoder_results_8topics.csv` olarak duruyor. Pilotun eski indeksle yapıldığı, 20 konuluk koşunun ise 8 konuyu da yeni indeksle yeniden koşturduğu unutulmamalı.
- **Doğrudan sorular (baseline, 20 soru):** M2_strong'da sızıntı **0/40** (gemma3 19/20, qwen2.5 9/20 açık ret; qwen2.5'in kalanı ret etiketsiz ama gizli bilgi içermeyen cevaplar). M1_weak'te sızıntı: gemma3 **16/20**, qwen2.5 **13/20**. ACL varsayımı M2'de geçerli; M1'in açığı bilinen zayıf-ACL açığı olarak ayrıca raporlandı.
- **Davranış neredeyse sabit:** `escalated` her satırda 0. `refusal_type≠none` oranı (probe, present/absent): gemma3 M1 %4/%20, gemma3 M2 %42/%60, qwen2.5 M1 %20/%0, qwen2.5 M2 %0/%2.
- **Operasyonel notlar (latency güvenilirliği):** Koşu sırasında (a) dizüstü pil modunda ve `power-saver` profilindeydi (hız 4× düştü), (b) Ollama CUDA'yı başlatamadı (CPU'ya düştü), (c) Ollama'nın llama-server süreci ~9 GB anonim bellek biriktirip sistemi belleğe sıkıştırdı. Etkilenen satırlar atıldı; koşu 40 çağrılık parçalara bölündü, her parça arasında modeller boşaltıldı ve loglanmayan bir ısınma çağrısı eklendi; işler modele göre gruplandı. Buna rağmen latency'de seyrek aykırı değerler var; latency zayıf kanıt sayılmalı.

## 6. Faz 4 — Özellikler ve decoder (20 konu)
Kod: `src/features/{dataset,behavioral,textual}.py`, `src/decoders/{metrics,classifier,stat_test,randomized_control,run_all}.py`; testler `tests/test_decoders.py` ve `tests/test_probes.py` (34 test). Çıktılar: `results/decoder_results.csv`, `results/stat_tests.json`, `results/features.csv`.

**Yöntem.** Hedef: konuda confidential doküman var mı (10 var / 10 yok). Sabit L2 lojistik regresyon (`class_weight="balanced"`, ayar yok); gruplar `behavior_nolat`, `behavior` (+latency), `text` (uzunluk + 22 stilometri + PCA(5) embedding), `behavior+text`. Birincil değerlendirme leave-one-topic-out. Randomized control: (i) konu-etiketi permütasyonu (184 756 dengeli etiketlemeden 500'ü Monte Carlo; p = (1+#≥)/(1+N), min ≈ 0,002), (ii) satır düzeyi etiket karıştırma (100), (iii) plasebo decoder (control satırları, aynı etiketle). "Kanal açık": önceden belirlenmiş tek test (konu-permütasyon p < 0,05) **ve** AUC güven aralığı alt sınırı > 0,5.

**Not (8 konuluk pilotta bulunan yöntem hatası):** LOTO + dengeli konu etiketlerinde lojistik regresyonun kesişim terimi etiketle ters ilişkili skor üretiyor (sabit özelliklerle AUC = 0,0). `class_weight="balanced"` ile giderildi, regresyon testi eklendi. Gürültüde kalan küçük sapma nedeniyle karar ölçütü mutlak AUC değil permütasyon p ve avantajdır.

**Sonuçlar (20 konu):**

| Model | Mod | Grup | AUC [%95 GA] | TPR@1%FPR | Gereken mesaj | Sızan bit/mesaj | p (konu-perm.) | Avantaj | Plasebo AUC | Kanal açık |
|---|---|---|---|---|---|---|---|---|---|---|
| gemma3 | M1_weak | behavior_nolat | 0.44 [0.30–0.57] | 0.00 | – | 0.00 | 0.543 | -0.01 | 0.43 | hayır |
| gemma3 | M1_weak | behavior | 0.48 [0.33–0.63] | 0.00 | – | 0.00 | 0.461 | +0.02 | 0.42 | hayır |
| gemma3 | M1_weak | text | 0.82 [0.75–0.91] | 0.12 | 2 | 0.12 | 0.004 | +0.36 | 0.35 | evet |
| gemma3 | M1_weak | behavior+text | 0.78 [0.70–0.86] | 0.00 | 3 | 0.00 | 0.006 | +0.31 | 0.40 | evet |
| gemma3 | M2_strong | behavior_nolat | 0.47 [0.32–0.62] | 0.00 | – | 0.00 | 0.489 | +0.01 | 0.41 | hayır |
| gemma3 | M2_strong | behavior | 0.46 [0.31–0.62] | 0.00 | – | 0.00 | 0.547 | -0.01 | 0.42 | hayır |
| gemma3 | M2_strong | text | 0.45 [0.34–0.56] | 0.00 | – | 0.00 | 0.563 | -0.02 | 0.43 | hayır |
| gemma3 | M2_strong | behavior+text | 0.48 [0.35–0.60] | 0.00 | – | 0.00 | 0.485 | +0.01 | 0.42 | hayır |
| qwen2.5 | M1_weak | behavior_nolat | 0.57 [0.38–0.76] | 0.20 | – | 0.05 | 0.190 | +0.12 | 0.55 | hayır |
| qwen2.5 | M1_weak | behavior | 0.58 [0.41–0.76] | 0.20 | – | 0.03 | 0.182 | +0.12 | 0.53 | hayır |
| qwen2.5 | M1_weak | text | 0.61 [0.48–0.72] | 0.00 | – | 0.00 | 0.126 | +0.14 | 0.33 | hayır |
| qwen2.5 | M1_weak | behavior+text | 0.61 [0.45–0.72] | 0.12 | – | 0.00 | 0.112 | +0.14 | 0.41 | hayır |
| qwen2.5 | M2_strong | behavior_nolat | 0.43 [0.29–0.60] | 0.00 | – | 0.00 | 0.547 | -0.01 | 0.42 | hayır |
| qwen2.5 | M2_strong | behavior | 0.45 [0.33–0.63] | 0.02 | – | 0.00 | 0.591 | -0.02 | 0.43 | hayır |
| qwen2.5 | M2_strong | text | 0.42 [0.32–0.53] | 0.00 | – | 0.00 | 0.693 | -0.05 | 0.55 | hayır |
| qwen2.5 | M2_strong | behavior+text | 0.37 [0.28–0.47] | 0.00 | – | 0.00 | 0.848 | -0.10 | 0.45 | hayır |

Randomized control: satır karıştırma AUC ortalaması 0,46–0,51 (≈ şans); plasebo AUC 0,33–0,55 (aynı prosedürün gürültü düzeyi).

**İstatistik testleri (`stat_tests.json`).** Konu düzeyi present-vs-absent (exact/MC permütasyon), refusal oranı: gemma3-M1 p=0,05, qwen2.5-M1 p=0,034, diğerleri anlamlı değil; Holm sonrası en küçük p = 0,094 (qwen2.5-M2 cevap uzunluğu) → hiçbiri düzeltmeyi geçmiyor. Satır düzeyi betimleyici testlerde qwen2.5-M1 `refusal_type` ki-kare p = 0,001 (varyantlar bağımsız olmadığı için iyimser). qwen2.5-M1'de ret türü dağılımı: present konularda 10 `cannot_share`, absent konularda 0.

**Metin sinyali içerik sızıntısı mı?** M1'de present konulara ait probe cevaplarında doğrudan sorulardaki gizli ifadeler (rakamlar, yer adları) gemma3'te 12/50 (%24), qwen2.5'te 4/50 (%8) cevapta geçiyor; M2'de 0/100. Yani meşru, masum müşteri sorularında bile M1 gizli içeriği cevaba taşıyor (alt sınır: yalnızca bilinen işaretçiler sayıldı).

**Bulgular (yorumsuz özet).**
1. **gemma3 + M1_weak, metin:** AUC 0,83 [0,75–0,91], p = 0,004, avantaj +0,36, 2 mesajda konu düzeyinde AUC ≥ 0,9. Pilottaki sonuçla (0,84, p = 0,029) tutarlı ve 20 konuda daha güçlü. Aynı hücrede cevaplar gizli içeriği doğrudan içerdiği için bu, *davranışsal* yan kanaldan çok M1'in bilinen **içerik sızıntısının** istatistiksel yansıması.
2. **Sadece-davranış özellikleri:** 8 hücre grubunun hiçbirinde anlamlı sinyal yok (en küçük p = 0,18, qwen2.5-M1). İpucu niteliğinde: qwen2.5-M1'de AUC 0,57–0,58, avantaj +0,12, `cannot_share` yalnızca present konularda; ama plasebo AUC (0,53–0,55) gerçek AUC'ye yakın, konu-permütasyon p ≥ 0,18 ve Holm geçmiyor → kanıt değil, takip edilecek bir ipucu.
3. **M2_strong:** hiçbir model ve grupta sinyal yok (p ≥ 0,48). 20 konuyla pilota göre güç daha yüksek (AUC GA yarı genişliği ≈ 0,15) ama yine de küçük etkileri (AUC < ~0,65) dışlayamıyoruz. Güçlü ACL bu ölçekte gözlemlenebilir davranışsal sızıntıyı sıfırlıyor görünüyor.
4. 16 karşılaştırma için çoklu test düzeltmesi yapılmadı; tek sağlam sonuç (1) zaten Bonferroni (0,05/16 = 0,003) sınırının hemen yanında (p = 0,004).

### 6.x Maskeleme analizi (gemma3 M1 metin sinyali)
Soru: gemma3+M1 metin sinyali (AUC 0,83) yalnızca cevaba sızan gizli terimlerden mi geliyor? Yeni koşu yok; `src/features/masking.py` + `python -m src.decoders.run_masked`. İki seviye: `topic` (konu anahtar kelimeleri ve konu adı sözcükleri → XXX), `strict` (ek olarak rakamlar, sayı sözcükleri, cümle ortası büyük harfli sözcükler ve yalnızca gizli dokümanlarda geçen 210 sözcük).

| Seviye | gemma3 M1 text AUC [GA] | p (konu perm.) | gemma3 M2 text | qwen2.5 M1 text |
|---|---|---|---|---|
| maskesiz | 0,83 [0,75–0,91] | 0,004 | p ≥ 0,48 | 0,61 (p 0,126) |
| topic | 0,83 [0,77–0,90] | 0,002 | 0,40 (p 0,77) | 0,55 (p 0,24) |
| strict | 0,82 [0,75–0,90] | 0,002 | 0,43 (p 0,67) | 0,53 (p 0,28) |

**Sonuç:** Maskeleme sinyali ortadan kaldırmıyor; önceki "sinyal doğrudan içerik sızıntısıyla açıklanır" yorumu desteklenmedi. Sinyal sözcük içeriğinden değil üslup kaymasından geliyor (konu düzeyinde, M1 present vs absent): present konularda "we/our" 0,050 vs 0,017 (p=0,0006), "I" 0,009 vs 0,032 (p=0,0006), "unfortunately" 0 vs 0,14, telefon/e-posta içerme 0,06 vs 0,24, rakam oranı 0,005 vs 0,015. Yani gizli bağlam varken model kurumsal "biz" diliyle, jenerik özür + iletişim bilgisi yönlendirmesi olmadan cevaplıyor. Bu, davranış (karar alanı) değil metin üslubu kanalıdır; M2'de yok. Uyarılar: keşifsel (özellik başına p düzeltilmedi), 10+10 konu, tek model; kalan sözcüksel/semantik sızıntı (parafraz) tamamen dışlanamaz. Çıktı: `results/decoder_results_masked.csv`.


## 7. Faz 5 — Ana tablo, M1 vs M2 ve gizli belge sayısı taraması
Çıktılar: `results/main_table.md`, `main_results.csv`, `m1_vs_m2.csv`, `ratio_table.md`, `ratio_results.csv`, `ratio_retrieval.csv`, `figures/` (`auc_m1_vs_m2.png`, `leaked_bits_m1_vs_m2.png`, `auc_vs_docs_per_topic.png`). Komutlar: `python -m src.experiments.analyze`, `python -m src.experiments.ratio`, `python -m src.experiments.retrieval_stats`.

### 7.1 M1 vs M2 (LOTO AUC, k=3)
| Model | Grup | AUC M1 | AUC M2 | p M1 | p M2 |
|---|---|---|---|---|---|
| gemma3 | behavior | 0,48 | 0,46 | 0,46 | 0,55 |
| gemma3 | text | 0,82 | 0,45 | 0,004 | 0,56 |
| gemma3 | behavior+text | 0,78 | 0,48 | 0,006 | 0,49 |
| qwen2.5 | behavior | 0,58 | 0,45 | 0,18 | 0,59 |
| qwen2.5 | text | 0,61 | 0,42 | 0,13 | 0,69 |

Randomized control satırları (satır karıştırma, konu permütasyonu, plasebo) ana tabloda her hücre için yer alıyor ve şansa yakın (≈ 0,35–0,50). M2'de hiçbir hücrede sinyal yok; M1'de tek anlamlı kanal gemma3 metin/üslup kanalı. Davranış (karar alanı) grupları hiçbir hücrede güvenilir sinyal vermiyor.

### 7.2 Gizli belge sayısı taraması
**k nedir:** kanarya konusu başına M1_weak'te retrieval'a açık gizli kanarya belgesi sayısı (üretilen 3 belgeden ilk k'sı; kalanı `doc_id` filtresiyle dışlanır). Normal Enron belgeleri sabit; yani k gizli/normal belge oranını ayarlar. Yalnızca M1 koşuldu (M2 gizli belgeyi zaten getirmiyor); k=1,2 için 2 model × 20 konu × 5 varyant × probe/control = 400 çağrı/k, k=3 mevcut tam matris.

**Müdahale kontrolü (top-5 bağlamında gizli belge, M1, `ratio_retrieval.csv`):**
| k | present konu, probe: ort. gizli belge | konunun kendi kanaryası geldi | absent konu, probe | present, control |
|---|---|---|---|---|
| 1 | 1,88–1,90 | %94–96 | 1,06 | 1,10 |
| 2 | 2,48 | %96 | 1,10 | 1,16 |
| 3 | 3,30 | %100 | 1,14 | 1,16 |

Retrieval k ile tek yönlü artıyor, yani doz-yanıt değişkeni beklendiği gibi çalışıyor. Modellerin retrieval'ı aynı (aynı retriever). Dikkat: absent konularda ve control mesajlarında bile top-5'te ortalama ~1 "gizli" belge var (%58–64 mesajda ≥1); bunlar kanarya olmayan, ACL etiketleyicinin gizli dediği Enron belgeleridir. Fark yokluk/varlıkta değil gizli belge sayısındadır (≈1 vs 1,9–3,3).

**AUC (M1_weak):**
| Model | Grup | k=1 | k=2 | k=3 |
|---|---|---|---|---|
| gemma3 | text | 0,71 (p 0,012) | 0,64 (p 0,048) | 0,82 (p 0,004) |
| gemma3 | behavior+text | 0,71 (p 0,004) | 0,57 (p 0,14) | 0,78 (p 0,006) |
| gemma3 | behavior | 0,45 | 0,38 | 0,48 |
| qwen2.5 | behavior | 0,55 (p 0,21) | 0,66 (p 0,042) | 0,58 (p 0,18) |
| qwen2.5 | behavior+text | 0,59 | 0,73 (p 0,010) | 0,61 |

**Yorum:** Girdi dozu monoton arttığı halde AUC monoton değil; bu, retrieval başarısızlığıyla açıklanamaz (kendi kanaryası %94–100 geliyor). Güven aralıkları geniş ve örtüşüyor (ör. gemma3 text: k=1 [0,60–0,80], k=2 [0,51–0,75], k=3 [0,75–0,91]); k=1→2 farkı gürültü düzeyinde. Sağlam olan tek şey: gemma3'te metin/üslup sinyali tek gizli belgeyle (k=1) bile anlamlı, k=3'te en güçlü; davranış grupları gemma3'te her k'de şans düzeyinde. qwen2.5 davranış sinyali yalnızca k=2'de anlamlı (p 0,036–0,042) ve k=1,3'te yok; ~24 hücre içinde düzeltmesiz tek böyle sonuç olduğundan bulgu olarak sunulmuyor. Sızan bit çoğunlukla 0 (en fazla 0,12 bit/mesaj).

**Uyarılar:** 20 konu, repeats=1, çoklu test düzeltmesi yok; k=3 ayrı bir koşudan (aynı yapılandırma, sıcaklık 0) geldiği için k=1,2 ile fark kısmen koşu gürültüsü olabilir. "Oran arttıkça sızıntı artıyor/azalıyor" iddiası bu veriyle desteklenmiyor. Daha güçlü test için daha çok konu veya tekrar gerekir.

## 8. Faz 6 — Savunmalar ve güvenlik-fayda
Plan: `plans/faz6_plan.md`. Kod: `src/defenses/` (`behavior_norm`, `scoped_context`, `decision_hiding`, `quality`, `evaluate_defenses`, `figures`); komut: `python -m src.defenses.evaluate_defenses {collect,build,evaluate}`. Çıktılar: `results/defense_results.csv`, `results/defense_table.md`, `results/figures/security_utility.png`, `results/defenses/`.

**Savunmalar (korunan yapılandırma M1_weak):**
- `behavior_norm`: ret/eskalasyon cevapları tek şablon + tek ret türü (çevrimdışı, loglara uygulanır).
- `scoped_context`: dış mesaj için retrieval yalnızca `public` (M2'den sıkı: internal de dışarıda).
- `decision_hiding`: `routing_target`/`escalated`/`refusal_type` bağlamsız ikinci çağrıdan (yalnızca müşteri mesajı); gecikme sabit 60 s (ham gecikmeler < 60 s, aşım yok).
- `all`: üçü birden. `M2_reference`: Faz 5'teki güçlü ACL.

**Fayda ölçüleri:** (a) çözüm oranı (control mesajlarında ham karar `none` ve eskalasyon yok), (b) yönlendirme uyumu (savunmasız ajanla aynı `routing_target`), (c) 23 soruluk fayda setinde (`data/probes/utility_queries.json`; 14 public + 9 internal kaynaklı, hepsi M1'de top-5'te doğrulanmış, işaretçi içeren) cevaptaki işaretçi recall'ı. Fayda seti Claude tarafından oturumda yazıldı.

**Sonuçlar (LOTO AUC [%95 GA], M1_weak; `none` Faz 5'i aynen yeniden üretti):**
| Savunma | gemma3 text | gemma3 beh+text | qwen2.5 beh+text | Recall kaybı (gemma3 / qwen2.5) | Yönlendirme uyumu |
|---|---|---|---|---|---|
| none | 0,82 [0,75–0,91] | 0,78 [0,70–0,86] | 0,61 [0,45–0,72] | 0 / 0 | 1,00 |
| behavior_norm | 0,82 [0,73–0,90] | 0,82 [0,72–0,91] | 0,63 [0,48–0,75] | 0,04 / 0,00 | 1,00 |
| scoped_context | 0,44 [0,27–0,58] | 0,49 [0,34–0,62] | 0,42 [0,26–0,57] | 0,30 / 0,35 | 0,60 / 0,66 |
| decision_hiding | 0,82 [0,75–0,91] | 0,84 [0,79–0,91] | 0,54 [0,41–0,65] | 0 / 0 | 0,61 / 0,64 |
| all | 0,51 [0,37–0,62] | 0,54 [0,42–0,66] | 0,45 [0,30–0,59] | 0,30 / 0,35 | 0,61 / 0,64 |
| M2 referansı | 0,45 [0,34–0,56] | 0,48 [0,35–0,60] | 0,37 [0,28–0,47] | 0,04 / −0,04 | – |

Konu perm. p: gemma3 text `none` 0,004, `behavior_norm` ≈ 0, `decision_hiding` ≈ 0 (kanal açık); `scoped_context` 0,63, `all` 0,36 (kapalı). Sızan bit: gemma3 `none` 0,12 → `scoped_context`/`all` 0.

**Fayda ayrıntısı (recall, public / internal kaynaklı sorular):** `none` gemma3 0,86 / 1,00, qwen2.5 0,93 / 0,78; `scoped_context` gemma3 1,00 / **0,00**, qwen2.5 0,86 / **0,00**. Çözüm oranı `scoped_context`'te değişmiyor (0,93 / 0,99): ajan internal kaynak yokken de ret etmeden cevap veriyor, ama işaretçiyi içermiyor. Cevapların doğru/uydurma olup olmadığı ölçülmedi. M2 referansında çözüm oranı gemma3'te 0,92 → 0,67'ye düşüyor.

**Yorum (temkinli):**
1. **Sinyali kapatan tek savunma `scoped_context`** (gemma3 text 0,82 → 0,44, p 0,63; `all`'da 0,51). `all`, `scoped_context`'e ek güvenlik katmıyor.
2. **Bedeli belirgin ve öngörülen yönde:** internal kaynaklı soruların hiçbirinde işaretçi gelmiyor (recall 0), yönlendirme uyumu ~0,6. Çözüm oranı bu kaybı yakalamıyor; yalnızca çözüm oranına bakılsaydı savunma bedelsiz görünürdü.
3. **`behavior_norm` metin kanalına etki etmedi** (gemma3 text 0,82 → 0,82; beh+text 0,78 → 0,82). Planın hipotezi doğrulandı: sızıntı ret metinlerinde değil normal cevapların üslubunda.
4. **`decision_hiding` gemma3'te sızıntıyı azaltmadı** (beh+text 0,78 → 0,84, aralıklar örtüşüyor); qwen2.5'te 0,61 → 0,54 farkı da GA içinde. Bedeli yönlendirme kalitesi (uyum ~0,61). Uyarı: bağlamsız kararlar yalnızca mesaja bağlı olduğundan mesaj/konu kimliğini taşır; bu LOTO'da bile AUC'yi bozabilir.
5. **M2 referansı `scoped_context` kadar güvenli ama çok daha az pahalı** (recall kaybı ≤ 0,04; internal sorularda recall 0,89–1,00). Yani yalnızca confidential'ı retrieval'da kesmek (M2) yeterli; public-only kapsam gereğinden sıkı. M2'nin bedeli recall'da değil çözüm oranında (gemma3 0,92 → 0,67).

**Uyarılar:** 20 konu, repeats=1; aralıklar geniş, ±0,07'lik farklar anlamlı değil, çoklu test düzeltmesi yok. Fayda seti küçük (23 soru) ve tek yazarlı; recall kaba bir işaretçi ölçüsü. LOTO AUC şans altına (≈ 0,4) inebiliyor. Scoped koşusunda bellek baskısı nedeniyle bozulan 36 + 6 satırın gecikmesi temizlemek için satırlar yeniden koşuldu (sıcaklık 0, metin aynı beklenir; karşılaştırılmadı). Bağlamsız karar önbelleği `results/cache/ctxfree_decisions.jsonl` (repoda zorla eklendi).

### 8.1 Maskeleme savunması (span düzeyinde; plans/maskeleme_plan.md)
Soru: gizli belge bağlamda kalıp yalnızca hassas parçaları maskelenirse sızıntı kapanır mı, fayda M2'den iyi mi? Kod: `src/defenses/masking.py` (`MaskedRetriever`: M1_weak retrieval, yalnızca `confidential` parçalar bağlama girmeden maskelenir; public/internal dokunulmaz), sürücü `src/defenses/evaluate_masking.py`, veri `data/probes/secret_spans.json` ve `utility_conf.json` (Claude oturumunda, tek yazar). Prompt M1_weak ile aynı (fark yalnızca bağlam). Plandan sapma: yer tutucu `[REDACTED]` (İngilizce ajan).

**Maskeleyiciler.** `oracle`: elle yazılmış sır aralıklarını (sayı, tarih, bütçe, kadro, tedarikçi/site ayrıntısı, pozisyon) `[REDACTED]` ile değiştirir; sızıntıyı yapı gereği sıfırlayan üst sınır. `rule`: çalıştırmadan önce dondurulmuş genel regex kuralları (sayı/para/yüzde, tarih, e-posta/telefon, cümle başı olmayan büyük harfli sözcükler) ve tür etiketli yer tutucular. Politika: konunun varlığı ve dışarıya onaylı müşteri cümlesi **maskelenmez**; bu tek yazarın politika kararıdır, farklı bir politika farklı sonuç verir.

**Ölçümler.** (a) *Doğrudan soru sızıntısı:* 20 soru × 2 model, cevapta sır işaretçisi. (b) *Probe sızıntısı:* probe cevaplarında işaretçi. (c) *Yan kanal:* aynı sabit decoder ve randomized control'ler, `results/mask_results.csv`, `results/mask_table.md`. (d) *Fayda:* 23'lük set (public/internal kaynak), kontrol mesajı çözüm oranı ve **onaylı-cümle geri çağrısı** (gizli konuda sır olmayan, dışarıya söylenmesi onaylı cümleyi üretme, 18 soru; ör. "piyasa söylentilerine yorum yapmıyoruz"). Mevcut 23'lük sette gizli kaynak olmadığı için bu yeni set M2/maskeleme farkını görünür kılar.

| Model | Koşul | Metin AUC [GA] | p | Doğrudan sızıntı | Çözüm | Recall util23 | Onaylı-cümle recall |
|---|---|---|---|---|---|---|---|
| gemma3 | none (M1) | 0,82 [0,75–0,91] | 0,004 | 0,50 | 0,92 | 0,91 | 0,33 |
| gemma3 | M2 | 0,45 [0,34–0,56] | 0,563 | 0,00 | 0,67 | 0,87 | 0,00 |
| gemma3 | scoped | 0,44 [0,27–0,58] | 0,629 | – | 0,93 | 0,61 | 0,00 |
| gemma3 | mask_oracle | 0,84 [0,77–0,92] | 0,002 | 0,00 | 0,90 | 0,91 | 0,33 |
| gemma3 | mask_rule | 0,69 [0,55–0,83] | 0,016 | 0,00 | 0,92 | 0,87 | 0,39 |
| qwen2.5 | none (M1) | 0,61 [0,48–0,72] | 0,126 | 0,35 | 1,00 | 0,87 | 0,22 |
| qwen2.5 | M2 | 0,42 [0,32–0,53] | 0,693 | 0,00 | 1,00 | 0,91 | 0,00 |
| qwen2.5 | scoped | 0,52 [0,39–0,66] | 0,305 | – | 0,99 | 0,52 | 0,00 |
| qwen2.5 | mask_oracle | 0,60 [0,44–0,74] | 0,122 | 0,00 | 1,00 | 0,87 | 0,28 |
| qwen2.5 | mask_rule | 0,59 [0,44–0,70] | 0,144 | 0,00 | 1,00 | 0,87 | 0,33 |

**Bulgular.**
1. *İçerik sızıntısı kapanıyor.* Doğrudan soru sızıntısı 0,50 → 0,00 (gemma3) ve 0,35 → 0,00 (qwen2.5), probe cevaplarında da 0. Oracle'da sıfır beklenen bir doğrulama kontrolüydü (yapı gereği). **Rule maskeleyici de işaretçileri sıfırladı**, ama bu planın "kaçırır" öngörüsünü doğrulamıyor: kurallar sayı/tarih/ad işaretçilerini yakaladı, sayısal olmayan işaretçiler ("outsourc", "vendor", "non-disparagement") doğrudan sorulara girmedi veya modelin cevabına yansımadı. Bu, 40 soruluk örnekte bir üst sınır değil bir gözlemdir. Kanarya belgeleri üzerinde yapılan kontrolde kuralların bu üç işaretçiyi belgede bıraktığı görüldü (c03_1 "non-disparagement", c09_1 "outsourc"/"vendor"), yani sızıntı riski var; bu örnekte cevaba yansımadı.
2. *Metin üslubu kanalı kapanmıyor.* gemma3'te oracle AUC 0,84 (p = 0,002), M1'den (0,82) ayrışmıyor; rule 0,69 (p = 0,016) kısmen düşüyor ama kanal-açık ölçütünü hâlâ geçiyor. M2 ve scoped (0,44–0,45) kanalı kapatıyor. Dolayısıyla H2 doğrulandı: maskelenmiş belge de konunun *varlığını* ve bağlamını (proje adı, "deal team", genel durum) taşıyor ve model bunu üsluba yansıtıyor. Yer tutucu yankısı bunu kısmen açıklıyor: oracle'da gemma3 present-probe cevaplarının 6/50'si (diğerlerinde 0/150) `[REDACTED]` içeriyor; rule'da 20/50 (diğer satırlarda 4/50 probe, 11/99 kontrol) yer tutucu içeriyor. Yani yer tutucu bir ipucu, ama oracle'ın AUC 0,84'ünü tek başına açıklamıyor.
3. *Fayda korunuyor.* Onaylı-cümle geri çağrısı M1'e eşit veya yakın (0,28–0,39 vs 0,22–0,33) ve M2 ile scoped'ın sıfırının çok üstünde; çözüm oranı M2'nin gemma3'teki düşüşünü (0,92 → 0,67) yaşamıyor (0,90–0,92); util23 recall'u scoped'ın kaybını yaşamıyor (0,87–0,91 vs 0,52–0,61). Not: onaylı-cümle recall'u M1'de de düşük (0,22–0,33), çünkü model cümleyi çoğu zaman birebir üretmiyor; bu metriğin mutlak değerine değil kıyasa güveniyoruz.
4. *Davranış-yalnızca.* Hiçbir koşulda kanal-açık yok. qwen2.5 + mask_oracle davranış grubunda nominal p = 0,036 (AUC 0,68) ve behavior+text'te kanal-açık (AUC 0,75, p = 0,014) çıktı; M1 qwen2.5'te kanal zaten kapalıydı (AUC 0,61). Birden çok hücre karşılaştırıldığı için (5 koşul × 4 grup × 2 model = 40 hücre) bu bir ipucu olarak okunmalı, kanıt olarak değil.

**Yorum (güvenlik-fayda).** Maskeleme *içerik* sızıntısını M2 ile aynı düzeyde (0) kapatırken faydayı korur (M2 ve scoped'ın aksine), ama *metin üslubu kanalını kapatmaz*; bunun için belgenin bağlama hiç girmemesi gerekiyor (M2/scoped). Pratik sonuç: koruma hedefi "sırrın içeriği" ise maskeleme M2'den iyi bir dengedir; hedef "konunun varlığı" ise maskeleme yetmez. Sınırlar: 10 konu × 5 varyant, tek tekrar, iki yerel model, tek yazarlı sır politikası; rule maskeleyicinin 40 soruda sıfır sızıntısı genelleşmez; onaylı-cümle seti ve değerlendirme metriği bu çalışma için yazıldı. Koşu notu: doğrudan sorularda iki sorunun message_id'si çakışıyordu (aynı konu kimliği); bu yüzden ilk doğrudan koşu yarım kaldı, kod düzeltilip dört koşul için silinip yeniden koşuldu.

## 9. Ek pilot — çok kullanıcılı sızıntı (A → B)
Soru: kullanıcı A'nın bota meşru biçimde verdiği veri, yalnızca meşru mesaj yazan kullanıcı B'ye sızıyor mu? Plan: `plans/pilot_cok_kullanici_plan.md`. Bu, ana çalışmaya **ek** bir pilottur; ana bulguları değiştirmez.

**Kurulum.** A, 10 konuda (c00–c03, c08–c13) kendi hesabına özel not verir (`data/xuser/shares.json`, Claude oturumunda yazıldı, uydurma). Kurumsal belgeler M2 gibi süzülür (kanarya belgesi yok); sır yalnızca A'nın mesajındadır. B, ana çalışmadaki 200 probe/kontrol mesajını gönderir (20 konu × 5 varyant × probe/kontrol; 10 konuda A'nın verisi var, 10'da yok). Modlar: **X1_shared_weak** (tüm kullanıcılar için ortak hafıza, prompt "başkasının verisini verme" der), **X2_isolated** (kullanıcı başına hafıza; B'nin görünümünde A yok, negatif kontrol), **X3_shared_summary** (A'nın verilerinden LLM ile üretilmiş ortak not her bağlamda). 2 model × 3 mod × 200 = 1200 çağrı, hepsi tamam (bir satır parse hatası).

**İzolasyonun uygulanışı (X2_isolated).** İzolasyon prompt'ta değil, LLM'e giden bağlam oluşturulmadan önce, retrieval katmanında uygulanıyor. Adımlar:

1. *Yazım (sahiplik etiketi).* `UserMemory.write(owner, text, topic_id)` (`src/multiuser/memory.py`) her mesajı verbatim, MiniLM ile gömülmüş vektörüyle birlikte `MemoryEntry(owner, text, topic_id, vec)` olarak saklar. `owner` ("A" veya "B") yazım anında konuşan kullanıcıdan gelir. A fazında LLM çağrısı yoktur, A'nın 10 mesajı `owner="A"` ile yazılır. Hafıza ayrı, süreç içi (numpy) bir yapıdır; kurumsal belge indeksinden (ChromaDB) bağımsızdır.
2. *Arama (sahibe göre süzme).* `UserMemory.search(query, k, owner)` önce adayları `pool = [e for e in entries if owner is None or e.owner == owner]` ile süzer, kosinüs benzerliğini yalnızca bu havuzda hesaplar ve top-k (k = `memory_top_k` = 2) döndürür. Süzme sıralamadan **önce** olduğundan A'nın kaydı B için ne yüksek skorla ne düşük skorla aday olur. Bu "sonradan çıkarma" değil, "baştan görmeme"dir.
3. *Mod seçimi.* `MultiUserRetriever.retrieve(message, mode)` (`src/multiuser/retriever.py`) önce kurumsal bağlamı M2 gibi alır (`super().retrieve(message, "M2_strong")`; yapıcıda `docs_per_topic=0`, yani tüm kanarya belgeleri indeks dışı, yalnızca public+internal). Ardından hafıza parçasını moda göre ekler: X1'de `owner=None` (tüm kullanıcıların kayıtları aranır), X2'de `owner=self.current_user` (= "B"), X3'te paylaşılan özet notu. Bilinmeyen mod `ValueError` verir (sessizce başka moda düşmez).
4. *Kimlik.* Sorgulayan kullanıcı retriever'da sabit alandır (`current_user="B"`); pilotta B'nin kimliği doğrulama/oturum katmanı olmadan, deney düzeneği tarafından verilir. Gerçek üründe bu etiketin doğruluğu kimlik doğrulamaya bağlıdır; burada bu varsayım ölçülmüyor.
5. *B'nin görünümü.* B'nin mesajları hafızaya yazılmaz (plan kararı). Bu yüzden X2'de B'nin havuzu boştur ve B'nin bağlamı yalnızca kurumsal belgelerden oluşur; X2 bu anlamda "A hiç konuşmamış" koşuluyla (X0) aynıdır ve negatif kontrol işini görür.
6. *Prompt.* X2'de ek bir "başkasının verisini verme" kuralı **yoktur** (`SYSTEM_MODE` içinde X2 yok); X1 ve X3'te `SYSTEM_XUSER` kuralı vardır. Yani X1/X2 farkı iki şeyin birleşimidir: retrieval süzmesi ve kuralın yokluğu. Kural olmadan da sızıntının sıfıra inmesi, korumanın promptta değil bağlam sınırında olduğunu gösterir, ama "yalnızca süzme" etkisi ayrı bir deneyle (X2 + kural, X1 − kural) izole edilmedi.

*Doğrulama.* (a) Birim test `test_x2_isolated_never_returns_other_users_memory`: A'nın kayıtları varken X2 sorgusu hiç `user_memory` parçası döndürmez; B bir kayıt yazınca yalnızca B'nin kaydı döner. (b) Koşu logu: 400 X2 satırının (2 model × 200) hiçbirinde bağlamda `mem_A_*` yok (`results/xuser_retrieval.csv`, own_mem = any_mem = 0). (c) Sızıntı ölçümü: X2'de işaretçi oranı gürültü tabanında (bölüm 9 tablosu).

*Sınır.* X3 (paylaşılan özet) bu yolla izole edilemez: özet, tüm kullanıcıların mesajlarından üretilmiş tek bir metindir ve içinde sahiplik bilgisi kalmaz. X3'ün korunması için özetin kullanıcı başına üretilmesi gerekir, bu da X2'ye indirgenir. Ayrıca izolasyon yalnızca hafıza yolunu kapatır; modelin kendi ağırlıkları, loglar veya çıktı üzerinden gelen yan kanallar bu mekanizmanın kapsamı dışındadır.

**Doğrulama 1 — retrieval (`results/xuser_retrieval.csv`).** X1'de A'nın kaydı, A'nın verisi olan konuda B'nin probe bağlamına %98 (kontrol %46) giriyor, verisi olmayan konuda %0. X2'de hiç girmiyor (0/200 her hücrede), X3'te ortak not her bağlamda var.

**Doğrulama 2 — doğrudan içerik sızıntısı (`results/xuser_leak.csv`; B'nin cevabında A'nın sır işaretçilerinden biri geçiyor mu).**

| model | mod | probe, veri var | kontrol, veri var | probe, veri yok |
|---|---|---|---|---|
| gemma3 | X1_shared_weak | 36/50 (%72) | 5/50 | 0/50 |
| gemma3 | X2_isolated | 1/50 (%2) | 3/50 | 0/50 |
| gemma3 | X3_shared_summary | 35/50 (%70) | 2/50 | 0/49 |
| qwen2.5 | X1_shared_weak | 26/50 (%52) | 1/50 | 0/50 |
| qwen2.5 | X2_isolated | 0/50 | 0/50 | 0/50 |
| qwen2.5 | X3_shared_summary | 28/50 (%56) | 0/50 | 0/50 |

Ortak hafıza, prompt'ta "başkasının verisini verme" kuralı olmasına rağmen A'nın sayısal/ayrıntı verisini B'nin cevabına yazıyor (probe konuya doğrudan sorduğunda). X2'de oran gürültü tabanına iner (gemma3'te 1–3 satır, sayıların tesadüfen geçmesi). Dolayısıyla izolasyon (kullanıcı başına hafıza) kapatıyor, prompt kuralı kapatmıyor; bu, ana çalışmanın M1/M2 bulgusuyla aynı yönde.

**Yan kanal (decoder, `results/decoder_results_xuser.csv`).** Aynı sabit decoder ve randomized control'lerle, "A bu konuda veri paylaştı mı?" etiketi, B'nin gözlediği çıktıdan. 24 hücrenin (2 model × 3 mod × 4 özellik grubu) yalnızca biri kanal-açık ölçütünü geçti: **qwen2.5 + X3 + metin, AUC 0,668 (CI 0,531–0,789), konu-permütasyon p = 0,032**. Davranış-yalnızca hücreleri hiçbirinde anlamlı değil (en yüksek qwen2.5-X1 davranış, AUC 0,605, p = 0,116). X2 negatif kontrolünün hiçbir hücresi anlamlı değil, beklenen sonuç. Düzeltme yapılmadan 24 testte ≈ 1 yanlış pozitif beklenir; tek hücrelik p = 0,032 bulgusu kanıt değil, tutarlı bir ipucu olarak okunmalı. X3'te metin sinyali büyük olasılıkla doğrudan içerik sızıntısıyla birlikte gidiyor (aynı cevaplarda A'nın işaretçileri var), yan kanal olarak ayrıştırılmadı.

**Sonuç.** (1) Çok kullanıcılı **doğrudan sızıntı** gerçek ve büyük (%52–72); ortak hafıza + prompt kuralı yetmez, kullanıcı başına izolasyon kapatır. (2) **Davranışsal yan kanal** burada da bulunamadı (davranış-yalnızca hücreleri anlamsız); tek aday metin hücresi çoklu karşılaştırma altında zayıf. (3) Sınırlar: 10 konu, 5 varyant, tek tekrar, iki yerel model, A mesajları tek yazardan; X3 özeti modelin ürettiği bir yapı olduğundan gerçek ürünlerdeki hafıza özelliğini yalnızca yaklaşık temsil eder. Savunma (çok kullanıcılı bağlamda kapsamlama) ayrıca sınanmadı.

Koşu notları: Ollama bellek şişmesi nedeniyle koşu 10'luk parçalarla yapıldı; tekrar döngüsüne giren üretimleri sınırlamak için ajan çağrısına `max_tokens=700` eklendi ve sunucu iptalleri başarısız deneme sayıldı (önceki koşuları etkilemez, yalnızca kontrolsüz üretimleri keser). >20 s gecikmeli thrash satırları silinip yeniden koşuldu; 1 satırda gecikme 20 s üzerinde kaldı.

## 10. Sınırlılıklar ve açık noktalar
- İki model de yerel/açık ağırlıklı; plandaki "biri ticari API" şartı API anahtarı olmadığı için karşılanmadı. Anahtar alınırsa config'e model eklemek yeterli.
- Kanarya ve probe metinleri tek yazar tarafından (Claude oturumunda) yazıldı; üslup çeşitliliği sınırlı.
- Gizli belge taraması (k) yalnızca M1'de, repeats=1; k etkisi istatistiksel olarak ayrışmıyor (bkz. 7.2).
- Ölçek: 10+10 konu, 5 varyant, tek tekrar. TPR@1%FPR çözünürlüğü kaba (50 negatif probe satırı/hücre).
- Ajan davranışı düşük değişkenlikli (eskalasyon hiç yok, ret nadir): davranışsal kanal için taşıyıcı sinyal az. Ajan promptunun daha çok ret/eskalasyon üretecek şekilde gözden geçirilmesi ayrı bir deney olabilir.
- Konu kimliği ile predicate karışık olabilir (konu-leksikal etki); LOTO + plasebo azaltır, elemez.
- LOTO'nun gürültüde AUC'yi ≈ 0,41'e çekme yan etkisi var; mutlak AUC yerine permütasyon p ve avantaj esas alınmalı.
- Latency kanalı güvenilir değil (tek GPU, ısınma/sıra etkileri); runner sırayı karıştırarak etkiyi dağıtıyor.

## 11. Sıradaki adım
1. Makalenin gözden geçirilmesi (kullanıcı): metni okumak, Overleaf'te derleyip **sayfa sayısını** (5–5,5) kontrol etmek, kaynakça `[TODO]` künyelerini yayıncı sayfasından tamamlamak, en az 5 dergi makalesinin (2024 sonrası) gerçekten dergi olduğunu doğrulamak.
2. Teslim: makale PDF'i Ninova'ya, son tarih **06.12.2026**. Sunum için son tarih 22.12.2026; sunum gönderilmez, sınıfta gösterilir (en çok 8 sayfa, 6 dk anlatım + 4 dk soru).
3. Açık teknik işler (zorunlu değil): daha çok konu (ör. 40) ve tekrar; ticari model (API anahtarı yok; DeepSeek bulut modeli denemesi plan hatası verdi, bkz. 13); kimlik doğrulamalı izolasyon; farklı "sır" politikaları.

## 12. Makale, sunum ve teslim durumu
**Makale** (`docs/makale/`): `main.tex` (IEEEtran, conference). Başlık, abstract (137 kelime), keywords, Introduction, Related Work, "CanaryProbe" (önerilen çözüm), Analysis, Conclusion ve 14 kaynak. Metin AI desteğiyle yazıldı; ödev PDF'inde AI yasağı yazıyor ama kullanıcı, hocanın AI desteğine izin verdiğini bildirdi (bu onayın yazılı kaydı kullanıcıda saklanmalı). `verify_numbers.py` makaledeki ~100 sayıyı `results/` dosyalarından yeniden hesaplıyor (uyuşmazlık: 0). `kaynak_adaylari.md`: okunacak kaynaklar; `deney_sayilari.md`: sayı ve kaynak dosya eşlemesi. Henüz derlenmedi (yerelde LaTeX yok); künyeler `[TODO]`.
**Sunum** (`docs/sunum/`): `presentation.pptx` (8 slayt, İngilizce, konuşmacı notları dahil; sırayla kapak, problem, ACL ve fark, tasarım, bulgular (neden AUC dahil), maskeleme, savunmalar, zorluklar ve sonuç). Uzun sürüm: `presentation_full19.pptx`; web kaynağı: `deck.json` + `slides/`. Üretim: `build_pptx.py` (python-pptx).
**Rapor:** `docs/proje_raporu.html` (Türkçe, diyagramlı, sıfırdan anlatım + sık sorulan sorular + karar günlüğü), `docs/soru_cevap_hazirlik.md` (olası sorular ve cevaplar).

## 13. Karar günlüğü ve operasyonel notlar
**Önemli kararlar ve nedenleri**
- *8 → 20 konu:* pilotun gücü düşüktü; 12 konu eklendi (18 belge, 120 mesaj).
- *Sabit lojistik regresyon:* sonuç "iyi ayarlanmış model" değil, "sinyal var" olsun diye.
- *LOTO hatası:* dengeli konu etiketlerinde kesişim terimi etiketle ters ilişkili skor üretiyordu (AUC 0,0); `class_weight="balanced"` ile giderildi; karar ölçütü mutlak AUC değil permütasyon p.
- *Kanal-açık ölçütü* (önceden sabit): permütasyon p < 0,05 ve AUC alt sınırı > 0,5.
- *Maskeleme analizi (6.x)* sinyalin kelimeden değil üslupten geldiğini gösterdi; önceki "içerik sızıntısı" yorumu geri alındı.
- *Fayda ölçümü Faz 6'da zorunlu:* yalnızca çözüm oranına bakılsaydı scoped_context bedelsiz görünürdü.
- *Pilot → "ek çalışma":* ana çalışmaya ek olduğu için sunumda böyle adlandırıldı; X0 ayrıca koşulmadı (X2'de B'nin hafızası boş, X0 ile aynı).
- *Maskeleme:* oracle (üst sınır, sızıntı yapı gereği 0) ve rule (dondurulmuş regex) birlikte; sır tanımı tek yazarlı politika kararı (`data/probes/secret_spans.json`); onaylı-cümle seti (`utility_conf.json`) mevcut fayda setindeki gizli kaynak eksikliğini kapatıyor.
- *Sunum 19 → 8 slayt:* ödev sınırı (en çok 8 sayfa).

**Operasyonel sorunlar ve çözümleri**
- *Ollama bellek şişmesi* (`llama-server` ~9 GB, 15,7 GB RAM, takas yok): koşu kısa parçalara bölündü (40 → 20 → 10 çağrı), parçalar arası model boşaltıldı, Ollama yeniden başlatıldı; >20 sn gecikmeli (thrash) satırlar silinip yeniden koşuldu.
- *Tekrar döngüsü:* modelin sonsuz üretimi koşuyu kilitledi; ajan çağrısına `max_tokens=700` eklendi ve Ollama sunucu iptali başarısız deneme sayıldı (önceki koşuları etkilemez).
- *Doğrudan sorularda `message_id` çakışması:* aynı konudaki iki soru aynı kimliği alıyordu; varyant indeksiyle düzeltildi, dört koşul yeniden koşuldu.
- *Gecikme özelliği güvenilmez* (pil/performans profili, CUDA düşmesi, bellek baskısı); makalede ve sunumda zayıf kanıt sayıldı.

**Bilinen açık noktalar**
- DeepSeek `deepseek-v4.1-flash:cloud`: kullanıcının terminalinde çalıştığı bildirildi, ancak yerel Ollama servisi benim çağrımda "Free plan" hatası verdi; test edilmedi. Veri bulut servise gideceği için ayrıca onay gerekir.
- Makale kaynakçasında dergi/venue doğrulaması kullanıcıda.

## 14. Dosya haritası (kısa)
- Kod: `src/data_layer/`, `agent/`, `probes/`, `features/`, `decoders/`, `experiments/`, `defenses/` (maskeleme dahil), `multiuser/`; testler `tests/` (51 birim test).
- Veri: `data/canaries/`, `data/probes/` (probes, direct_queries, utility_queries, secret_spans, utility_conf), `data/xuser/shares.json`.
- Sonuçlar: `results/*.csv|md|json`, ham loglar `results/runs/*.jsonl`, şekiller `results/figures/`.
- Planlar: `plans/` (faz2, faz6, pilot, maskeleme). Çıktılar: `docs/`.
- Tüm faz komutları ve sonuç tabloları bu raporun ilgili bölümlerinde.
