# Proje: Dış AI hizmet ajanlarında davranışsal yan kanal sızıntısı
- Amaç: ajan gizli içeriği yazmasa bile davranışının o içeriğin varlığını
  sızdırıp sızdırmadığını ölçmek. Enjeksiyon YOK, sadece meşru mesajlar.
- ETİK: deneyler SADECE kendi replika ortamında + Enron (kamuya açık) +
  uydurma kanarya veriyle. Gerçek üründe / gerçek kişisel veriyle test YOK.
- Her faz bitince git commit. Her fazın bir doğrulama adımı var, atlanmaz.
- Metrikler sabit: AUC, TPR@1%FPR, gereken mesaj sayısı, sızan bit.
- Randomized control her decoder için zorunlu.

## Ortam
- Proje venv'i: `.venv` (`source .venv/bin/activate`), kurulum: `pip install -e .`
- API anahtarları `.env`'de (repoda değil); örnek: `.env.example`.
- Konfigürasyon: `config/experiment.yaml`.

## Dizin yapısı
- `src/data_layer/` Faz 1: yükleme, ACL etiketleme, kanarya, indeks
- `src/agent/` Faz 2: retrieval + LLM + karar + log (M1_weak / M2_strong)
- `src/probes/` Faz 3: probe/kontrol üretimi + runner + baseline check
- `src/features/` Faz 4: davranışsal + metinsel özellikler
- `src/decoders/` Faz 4: istatistik testi, sınıflandırıcı, randomized control
- `src/experiments/` Faz 5: matris koşturucu + analiz
- `src/defenses/` Faz 6: savunmalar + güvenlik-fayda
- `data/{raw,labeled,canaries}`, `results/`, `tests/`

## Kod stili
- Python >=3.10, type hint kullan, kısa docstring. Kod ve değişken adları İngilizce.
- Küçük başla: önce 3-4 kanarya, tek model, az tekrar ile duman testi.
