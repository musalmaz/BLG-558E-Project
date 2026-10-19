# Dış AI Hizmet Ajanlarında Davranışsal Yan Kanal Sızıntısı: Ölçüm ve Savunma Değerlendirmesi

*Taslak v0.1 — BLG 558E. Sayılar `results/` altındaki dosyalardan alınmıştır; yorumlar temkinlidir. `[...]` ile işaretli yerler henüz yazılmadı.*

## Özet

Dış müşterilere cevap veren ve iç dokümanlara erişen bir AI ajanı, gizli içeriği hiç yazmasa bile, davranışıyla (eskalasyon, ret türü, yönlendirme, gecikme) ve cevap üslubuyla o içeriğin varlığını sızdırabilir mi? Bunu yalnızca meşru müşteri mesajlarıyla, enjeksiyon olmadan; kendi replika ortamımızda, Enron e-posta verisi ve uydurma kanarya belgelerle ölçtük. İki yerel model (gemma3, qwen2.5:7b), iki ACL modu (M1_weak: gizli belgeler bağlama girer, yalnızca prompt yasaklar; M2_strong: gizli belgeler retrieval'da süzülür) ve 20 kanarya konusu (10'unda gizli belge var, 10'unda yok) kullandık.

Başlıca bulgular: (1) Yalnızca-davranış özellikleri hiçbir hücrede anlamlı sinyal vermedi; makalenin ana hipotezi bu ölçekte **desteklenmedi**. (2) gemma3 + M1'de **cevap metni** gizli belge varlığını ayırt ettirdi (konu düzeyi LOTO AUC 0,82, permütasyon p = 0,004); maskeleme sinyali ortadan kaldırmadı, sinyal sözcük içeriğinden çok üslup kaymasında. (3) M2'de hiçbir modelde sinyal yok. (4) Üç savunma denendi; sinyali kapatan tek savunma bağlamı yalnızca public kaynaklara daraltan `scoped_context` oldu, ancak internal kaynaklı meşru soruların hiçbirinde cevap işaretçisi gelmedi (recall 1,00 → 0,00). Gizli belgeleri retrieval'da süzen M2 referansı benzer güvenliği çok daha küçük fayda kaybıyla sağladı.

## 1. Giriş

[Motivasyon: dış müşteri hizmetleri ajanları; iç veriye erişen ajanların sızıntı yüzeyi. Yan kanal sorusu: içerik yazılmasa da davranış sızdırır mı?]
[İlgili çalışma: prompt injection ve ajan sızıntısı, ajan yetki ayrımı (ör. CaMeL), LLM yan kanalları — **kaynakça henüz eklenmedi**.]

**Katkılar (iddia edilebilenler).** (i) Enjeksiyonsuz, yalnızca meşru mesajlarla çalışan bir ölçüm hattı ve randomized control zorunlu bir decoder protokolü. (ii) Davranış-yalnız sinyalin bu ölçekte bulunmadığına dair negatif sonuç. (iii) M1'de metin üslubu kanalının varlığı ve maskeye dayanıklılığı. (iv) Üç savunmanın güvenlik-fayda ölçümü.

## 2. Tehdit modeli ve etik

Saldırgan, ajanla meşru bir dış müşteri gibi yazışır; ajanın çıktısını (cevap metni, karar alanları, gecikme) gözler, enjeksiyon veya araç kötüye kullanımı yoktur. Hedef: belirli bir konuda gizli doküman olup olmadığı (1 bit/konu). Deneyler **yalnızca** replika ortamında, kamuya açık Enron verisi ve uydurma kanarya belgelerle yapıldı; gerçek ürün veya gerçek kişisel veriyle test yok.

## 3. Sistem ve veri

- **Veri:** 2000 Enron e-postası + elle yazılmış 30 kanarya belge; ACL: internal 1596, confidential 271, public 163. 20 kanarya konu: 10 gerçek (her biri 3 gizli belge), 10 uydurma (belgesiz).
- **Ajan:** retrieval (top-5, MiniLM embedding, ChromaDB) + LLM + yapılandırılmış karar (`escalated`, `refusal_type`, `routing_target`, `answer_text`), sıcaklık 0. M1_weak: her şey getirilir, prompt gizli içeriği yazmayı yasaklar. M2_strong: confidential retrieval'da süzülür.
- **Modeller:** `gemma3:latest`, `qwen2.5:7b` (yerel/açık ağırlıklı; ticari API modeli anahtar olmadığı için kullanılamadı).
- **Probe/control:** konu başına 5 varyant × {probe, control}; control aynı yapıda, konuyla ilgisiz; uzunluk farkı ≤ %25. Toplam 800 çağrı (20 konu × 2 tür × 5 varyant × 2 mod × 2 model), 0 parse hatası.

**Baseline (doğrudan sorular, 20 soru).** M2'de sızıntı 0/40; M1'de gemma3 16/20, qwen2.5 13/20. Yani M1 yan kanala gerek kalmadan doğrudan da sızdırıyor; bu bilinen zayıf-ACL açığıdır ve ayrıca raporlanır.

## 4. Yöntem

**Özellik grupları:** `behavior_nolat` (eskalasyon, ret türü, yönlendirme), `behavior` (+gecikme), `text` (uzunluk, 22 stilometri, PCA(5) embedding), `behavior+text`.
**Decoder:** sabit L2 lojistik regresyon (`class_weight="balanced"`, ayar yok); birincil değerlendirme leave-one-topic-out (LOTO).
**Metrikler (sabit):** AUC [%95 bootstrap GA], TPR@1%FPR, gereken mesaj sayısı, sızan bit.
**Randomized control (her decoder için):** konu-etiketi permütasyonu (500 Monte Carlo), satır düzeyi etiket karıştırma (100), control satırlarıyla plasebo decoder. "Kanal açık" = konu-permütasyon p < 0,05 **ve** AUC GA alt sınırı > 0,5.
**Yöntem notu:** LOTO + dengeli etiketlerde kesişim terimi şansın altına (≈ 0,4) AUC üretebiliyor; bu yüzden karar ölçütü mutlak AUC değil permütasyon p ve avantajdır.

## 5. Bulgular

### 5.1 Ana tablo ve M1 vs M2 (`results/main_table.md`, Şekil `auc_m1_vs_m2.png`)

| Model | Grup | AUC M1 (p) | AUC M2 (p) |
|---|---|---|---|
| gemma3 | behavior | 0,48 (0,46) | 0,46 (0,55) |
| gemma3 | text | **0,82 (0,004)** | 0,45 (0,56) |
| gemma3 | behavior+text | **0,78 (0,006)** | 0,48 (0,49) |
| qwen2.5 | behavior | 0,58 (0,18) | 0,45 (0,59) |
| qwen2.5 | text | 0,61 (0,13) | 0,42 (0,69) |

- **Davranış-yalnız:** 8 hücre grubunun hiçbirinde anlamlı sinyal yok (en küçük p = 0,18). Karar alanı neredeyse sabit: eskalasyon her satırda 0. qwen2.5-M1'de `cannot_share` yalnızca gizli belgeli konularda görüldü (10'a 0), ama permütasyon p ≥ 0,18 ve çoklu test düzeltmesi geçilmiyor; bu kanıt değil, takip edilecek bir ipucu.
- **gemma3 + M1 metin:** AUC 0,82 [0,75–0,91], 2 mesajda konu düzeyi AUC ≥ 0,9, sızan bit 0,12/mesaj.
- **M2:** hiçbir hücrede sinyal yok. Güç sınırlı: AUC GA yarı genişliği ≈ 0,15, küçük etkiler (AUC < ~0,65) dışlanamaz.

