# İlerleme Raporu — Dış AI ajanlarında davranışsal yan kanal sızıntısı

Son güncelleme: 2026-10-17 · Tamamlanan fazlar: 0, 1, 2, 3 (kod) · Sıradaki: Faz 4

## 1. Faz özeti

| Faz | İçerik | Durum | Commit |
|---|---|---|---|
| 0 | İskelet, ortam, config | Tamam | `5108fb1` |
| 1 | Veri katmanı: Enron yükleme, ACL etiketleme, kanarya, Chroma indeksi | Tamam | `c56c8a0` |
| 2 | Ajan boru hattı: retrieval (M1/M2) + LLM + yapılandırılmış karar + log | Tamam | `05a3747` |
| 3 | Probe/control seti, runner, baseline check | Kod tamam, tam matris koşusu sürüyor | `1473694` |

## 2. Veri (Faz 1)
- 2012 doküman (2000 Enron + 12 elle yazılmış kanarya), 7502 chunk.
- ACL dağılımı: internal 1596, confidential 253, public 163.
- 8 kanarya konu: 4 gerçek (c00–c03, confidential dokümanlı, predicate=1), 4 uydurma (c04–c07, dokümansız, predicate=0).

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

## 5. Tam matris koşusu (repeats=1)
- Boyut: 8 konu × 2 tür × 5 varyant × 2 mod × 2 model = 320 çağrı (~55 dk, yerel).
- Gerekçe: `temperature=0` olduğundan ikinci tekrar karar bilgisi eklemez, yalnızca latency güvenilirliğini artırır.
- Sonuç: _koşu bitince doldurulacak_

## 6. Sınırlılıklar ve açık noktalar
- İki model de yerel/açık ağırlıklı; plandaki "biri ticari API" şartı API anahtarı olmadığı için karşılanmadı. Anahtar alınırsa config'e model eklemek yeterli.
- Kanarya ve probe metinleri tek yazar tarafından (Claude oturumunda) yazıldı; üslup çeşitliliği sınırlı.
- Küçük ölçek: 4+4 konu, 5 varyant. Ölçek artırımı Faz 5'te.
- Latency kanalı güvenilir değil (tek GPU, ısınma/sıra etkileri); runner sırayı karıştırarak etkiyi dağıtıyor.

## 7. Sıradaki adım
Faz 4: davranışsal + metinsel özellikler, istatistik testi, sınıflandırıcı, randomized control (plan modunda başlanacak).
