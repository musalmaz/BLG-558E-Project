# Maskeleme Planı — Span düzeyinde maskeleme savunması (M1_weak üzerinde)

Durum: **uygulandı** (2026-10-24; önerilen kararlarla: oracle+rule, M1 promptu, gemma3+qwen2.5, veri Claude tarafından). Faz 0–6 ve çok kullanıcılı pilot tamam (son commit `4a1150a`). Bu, Faz 6 savunma ailesine eklenen **dördüncü savunmadır**; mevcut sonuçları değiştirmez.

## Soru

M2 (retrieval'da süzme) gizli belgeyi tamamen atıyor ve bedel ödüyor (gemma3 çözüm oranı 0,92 → 0,67). Gizli belge **bağlamda kalır ama yalnızca hassas parçaları maskelenirse**: (1) sır sızıntısı kapanır mı, (2) metin üslubu kanalı (M1'de gemma3 AUC 0,82) kapanır mı, (3) cevap kalitesi M2 ve scoped_context'ten iyi mi?

## Hipotezler (ölçülecek, sonuç değil)

- **H1 (güvenlik, içerik):** Oracle maskeleme işaretçi sızıntısını sıfırlar (yapı gereği, bir doğrulama kontrolüdür). Kural tabanlı maskeleme sıfırlamaz, kaçıran bir miktar kalır.
- **H2 (güvenlik, yan kanal):** Maskelenmiş belge yine de *varlığını ve üslubunu* taşır; metin kanalı M1'e göre düşer ama M2 düzeyine **inmeyebilir**. Bu planın asıl bilimsel sorusu.
- **H3 (fayda):** Gizli konunun *sır olmayan* yönlerine (projenin ne olduğu, kimin ilgilendiği) cevap kalitesi M2 ve scoped_context'ten yüksek, M1'e yakın.

## Maskeleyiciler (iki tane, ikisi de aynı arayüz)

`src/defenses/masking.py`: `mask(text, kind) -> str` ve `MaskedRetriever` (M1_weak gibi gizli belgeleri getirir, **bağlama koymadan önce** yalnızca `acl_label == "confidential"` parçalarını maskeler; public/internal dokunulmaz).

1. **`oracle`:** konu başına elle yazılmış *sır aralıkları* listesi (`data/probes/secret_spans.json`) birebir `[GİZLİ]` ile değişir. Mükemmel kapsamlı maskelemenin **üst sınırı**; sızıntı garantidir, deney yalnızca faydayı ve yan kanalı ölçer.
2. **`rule`:** gerçekçi, genel kurallar: sayılar/para/yüzde, tarih ve saatler, e-posta/telefon, çok sözcüklü büyük harfli özel adlar. Tür etiketli yer tutucu (`[NUM]`, `[DATE]`, `[NAME]`). **Kurallar çalıştırmadan önce dondurulur**, işaretçilere göre ayarlanmaz (aksi halde sızıntı ölçümü dairesel olur). Bağımlılık eklemeden (regex), spaCy yok.

Not: kural maskeleyici sır olmayan adları da (ör. "Veltrix Holdings") maskeler. Bu istenen bedeldir ve fayda ölçümünde görünür.

## Veri (yeni, elle yazılacak, uydurma)

- **`data/probes/secret_spans.json`:** 10 mevcut konu için sır aralıkları (mevcut `direct_queries.json` işaretçileri + belgelerdeki diğer sayısal/tarihsel ayrıntılar). *Sır olmayan* aralıklar ayrıca etiketlenir.
- **`data/probes/utility_conf.json`:** 10 mevcut konu için 1'er (isteğe 2) **sır olmayan** soru ("Project Falcon nedir / hangi aşamada?" tipi) ve cevap işaretçileri. Mevcut 23'lük fayda setinde gizli kaynak yok (14 public, 9 internal), bu yüzden M2/maskeleme farkı onunla görünmez; bu set tam bu boşluğu kapatır.
- Hangi bilginin "sır" sayıldığı bir **politika kararıdır**; `secret_spans.json` bu politikayı açıkça yazar ve raporda belirtilir.

## Koşullar

Sabit prompt: **M1_weak promptu** (yasak kuralı kalır), böylece M1 ile fark yalnızca bağlam içeriğidir. Karşılaştırma satırları:

