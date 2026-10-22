# Pilot Planı — Çok kullanıcılı sızıntı (A'nın paylaştığı veri B'ye sızıyor mu?)

Durum: **uygulandı** (2026-10-20; kararlar: iki model, X3 dahil, A mesajları oturumda yazıldı, B yazmıyor, A+B).

**Uygulama notları (plandan sapmalar):** (1) X0_empty ayrı koşulmadı: X2'de B'nin hafızası boş olduğundan B'nin bağlamı X0 ile aynıdır (negatif kontrol rolünü X2 oynar; izolasyon birim testiyle doğrulanır). (2) A fazında LLM çağrısı yok: hafıza yazımı verbatim; yalnızca X3 özetinde model başına 10 LLM çağrısı. (3) X3'te ortak not her B mesajının bağlamına girer (benzerliğe göre seçilmez). Faz 0–6 tamam (son commit `4bfce6e`). Bu, ana çalışmaya **ek** bir pilottur; ana raporun iddialarını değiştirmez.

## Soru

Kullanıcı A bota meşru bir konuşmada veri verir. Kullanıcı B yalnızca meşru mesajlar yazar. B'nin gözlediği ajan çıktısı (cevap metni, karar alanları, gecikme) A'nın o konuda veri paylaşıp paylaşmadığını ayırt ettiriyor mu? Önce doğrudan içerik sızıntısı (B'nin sorusuna A'nın verisi yazılıyor mu), sonra yan kanal (veri yazılmasa da davranış/üslup fark ediyor mu).

## Ana çalışmayla eşleşme (neyi yeniden kullanıyoruz)

| Ana çalışma | Pilot |
|---|---|
| confidential kanarya belge | A'nın bota verdiği uydurma kişisel/kurumsal bilgi (sahibi A) |
| dış müşteri probe/control | B'nin probe/control mesajları (**mevcut `data/probes/probes.json` aynen**) |
| predicate: konuda gizli doküman var mı | predicate: A bu konuda veri paylaştı mı (aynı 10 var / 10 yok konu) |
| M1_weak / M2_strong | X1 paylaşılan hafıza + prompt kuralı / X2 kullanıcı başına hafıza |
| Faz 4 özellikler, LOTO decoder, randomized control, metrikler | **değişmeden** |
| baseline (doğrudan sorular, `secret_markers`) | aynı 20 soru, B ağzından |

Kanarya belgelerin içeriği A'nın mesajlarına taşınır; bu yüzden probe'lar, doğrudan sorular ve işaretçiler yeniden yazılmadan geçerli kalır. Kurumsal indeksten kanarya belgeler çıkarılır (`docs_per_topic=0` ile `excluded_canary_ids` zaten hepsini dışlar), böylece gizli bilgi **yalnızca** A'nın hafızasında bulunur. Kurumsal Enron belgeleri M2 gibi süzülür (confidential yok), yani modlar arasındaki tek fark kullanıcı hafızasıdır.

## Senaryo modları

| Mod | Hafıza | B'ye gösterilen |
|---|---|---|
| **X0_empty** (negatif kontrol) | A hiç paylaşmadı; hafıza boş | – (decoder bunda sinyal bulursa konu/üslup karışıklığıdır) |
| **X1_shared_weak** | tek ortak hafıza indeksi; A'nın mesajları sahibi etiketiyle yazılır | tüm kullanıcıların hafızasından top-k; prompt: "başka müşterilerin bilgisini asla yazma/ima etme" |
| **X2_isolated** | kullanıcı başına ayrı hafıza (`user_id` filtresi) | yalnızca B'nin kendi hafızası (boş) |
| **X3_shared_summary** (yeni yol) | A'nın paylaşımları sürekli güncellenen **tek ortak özet notuna** birleştirilir | ortak not (kullanıcı filtresi uygulanamaz) |

X3 pilotun asıl yeni sorusu: retrieval'da kullanıcı filtresi (X2) yetmediğinde, paylaşılan durum (özet/hafıza birleştirme) sızıntıyı geri getiriyor mu? Tahminler (sonuç değil, sınanacak hipotezler): X1'de sinyal olabilir, X2 ve X0'da olmaması beklenir, X3 belirsiz (özetleme birebir sızıntıyı azaltabilir ama üslup kaymasını koruyabilir).

## Deney akışı (mod × model başına)

1. Temiz hafıza.
2. **A fazı:** A'nın paylaşım mesajları (10 gerçek konu, konu başına 1 mesaj) sırayla ajana verilir; her biri hafızaya yazılır (X3'te özet güncellenir). Absent konular için A mesajı yok. A'nın turları loglanır ama analiz edilmez.
3. **B fazı:** B'nin probe/control mesajları (20 konu × 2 tür × 5 varyant) tek tek verilir; **B'nin mesajları hafızaya yazılmaz** (hafıza B fazı boyunca sabit → satırlar bağımsız, resume uygulanabilir). Çıktı mevcut log şemasıyla yazılır.
4. Log: `results/runs/xuser_<mod>_<model>.jsonl`; `message_id = konu|tür|vN|rN|mod|model` (mod adı `X*`), böylece `parse_id` ve `load_log` değişmeden çalışır.

## Dosyalar