### 5.2 Metin sinyali nereden geliyor? (maskeleme)

Konu terimleri, rakamlar ve yalnızca gizli belgelerde geçen sözcükler maskelense de gemma3-M1 metin AUC'si 0,83 → 0,82 kaldı (p = 0,002). Fark üslupta: gizli bağlam varken cevaplar "we/our" (0,050 vs 0,017), "unfortunately" (0 vs 0,14) ve iletişim bilgisi içerme (0,06 vs 0,24) bakımından farklı. Bu karar alanı değil **metin üslubu** kanalıdır. Uyarı: keşifsel analiz, özellik başına düzeltme yok, tek model; kalan semantik sızıntı dışlanamaz. Ayrıca M1'de probe cevaplarının %24'ü (gemma3) gizli işaretçileri doğrudan içeriyor; yani kanalın bir kısmı düpedüz içerik sızıntısıdır.

### 5.3 Gizli belge sayısı taraması (`results/ratio_table.md`)

Konu başına gizli belge sayısı k ∈ {1,2,3}. Top-5 bağlamındaki gizli belge sayısı k ile monoton arttı (present probe: 1,9 / 2,5 / 3,3; kendi kanaryası geliş oranı %94–100), ama AUC monoton değil (gemma3 text 0,71 / 0,64 / 0,82; güven aralıkları örtüşüyor). "Oran arttıkça sızıntı artıyor/azalıyor" iddiası desteklenmiyor; yalnızca gemma3 metin sinyalinin k=1'de bile anlamlı olduğu (p = 0,012) söylenebilir.

### 5.4 Savunmalar (`results/defense_table.md`, Şekil `security_utility.png`)

Üç savunma M1_weak üzerinde, `none` Faz 5'i aynen yeniden üretecek şekilde ölçüldü.

