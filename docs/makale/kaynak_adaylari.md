# Kaynak adayları (OKUMAK için; makaledeki özet ve yorum senin olmalı)

Durum: Aşağıdaki başlıklar ve bağlantılar web aramasında **listelendi**. Yazar listesi, cilt/sayı/sayfa, yayın yılı ve dergi adını yayıncının sayfasından kendin doğrula ve kaynakçaya oradan yaz. Bazı kayıtların dergi adı bağlantı biçiminden çıkarıldı (belirtildi). Hiçbirinin tam metnini ben okumadım.

Ödev kısıtları: 10–15 kaynak; **en az 5 dergi makalesi, 2024 sonrası**; web sayfası, bülten, teknik rapor kabul edilmiyor; "open access papers" ifadesi de geçiyor (USENIX, ACL, ICLR bildirileri açık erişimlidir, hocaya sor).

## A. Dergi makaleleri (2024 sonrası) adayları
| # | Başlık | Yayın yeri (doğrula) | Bağlantı |
|---|---|---|---|
| 1 | RAG-leaks: difficulty-calibrated membership inference attacks on retrieval-augmented generation | Science China Information Sciences (Springer), 2025 | https://link.springer.com/article/10.1007/s11432-024-4441-4 |
| 2 | Mitigating privacy risks in Retrieval-Augmented Generation via locally private entity perturbation | ScienceDirect, kod S0306457325000913 (dergi: büyük olasılıkla Information Processing & Management), 2025 | https://www.sciencedirect.com/science/article/abs/pii/S0306457325000913 |
| 3 | Privacy-preserving RAG via multi-agent semantic rewriting: Achieving confidentiality without compromising contextual fidelity | ScienceDirect, kod S0306457326003924 (aynı dergi ailesi; yıl 2026 görünüyor, doğrula) | https://www.sciencedirect.com/science/article/pii/S0306457326003924 |
| 4 | From prompt injections to protocol exploits: Threats in LLM-powered AI agents workflows | ScienceDirect, kod S2405959525001997 (dergi: büyük olasılıkla ICT Express), 2025 | https://www.sciencedirect.com/science/article/pii/S2405959525001997 |
| 5 | Unique Security and Privacy Threats of Large Language Models: A Comprehensive Survey | ACM Computing Surveys, 2025 (survey; kaynak olarak göstermek serbest, makalen survey olmamalı) | https://dl.acm.org/doi/10.1145/3764113 |
| 6 | Efficient Privacy-Preserving Retrieval Augmented Generation with Distance-Preserving Encryption | IEEE Xplore belge 11391120 (dergi mi bildiri mi, doğrula) | https://ieeexplore.ieee.org/abstract/document/11391120 |
| 7 | Cache Partitioning for Mitigating Timing Side-Channel Attacks in LLM Serving Systems | IEEE Xplore belge 10913329 (dergi mi bildiri mi, doğrula) | https://ieeexplore.ieee.org/iel8/10912812/10912809/10913329.pdf |

Dergi sayısı yetmezse kendin ara: IEEE Transactions on Information Forensics and Security, IEEE Transactions on Dependable and Secure Computing, Computers & Security, ACM Transactions on Privacy and Security, Information Processing & Management. Anahtar sözcükler: "retrieval-augmented generation privacy", "LLM side channel", "LLM agent access control", "prompt leakage", "membership inference RAG".

## B. Konferans bildirileri (2024 sonrası, hakemli)
| Başlık | Yayın yeri | Bağlantı |
|---|---|---|
| What Was Your Prompt? A Remote Keylogging Attack on AI Assistants (Weiss ve ark.) | USENIX Security 2024 | https://www.usenix.org/conference/usenixsecurity24/presentation/weiss |
| I Know What You Said: Unveiling Hardware Cache Side-Channels in Local Large Language Model Inference (Gao ve ark.) | USENIX Security 2025 | https://www.usenix.org/conference/usenixsecurity25/presentation/gao-zibo |
| I Know What You Asked: Prompt Leakage via KV-Cache Sharing in Multi-Tenant LLM Serving (Wu ve ark.) | NDSS 2025 | https://ndss-symposium.org/ndss-paper/i-know-what-you-asked-prompt-leakage-via-kv-cache-sharing-in-multi-tenant-llm-serving |
| The Early Bird Catches the Leak: Unveiling Timing Side Channels in LLM Serving Systems (Song ve ark.) | IEEE Xplore belge 11206380 (bildiri adını doğrula) | https://ieeexplore.ieee.org/abstract/document/11206380 |
| Mask-based Membership Inference Attacks for Retrieval-Augmented Generation | WWW '25 (ACM) | https://dl.acm.org/doi/10.1145/3696410.3714771 |
| Riddle Me This! Stealthy Membership Inference for Retrieval-Augmented Generation | ACM; aramada CCS '25 yazıyor, doğrula | https://dl.acm.org/doi/10.1145/3719027.3744840 |
| The Good and The Bad: Exploring Privacy Issues in Retrieval-Augmented Generation (RAG) (Zeng ve ark.) | Findings of ACL 2024 | arXiv 2402.16893 |
| Follow My Instruction and Spill the Beans: Scalable Data Extraction from RAG Systems (Qi ve ark.) | ICLR 2025 | arXiv 2402.17840 |
| MoEcho: Exploiting Side-Channel Attacks to Compromise User Privacy in Mixture-of-Experts LLMs | ACM CCS 2025 | https://repository.lsu.edu/eecs_pubs/2805 |

## C. Hakemli yayını doğrulanmamış (kaynakçada kullanmadan önce kontrol et)
- Carlini & Nasr, "Remote Timing Attacks on Efficient Language Model Inference" (arXiv 2410.17175): hakemli sürümü var mı bak.
- Microsoft, "Whisper Leak" (arXiv 2511.03675): arXiv ön baskısı görünüyor, ödev kuralına uymayabilir.
- Anderson ve ark., "Is My Data in Your Retrieval Database?" (arXiv 2405.20446): kayıtlarda çelişkili yayın yeri var.

## Neye bakmalı (okurken kendi cümlelerinle not al)
- Her makale hangi katmanda sızıntıyı gösteriyor (ağ, önbellek, uygulama)? Gözlemci kim? Saldırı istemi gerekiyor mu?
- Savunma önerisi var mı, bedeli ne?
- Senin çalışmanın farkı bu kayıtlarla kıyaslandığında nerede?
