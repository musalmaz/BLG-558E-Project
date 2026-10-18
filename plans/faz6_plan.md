# Faz 6 Planı — Savunmalar ve güvenlik-fayda eğrisi

Durum: **onay bekliyor** (2026-10-18). Faz 0–5 tamam (son commit `07749fb`).

## Hedef

Faz 5'te ölçülen sızıntıyı (M1_weak'te gemma3 metin/üslup kanalı, AUC ≈ 0,82; davranış
kanalı ≈ şans) üç savunmayla kapatmaya çalışmak ve her savunmanın **AUC düşüşünü** ile
**cevap kalitesi kaybını** birlikte raporlamak. Çıktı: tek figürde güvenlik-fayda eğrisi.

## Önemli gözlem (tasarımı belirliyor)

Faz 5'te sinyal karar alanında (eskalasyon, ret türü, yönlendirme) değil, **cevap metninin
üslubunda** ("we/our", jenerik özür, iletişim bilgisi). Bu yüzden:
- `behavior_norm` ve `decision_hiding` karar/ret/gecikme alanlarını düzeltir; metin
  üslubunu **kendiliğinden** kapatmaz. Bu beklenti bir sonuç değil, ölçülecek bir hipotezdir:
  bu iki savunmanın metin grubunda AUC'yi düşürmemesi mümkün.