| Savunma | gemma3 text AUC | gemma3 beh+text | qwen2.5 beh+text | Recall kaybı (g / q) | Yönlendirme uyumu |
|---|---|---|---|---|---|
| none | 0,82 | 0,78 | 0,61 | 0 / 0 | 1,00 |
| behavior_norm | 0,82 | 0,82 | 0,63 | 0,04 / 0 | 1,00 |
| scoped_context | **0,44** | **0,49** | 0,42 | **0,30 / 0,35** | 0,60 / 0,66 |
| decision_hiding | 0,82 | 0,84 | 0,54 | 0 / 0 | 0,61 / 0,64 |
| all | 0,51 | 0,54 | 0,45 | 0,30 / 0,35 | 0,61 / 0,64 |
| M2 referansı | 0,45 | 0,48 | 0,37 | 0,04 / −0,04 | – |

Fayda ölçüleri: çözüm oranı, savunmasız ajanla yönlendirme uyumu ve 23 soruluk (14 public, 9 internal kaynaklı) fayda setinde işaretçi recall'ı. `scoped_context`'te internal kaynaklı soruların recall'ı gemma3'te 1,00 → 0,00, qwen2.5'te 0,78 → 0,00; çözüm oranı ise değişmedi (0,93 / 0,99), yani ajan cevap veriyor ama bilgi içermiyor.

## 6. Tartışma: savunmalar işe yaradı mı?

- **`scoped_context`: gözlenen sinyali kapattı, bedeliyle.** Güvenlik açısından işe yaradı (text AUC 0,82 → 0,44, p = 0,63, sızan bit 0). Ancak bu, bağlamın gizli içerikten tamamen arındırılmasının beklenen sonucu; M2'den daha sıkı olduğu için gereksiz fayda kaybı getiriyor. M2 referansı benzer güvenliği ≤ 0,04 recall kaybıyla sağladı (M2'nin bedeli recall'da değil çözüm oranında: gemma3 0,92 → 0,67). Pratik çıkarım: asıl koruma confidential'ı retrieval'da kesmek; public-only kapsam bunun üstüne anlamlı bir şey katmıyor.
- **`behavior_norm` ve `decision_hiding`: etkisiz görünüyor, ama bu ikisi hakkında hüküm vermek için yeterli veri yok.** Gözlenen kanal metin üslubuydu; bu savunmalar karar alanlarını hedefliyor ve metin AUC'sini düşürmedi (gemma3 0,82 → 0,82). Daha önemlisi, davranış kanalında baştan ölçülebilir sinyal yoktu; dolayısıyla bu savunmaların davranış sızıntısını kapatıp kapatmadığı bu deneyde sınanamadı. `decision_hiding` ayrıca yönlendirme kalitesini düşürdü (uyum ~0,6).
- **Genel:** Savunma deneyi, "önlemler işe yaradı" demek için değil, "kapatılabilir tek kanal (metin üslubu/içerik) bağlam kaynağında kesilince kapanıyor, çıkış tarafı normalleştirmeler bunu kapatmıyor" demek için kullanılabilir.

## 7. Sınırlılıklar

- Ölçek: 10 + 10 konu, 5 varyant, repeats=1; AUC aralıkları geniş (≈ ±0,15), ±0,07'lik farklar anlamlı değil; çoklu test düzeltmesi yok.
- İki küçük yerel model; ticari API modeli yok. Sonuçlar daha güçlü modellere genellenemez.
- Kanarya ve probe metinleri tek yazarlı (oturumda yazıldı); üslup çeşitliliği sınırlı. Fayda seti 23 soru, işaretçi recall'ı kaba bir proxy; cevapların doğruluğu/uydurma olup olmadığı ölçülmedi.
- Konu kimliği ile predicate karışık olabilir (LOTO + plasebo azaltır, elemez).
- Gecikme kanalı güvenilir değil (tek GPU, ısınma/bellek baskısı); zayıf kanıt sayılmalı.
- M1'de doğrudan içerik sızıntısı var (baseline 16/20); "yan kanal" ile "içerik sızıntısı" tam ayrıştırılamadı.

## 8. Sonuç ve gelecek iş

Yalnızca-davranış yan kanalı bu ölçekte bulunamadı; M1'de ölçülen kanal esas olarak metin üslubu ve içerik sızıntısıdır ve M2 (retrieval'da süzme) onu kapatıyor. Gelecek iş: daha çok konu/tekrarla davranış ipuçlarını (özellikle qwen2.5-M1 ret türü) yeniden sınamak; daha güçlü ve ticari bir modelle tekrar; ajan promptunu daha çok ret/eskalasyon üretecek şekilde değiştirmek; savunmaların davranış kanalındaki etkisini sinyal varken sınamak; metin üslubu kanalı için çıkış tarafı normalleştirme.

## Ek: yeniden üretim

Ortam `.venv`; konfigürasyon `config/experiment.yaml`. Ana tablo: `python -m src.experiments.analyze`; k taraması: `python -m src.experiments.ratio`; savunmalar: `python -m src.defenses.evaluate_defenses {collect,build,evaluate}`. Ayrıntılı faz notları: `docs/ilerleme_raporu.md`.