| satır | kaynak |
|---|---|
| none (M1) | mevcut `def_none` |
| M2 | mevcut referans |
| scoped_context | mevcut |
| **mask_oracle** | yeni |
| **mask_rule** | yeni |

Modeller: gemma3, qwen2.5 (DeepSeek bulut erişimi çözülene kadar kapsam dışı).

## Deneyler

1. **Güvenlik (içerik):** 20 doğrudan soru × 2 model × 2 maskeleyici (80 çağrı) + ana probe matrisinde cevaplardaki işaretçi oranı.
2. **Güvenlik (yan kanal):** ana probe matrisi (200 mesaj × 2 model × 2 maskeleyici = 800 çağrı) → mevcut Faz 4 decoder'ları, aynı randomized control'lerle, `behavior_nolat/behavior/text/behavior+text`. Başarı ölçütü Faz 6 ile aynı: text AUC, permütasyon p, kanal-açık.
3. **Fayda:** (a) mevcut 23'lük set (maskeleme sır olmayan public/internal belgeleri etkilememeli, yan etki kontrolü), (b) yeni `utility_conf` seti (sır olmayan soruya cevap işaretçisi geri çağrısı), (c) kontrol mesajlarında çözüm oranı ve yönlendirme uyumu (`quality.py`).
4. **Güvenlik-fayda figürü:** mevcut `security_utility.png`'ye iki nokta eklenir (x: fayda kaybı, y: text AUC ve işaretçi sızıntısı).

Tahmini maliyet: ~1100 çağrı (≈2,5 saat, Ollama bellek şişmesi nedeniyle 10'luk parçalar, `max_tokens=700` sınırı kalır) + decoder ≈ 40 dk.

## Doğrulama adımları (atlanmaz)

1. Birim testler: `mask_oracle` her sır aralığını çıkarır ve başka metne dokunmaz; `mask_rule` deterministik; public/internal parçalar değişmez; `MaskedRetriever` M1 ile aynı belge kimliklerini getirir (yalnızca metin farklı).
2. Duman testi: 3 konu, 1 model, 20 çağrı; log şeması Faz 6 logları ile aynı (`load_log` çalışır).
3. **Oracle sanity:** mask_oracle'da işaretçi sızıntısı 0 olmak zorunda; değilse maskeleme veya liste hatalıdır, devam edilmez.
4. Randomized control (konu-permütasyon, satır karıştırma, plasebo) her decoder için zorunlu; `channel_open` ölçütü değişmez.

## Riskler ve sınırlar

- **Sır tanımı:** "sır" aralıklarını ben (tek yazar) belirleyeceğim; farklı bir politika farklı sonuç verir. Rapor bunu belirtir.
- **Dairesellik:** oracle'ın sızıntıyı sıfırlaması bir sonuç değildir. Kural maskeleyici değerlendirmesi dürüst olsun diye kurallar dondurulur, işaretçiler maskeleyiciden saklanır.
- **Ölçek:** 10 konu, 5 varyant, tek tekrar; iki yerel model. H2/H3 için fark küçükse anlamlı çıkmayabilir, bu durumda "ayrışmıyor" diye raporlanır.
- **Maskeleme belge varlığını gizlemez:** `[GİZLİ]` yer tutucuları bile modelin davranışını etkileyebilir; bu H2'nin konusu, kusur değil.
- Ollama bellek sorunu (bilinen): parça boyutu 10.

## Sonuçların raporlanması

`docs/ilerleme_raporu.md` Faz 6 bölümüne alt başlık olarak (savunma tablosu + figür güncellemesi), `docs/rapor_taslagi.md` savunmalar kısmına bir paragraf. Ayrı bir faz numarası açılmaz.

## Onay bekleyen kararlar

1. Maskeleyici: **oracle + rule ikisi birden** (önerilen) / yalnızca rule.
2. Prompt: **M1 promptu korunur** (önerilen) / M2 promptu.
3. Modeller: **gemma3 + qwen2.5** (önerilen); DeepSeek/llama3.1 sonraya.
4. Sır olmayan fayda soruları ve sır aralıkları **benim tarafımdan yazılsın** (önerilen).
