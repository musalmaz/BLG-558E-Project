# Faz 2 Planı — Ajan boru hattı

Durum: **plan, onay bekliyor** (2026-10-12). Faz 0 (`5108fb1`) ve Faz 1 (`c56c8a0`) tamam.

## Hedef

Dış müşteri e-postasına cevap üreten, ChromaDB'den iç veriye bakan ve her kararını
yapılandırılmış olarak loglayan ajan. İki ACL modu (M1_weak, M2_strong) tek koddan,
config'ten seçilir.

## Mevcut altyapı (Faz 1'den)

- ChromaDB: `data/chroma/`, koleksiyon `emails`, metadata `{doc_id, acl_label, folder, is_canary}`
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (sorgu da aynı modelle embed edilmeli)
- Config: `src/config.py` → `load_config()`, `resolve()`; `.env` otomatik yüklenir
- Kanaryalar: `data/canaries/canaries.json` (4 present, 4 absent)

## Dosyalar

### 1. `src/agent/retrieval.py`
- `Retriever(cfg)`: Chroma koleksiyonunu ve embedding modelini bir kez yükler.
- `retrieve(message, mode) -> list[RetrievedChunk]` (`text, doc_id, acl_label, is_canary, score`).
  - **M1_weak:** filtre yok, `top_k` (config: 5) chunk; confidential dahil.
  - **M2_strong:** Chroma `where={"acl_label": {"$in": ["public", "internal"]}}`;
    confidential retrieval aşamasında hiç gelmez.
- Mod `acl_modes` listesinde değilse `ValueError`.

### 2. `src/agent/agent.py`
- `AgentDecision` (pydantic): `escalated: bool`, `refusal_type: Literal[none, no_info,
  cannot_share, deflect]`, `routing_target: Literal[...]`, `answer_text: str`.
- `routing_target` serbest string yerine **sabit küme** (Faz 4'te kategorik özellik
  kararlı olsun): `billing, technical_support, account_management, legal, sales,
  operations, none`. Model dışında bir değer dönerse `other`'a eşlenir.
- Sistem promptu: dış müşteri hizmet ajanı (Fin/Agentforce benzeri). Retrieved chunk'lar
  `[acl_label]` etiketiyle bağlama konur.
  - M1_weak ek kuralı: "confidential etiketli içeriği müşteriye asla yazma/ima etme".
  - M2_strong: aynı rol; bağlamda zaten confidential yok.
- Çağrı: `litellm.completion(model, messages, response_format=<JSON schema>, temperature=0)`.
  Ollama'da `ollama_chat/*` + JSON schema → `format` alanına gider.
- Doğrulama: pydantic ile parse; başarısızsa 2 retry, yine olmazsa
  `parse_error=True` ile loglanır (satır atılmaz, Faz 4'te filtrelenir).
- `AgentRunner.handle(message, mode, model) -> (AgentDecision, meta)`; meta:
  `latency_ms`, `retrieved_acl_labels`, `retrieved_doc_ids`, token kullanımı.

### 3. `src/agent/logger.py`
- `log_call(record)` → `results/agent_log.jsonl`'a append (config `paths.agent_log`).
- Alanlar (plandaki liste + birkaç ek):
  `message_id, acl_mode, model, retrieved_acl_labels, escalated, refusal_type,
  routing_target, answer_text, latency_ms, timestamp` +
  `retrieved_doc_ids, prompt_tokens, completion_tokens, parse_error, message_text`.
- `message_id`: çağıran verirse onu kullanır (Faz 3 probe id'leri), yoksa uuid4.

### 4. `src/agent/smoke.py` (doğrulama komutu)
- `python -m src.agent.smoke`: 2-3 sabit mesajı (biri kanarya konusuna değen, biri
  ilgisiz) her model × {M1, M2} için çalıştırır, `retrieved_acl_labels` farkını ve log
  satırlarını yazdırır.

### 5. `tests/test_agent.py` (offline)
- Retrieval: küçük geçici index'te M2 hiçbir zaman `confidential` döndürmez, M1 döndürür.
- Agent: `litellm.completion` mock'lanır; geçerli JSON → doğru `AgentDecision`;
  bozuk JSON → retry → `parse_error=True`; bilinmeyen routing → `other`.
- Logger: satır tüm zorunlu alanları içerir, JSONL geçerli.

### Config değişiklikleri (`config/experiment.yaml`)
- `models`: iki yerel Ollama modeli (API anahtarı yok — bkz. açık kararlar).
- `agent:` bölümü: `temperature: 0`, `max_retries: 2`, `routing_targets: [...]`.

## Doğrulama (plan dokümanındaki kriterler)
- Aynı mesaj M1 ve M2'de çalışınca `retrieved_acl_labels` farklı; M2'de `confidential` yok.
- Log satırı tüm alanları içerir.
- En az iki modelde çalışır.
- `pytest` yeşil → commit "Faz 2: ajan boru hattı".

## Açık kararlar (devam ederken netleştir)
1. **İki model seçimi** (API anahtarı yok):
   - `ollama_chat/gemma3:latest` (4B, mevcut) — hızlı, önerilen birinci model.
   - İkinci model için seçenekler: `qwen2.5:7b` veya `llama3.1:8b` indirmek (~4.7 GB,
     instruct, JSON çıktıda iyi); ya da mevcut `gemma4:26b` (kaliteli ama ~5.6 tok/s,
     Faz 3 ölçeğinde çok yavaş). `qwen2.5-coder:7b` kod modeli, müşteri ajanı için uygun değil.
   - Plan dokümanı "biri açık + biri ticari API" diyor; API anahtarı alınırsa ikinci model
     config'ten değiştirilir, kod değişmez.
2. **routing_target** sabit küme mi (önerilen) yoksa serbest string mi?
3. **gemma4 düşünme modu:** kullanılacaksa litellm üzerinden thinking'i kapatmak
   gerekebilir (uzun reasoning çıktısı gecikmeyi ve latency kanalını bozar).

## Notlar / dersler
- `pkill -f <desen>` kullanma: desen kendi shell komut satırında da geçtiği için
  çağıran shell'i öldürüyor. PID ile `kill` kullan.
- `gemma4:26b` 4 GB GPU'ya sığmıyor (RTX 3050 Ti), ~5.6 tok/s.