- `scoped_context` bağlamı kaynağında kestiği için metin kanalını da kapatması beklenir
  (M2'de sinyal yok), ama bedeli fayda kaybıdır.

## Mimari

Savunmalar ajanın etrafında **sarmalayıcı** olarak çalışır; `src/agent/` değişmez
(yalnızca gerekirse `AgentRunner`'a küçük bir kanca). Config'e yeni blok:

```yaml
defenses:
  names: [none, behavior_norm, scoped_context, decision_hiding, all]
  latency_pad_ms: <sabit, ölçülen p95 üstü>
  templates: {refusal: "...", escalate: "..."}
```

Her savunma kendi logunu yazar (`results/runs/defense_<ad>.jsonl`) ve **aynı şemada**
olduğu için Faz 4 özellik/decoder hattı (`load_log` → `run_decoders`) olduğu gibi çalışır.
Ham gecikme `latency_raw_ms` alanında saklanır, `latency_ms` savunmadan sonraki değerdir.

## Dosyalar

### 1. `src/defenses/behavior_norm.py`
- Çıktı tarafı: `refusal_type != none` ya da `escalated` ise `answer_text` sabit şablonla
  değiştirilir; `no_info`, `cannot_share`, `deflect` **tek** türe indirgenir
  ("bilmiyorum" ile "söyleyemem" ayırt edilemez).
- Yalnızca loglanmış çıktının fonksiyonu → mevcut M1 logları üzerinde **ek LLM çağrısı
  olmadan** çevrimdışı uygulanabilir.

### 2. `src/defenses/scoped_context.py`
- Dış göndericiye cevap veren ajan yalnızca `public` kaynağı görür (retrieval filtresi
  `acl_label == public`; M2'den daha sıkı: internal de dışarıda). CaMeL'in ayrıcalıklı/
  karantina ayrımının e-postaya uyarlaması: yetkili bağlam dış mesajla hiç buluşmaz.
- Yeni LLM koşusu gerekir (modeller × 20 konu × 5 varyant × probe/control).

### 3. `src/defenses/decision_hiding.py`
- `routing_target` ve `escalated` bağlamdan bağımsız üretilir: yalnızca **müşteri mesajından**
  (bağlamsız ikinci çağrı; mesaj başına bir kez, önbellekli) → karar bağlamdaki gizli
  belgeye bağlı olamaz.
- Gecikme sabitlenir (`latency_pad_ms`'e tamamlama) ve cevap türü sabit şablona eşlenir.
- Bağlamsız yönlendirme çağrısı yeni LLM çağrısı gerektirir (≈ mesaj başına 1).

### 4. `src/defenses/evaluate_defenses.py`
- Matris: savunma ∈ {none, behavior_norm, scoped_context, decision_hiding, all} ×
  model ∈ {gemma3, qwen2.5} × ACL = **M1_weak** (savunmanın korunduğu zayıf yapılandırma;
  M2 referans nokta olarak Faz 5'ten alınır). `all` = üçü birden.
- Her hücre için Faz 4 decoder'ı (**randomized control dahil**, değişmeden).
- Ölçümler:
  - **Güvenlik:** AUC (text, behavior, behavior+text), TPR@1%FPR, sızan bit, konu perm. p;
    Δ = AUC(none) − AUC(savunma).
  - **Fayda (kalite proxy'si):**
    (a) *çözüm oranı* = control mesajlarında `refusal_type == none` ve `escalated == false`
    olan cevap payı (mevcut loglardan, ek veri gerekmez);
    (b) *recall* = fayda setindeki sorularda cevapta beklenen işaretçinin geçme oranı
    (aşağıdaki "Karar noktaları" bkz.).
- Çıktılar: `results/defense_results.csv`, `results/defense_table.md`.

### 5. `src/defenses/figures.py`
- Güvenlik-fayda eğrisi: x = kalite kaybı (çözüm oranı / recall düşüşü), y = AUC;
  her savunma bir nokta (model başına işaretçi/panel), `none` ve M2 referans noktaları
  işaretli, şans çizgisi (0,5) kesikli. `results/figures/security_utility.png`.

### 6. Testler (`tests/test_defenses.py`)
- `behavior_norm`: üç ret türü aynı çıktıyı verir; ret olmayan cevap değişmez.
- `scoped_context`: dönen tüm chunk'lar `public`; kanarya belge hiç gelmez.
- `decision_hiding`: aynı mesaj için bağlam değişse de `routing_target`/`escalated` sabit;
  gecikme sabit.
- Sahte LLM ile uçtan uca: savunma logu Faz 4 `load_log` şemasını geçer.

## Doğrulama (atlanmaz)

1. Her savunma için AUC düşüşü ve kalite kaybı **birlikte** raporlanır.
2. `scoped_context` sızıntıyı en çok kapatan, ama kalite kaybı da olan savunma çıkmalı
   (planın beklentisi; çıkmazsa bunu açıkça yazarız).
3. Randomized control satırları şansa yakın kalmalı (her hücrede).
4. Güvenlik-fayda eğrisi tek figürde.
5. Her adımda `pytest`; faz sonunda git commit + rapora Faz 6 bölümü.

## Maliyet / süre (gemma3+qwen2.5, Ollama, bellek için 40'lık parçalar)

| İş | Yeni çağrı | Yaklaşık süre |
|---|---|---|
| behavior_norm (çevrimdışı) | 0 | dakikalar |
| scoped_context | 2 model × 200 = 400 | ~50 dk |
| decision_hiding (bağlamsız yönlendirme) | 400 | ~50 dk |
| all (scoped üstüne çevrimdışı + bağlamsız yönlendirme önbelleği) | ≈ 0 | dakikalar |
| Fayda seti (varsa) | 2 model × 3 mod × ~30 soru | ~30 dk |

## Karar noktaları (onayınla netleşecek)

1. **Fayda ölçüsü.** Öneri: çözüm oranı (ek veri yok) **+** küçük bir fayda seti
   (~30 meşru soru; cevabı public/internal Enron belgelerinde geçen işaretçiyle) — setin
   oturumda ben yazmamı öneririm. Yalnızca çözüm oranı yeterliyse set atlanır ve süre azalır.
2. **`scoped_context` kapsamı.** Öneri: yalnızca `public` (M2'den sıkı, fayda kaybı görünür
   olsun). Alternatif: public+internal (M2 ile aynı; yeni bilgi vermez).
3. **`decision_hiding` yönlendirmesi.** Öneri: bağlamsız LLM çağrısı (gerçekçi). Alternatif:
   anahtar-kelime tabanlı deterministik yönlendirici (ücretsiz ama kalite proxy'si bozulur).
4. **Tekrar.** repeats=1 (Faz 5 ile tutarlı). AUC GA yarı genişliği ≈ 0,15 olduğundan küçük
   savunma farkları ayrışmayabilir; repeats=2 süreyi ikiye katlar.

## Sınırlılıklar (baştan)

- AUC düşüşü gürültü içinde kalabilir (20 konu); p ve sızan bit birlikte raporlanacak.
- Sızıntının asıl taşıyıcısı yalnızca gemma3-M1 metin kanalı; qwen2.5'te savunma etkisi
  ölçülecek sinyal olmadığından belirsiz kalır.
- Kalite proxy'leri kaba; gerçek müşteri memnuniyetini ölçmez.