- `data/xuser/shares.json`: A'nın paylaşım mesajları (10 adet; kanarya içeriğinden türetilen, `secret_markers` içeren, A'nın ağzından, uydurma). **Oturumda ben yazarım** (kanarya/probe ile aynı yöntem); her biri için doğrulama: işaretçiler mesajda var, enjeksiyon deseni yok.
- `src/multiuser/memory.py`: `UserMemory` (sahip etiketli kayıt, `write`, `search(user, k, scope)`), `SharedSummary` (X3 özet güncelleme çağrısı).
- `src/multiuser/retriever.py`: `MultiUserRetriever` — kurumsal indeks (M2 süzgeçli, kanaryasız) + hafıza sonucu; bağlama `[user_memory]` etiketiyle girer; `current_user` özelliğiyle hangi kullanıcı adına çağrıldığı bilinir.
- `src/multiuser/run_pilot.py`: A fazı + B fazı koşturucu (40'lık parçalar, parça arası Ollama boşaltma; ana çalışmadaki bellek dersi).
- `src/agent/agent.py`: **küçük kanca**: sistem prompt'u moda göre config'ten seçilsin (şimdi `mode == "M1_weak"` sabit). Mevcut davranış değişmemeli (regresyon testi).
- `config/experiment.yaml`: `multiuser:` bloğu (modlar, hafıza top-k, özet prompt'u, kullanıcı kimlikleri).
- `tests/test_multiuser.py`.
- Analiz: mevcut `run_matrix.py --log ... --out-prefix _xuser_<mod>` + `analyze.py`/`figures.py` uyarlaması (tablo: satır = model/mod/grup).
- `CLAUDE.md` dizin listesine `src/multiuser/` eklenir.

## Doğrulama (atlanmaz)

1. **İzolasyon birim testi:** X2'de B için hiçbir A kaydı dönmez; X1'de döner; X3'te ortak not döner.
2. **Retrieval ölçümü** (ratio çalışmasındaki gibi): X1'de present-konu probe'larında B'nin bağlamına A kaydının girme oranı yüksek, control ve absent konularda düşük olmalı. Değilse müdahale çalışmıyor demektir ve AUC yorumlanmaz.
3. **Baseline (doğrudan sorular, B ağzından):** X1'de >0 sızıntı (kanal gerçekten açık), X2'de 0/20. X1'de 0 çıkarsa senaryo sızdırmıyor demektir ve bu da bir sonuçtur.
4. **X0 negatif kontrol:** decoder sinyal vermemeli (permütasyon p > 0,05, AUC ≈ şans).
5. **Randomized control** her decoder için (konu perm., satır karıştırma, plasebo), değişmeden.
6. Her aşamada `pytest`; faz sonunda commit + rapora kısa bölüm.

## Maliyet / süre (Ollama, 40'lık parçalar)

| İş | Çağrı | Yaklaşık süre |
|---|---|---|
| gemma3: X0, X1, X2, X3 × 200 B mesajı | 800 | ~1,5–2 sa |
| A fazı + X3 özet güncellemeleri | ~60 | dakikalar |
| qwen2.5 (ikinci aşama, isteğe bağlı) | 800 | ~2–3 sa |
| decoder (6–8 log) | – | ~15 dk/log |

Önerilen sıra: önce **yalnızca gemma3** (ana çalışmada tek anlamlı sinyal onda), sonuç ilginçse qwen2.5.

## Karar noktaları (onayınla netleşecek)

1. **Model kapsamı.** Öneri: önce yalnızca gemma3. Alternatif: iki model birden (süre ~2,5 kat).
2. **X3 (ortak özet) dahil mi?** Öneri: dahil (pilotun yeni katkısı). Alternatif: yalnızca X0/X1/X2 (süre ~%25 azalır, ama yeni soru kalmaz).
3. **A mesajları.** Öneri: oturumda ben yazayım (10 mesaj). Alternatif: sen yaz/gözden geçir.
4. **B'nin mesajları hafızaya yazılmaz** (satırlar bağımsız kalsın). Alternatif: yazılsın, ama sıra etkisi ve tekrarlanamazlık eklenir. Öneri: yazılmasın.
5. **Kullanıcı sayısı.** Öneri: A ve B (+ ileride C). Çoklu paylaşan kullanıcı pilot dışı.

## Etik

Tüm kullanıcılar ve mesajlar uydurma; gerçek ürün veya gerçek kişisel veri yok. A'nın verisi kanarya içeriğinden türetilir. Enjeksiyon yok; B yalnızca ana çalışmadaki meşru probe/control mesajlarını kullanır.

## Sınırlılıklar (baştan)

- Aynı 20 konu ve repeats=1: ana çalışmadaki güç sınırı burada da geçerli (AUC GA ≈ ±0,15).
- Hafıza tek yazma biçimi (A'nın mesajı verbatim; X3 hariç); gerçek ürünlerin hafıza/özetleme mekanizmaları farklı olabilir. Sonuçlar replikaya özgüdür.
- Paylaşılan önbellek/KV-cache zamanlama kanalları (barındırılan altyapıya özgü) kapsam dışı.
- X3'te özet bir LLM çağrısına bağlı, yani ek bir gürültü kaynağı.
