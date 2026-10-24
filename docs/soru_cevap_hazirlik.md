# Soru-cevap hazırlığı (sunum ve makale için)

Ödev kuralı: raporun her ayrıntısını bilmen ve sorulara cevap vermen gerekiyor. Aşağıdaki cevaplar kısa tutuldu; sayıların kaynağı `docs/ilerleme_raporu.md` ve `docs/makale/deney_sayilari.md`. Cevapları kendi cümlelerinle söylemeye çalış.

## A. Genel
**1. Projenin sorusu ne?**
Gizli belgelere erişebilen bir müşteri ajanı, hiçbir sırrı yazmasa bile *davranışıyla* o belgelerin varlığını ele verir mi? Gözlemci sıradan bir müşteri, yalnızca meşru mesaj yazıyor.

**2. Doğrudan sızıntı ile yan kanal farkı nedir?**
Doğrudan sızıntıda sır cevabın içinde yazılır ("kurul 24'ünde"). Yan kanalda sır yazılmaz; ton, ret, yönlendirme ve süre gibi davranış o konuda gizli belge olduğunu gösterir.

**3. Neden önemli?**
Bir birleşmenin ya da işten çıkarmanın hazırlandığını bilmek bile zarar verebilir. Ayrıca "prompt'ta gizliyi yazma de" tek başına koruma sağlamıyor.

**4. Enjeksiyon neden kullanılmadı?**
Zayıf bir saldırgan modeli seçtik: meşru mesajlar yeterliyse her müşteri potansiyel gözlemci olur. Hazırlanmış veya enjekte edilmiş istemlerle yapılan saldırılar zaten ayrı bir literatür (Qi vd., Zeng vd.).

**5. Etik sınır nedir?**
Kendi replika ortamımız, kamuya açık Enron e-postaları ve uydurma kanarya belgeler. Gerçek ürün veya gerçek kişisel veri yok.

## B. ACL ve ajan
**6. ACL nedir, M1 ve M2 farkı?**
Her belgeye public/internal/confidential etiketi verilir. M1 (zayıf): arama her etiketi getirir, prompt yalnızca "gizliyi yazma" der. M2 (güçlü): gizli belge arama aşamasında süzülür, model hiç görmez. Aradaki tek fark ajan boru hattının 3. adımıdır.

**7. Ajan nasıl çalışıyor?**
Mesaj gömülür, ChromaDB'den en benzer 5 parça gelir, ACL moduna göre süzülür, prompt kurulur, yerel LLM (gemma3 veya qwen2.5:7b, sıcaklık 0) JSON karar ve cevap üretir (`escalated`, `refusal_type`, `routing_target`, `answer_text`). Her çağrı loglanır.

**8. Neden sıcaklık 0?**
Çıktı deterministik olsun; farklar rastgelelikten değil bağlamdan gelsin.

**9. Neden yerel modeller?**
API anahtarı yoktu ve veri makineden çıkmasın istedik. Sınırlama: iki küçük model.

## C. Veri ve deney tasarımı
**10. Kanarya belge nedir, neden?**
Kendimizin yazdığı sahte gizli e-postalar. Hangi konuda gizli belge olduğunu biz bildiğimiz için doğru cevap (ground truth) vardır; içlerine sır niteliğinde ayrıntılar (işaretçi: tarih, rakam) koyduk.

**11. 20 konunun yapısı?**
10 konuda 3'er gizli belge var, 10 konuda yok. Belgesiz konular, decoder'ın "var mı yok mu" ayrımı için negatif sınıf.

**12. Probe ve control nedir, neden control?**
Probe konuya dokunan, control aynı kalıp ve uzunlukta (fark ≤ %25) ama konusuz mesaj. Karşılaştırarak konunun etkisini kelime dizilişi etkisinden ayırıyoruz.

**13. 800 çağrı nereden?**
20 konu × 2 tür × 5 varyant × 2 ACL modu × 2 model.

## D. Ölçüm ve istatistik
**14. Decoder nedir, neden lojistik regresyon?**
Saldırganı temsil eden sınıflandırıcı: çıktıya bakıp konuda gizli belge var mı tahmin eder. Sabit L2 lojistik regresyon seçtik, ayar yok; basit bir model bile başarıyorsa sinyal gerçektir. Karmaşık model sinyalin varlığı sorusunu bulanıklaştırırdı.

**15. AUC nedir, neden AUC?**
Gizli belgeli bir konunun gizli belgesiz bir konudan yüksek skor alma olasılığı. Eşik gerektirmez, sınıf dengesizliğinden etkilenmez, tek karşılaştırılabilir sayı verir. 0,5 yazı-tura, 1,0 kusursuz.

**16. TPR@1%FPR, gereken mesaj, sızan bit?**
Yanlış alarm %1 iken yakalama oranı (temkinli saldırgan); konu düzeyinde AUC ≥ 0,9 için gereken probe sayısı; mesaj başına bilgi (bit).

**17. Leave-one-topic-out (LOTO) neden?**
Decoder test konusunu eğitimde hiç görmez; konu kelimelerini ezberleyip puan alamaz.

**18. Randomized control nedir?**
Sonucun şans olmadığını gösterir: (i) konu etiketlerini 500 kez rastgele dağıtıp AUC'nin şansla ne kadar çıkabildiğine bakmak (p değeri), (ii) satır etiketi karıştırma, (iii) plasebo decoder (control satırlarında aynı prosedür).

**19. "Kanal açık" ne demek?**
Önceden sabit ölçüt: konu-permütasyon p < 0,05 ve AUC güven aralığı alt sınırı > 0,5.

**20. LOTO'da AUC neden 0,5'in altına inebiliyor?**
Dengeli etiketlerde kesişim terimi etiketle ters ilişkili skor üretebiliyor (pilotta AUC 0,0 çıkmıştı; `class_weight="balanced"` ile giderildi). Gürültüde bu küçük etki kalıyor, bu yüzden mutlak AUC yerine permütasyon p ve avantaja bakıyoruz.

## E. Bulgular
**21. Ana bulgu?**
Zayıf ACL'de gemma3'ün cevap metni gizli belge olan konuları ayırıyor (AUC 0,82, p = 0,004; 2 mesaj yeter). Davranış alanları (eskalasyon, ret, yönlendirme) anlamlı sinyal vermedi. M2'de hiçbir sinyal yok.

**22. Sinyal sızan gizli kelimelerden mi?**
Hayır. Konu kelimeleri, rakamlar, özel adlar ve yalnızca gizli belgelerde geçen 210 kelime maskelendiğinde AUC düşmedi (0,83 → 0,82). Sinyal üsluptan: gizli bağlamda "we/our" daha çok, "I" ve "unfortunately" daha az, telefon/e-posta verme daha az.

**23. Davranış kanalı yok mu?**
"Bulunamadı" diyebiliyoruz, "yok" diyemiyoruz. Ajan neredeyse hiç eskalasyon yapmıyor, nadiren reddediyor; ölçülecek davranış çeşitliliği az. qwen2.5'in ret türü ipucu veriyor ama anlamlı değil.

**24. k taraması ne gösterdi?**
Konu başına gizli belge sayısı 1, 2, 3: top-5'teki gizli belge sayısı monoton arttı (1,9 → 2,5 → 3,3) ama gemma3 metin AUC'si monoton değil (0,71 → 0,64 → 0,82), aralıklar örtüşüyor. Sağlam olan: tek gizli belge bile anlamlı sinyal veriyor.

**25. qwen2.5 neden zayıf?**
M1'de metin AUC'si 0,61 ve anlamlı değil. Model daha az üslup farkı üretiyor olabilir; küçük örnekte kesin söylenemez.

## F. Savunmalar
**26. Hangi savunmalar, sonuç?**
behavior_norm (ret şablonu), decision_hiding (bağlamsız karar + sabit gecikme): etkisiz (AUC 0,82). scoped_context (yalnızca public): kanalı kapatıyor (0,44) ama internal bilgi kayboluyor (recall kaybı 0,30). M2: 0,45, recall kaybı 0,04, çözüm oranı gemma3'te 0,92 → 0,67.

**27. Çıktıyı düzeltme neden işe yaramadı?**
Sızan şey ret metni ya da karar alanları değil, normal cevapların üslubu; çıktı tarafı normalleştirme bunu değiştirmiyor.

**28. Maskeleme nasıl çalışıyor, sonuç?**
Gizli parçalar bağlama girmeden önce maskelenir: oracle elle yazılmış sır aralıklarını `[REDACTED]` yapar, rule dondurulmuş regex kullanır (sayı, tarih, ad). Doğrudan sızıntı 0,50 → 0,00 (gemma3); fayda korunuyor. Ama metin AUC'si 0,84 (oracle) ve 0,69 (rule): maskeli belge de konunun *varlığını* söylüyor.

**29. Neden oracle ve rule birlikte?**
Oracle üst sınırdır (sızıntı yapı gereği sıfır); rule gerçekçi, kaçıran olabilir (ör. sayısal olmayan "outsourc", "vendor", "non-disparagement" belgede kalıyor). Rule kuralları işaretçilere göre ayarlanmadı.

**30. "Onaylı cümle" ölçüsü ne?**
Gizli konuda dışarıya söylenmesi onaylı cümleyi ("söylentilere yorum yapmıyoruz") ajanın üretme oranı. Mevcut 23'lük fayda setinde gizli kaynak olmadığı için bu set M2 ve maskeleme farkını görünür kılmak için yazıldı.

## G. Ek çalışma (çok kullanıcılı)
**31. Soru ve düzenek?**
A kullanıcısı özel not paylaşıyor, B yalnızca meşru soru soruyor. X1: tüm kullanıcıların hafızası aranır; X3: herkesin notunun ortak özeti her bağlamda; X2: arama önce sahibe göre süzülür.

**32. Sonuç ve neden izolasyon çalışıyor?**
A'nın verisi B'nin cevabında: X1 %72/%52, X3 %70/%56 (gemma3/qwen2.5); X2 %2/%0. İzolasyon retrieval katmanında, benzerlik sıralamasından önce uygulandığı için A'nın kaydı B için aday bile olmuyor; prompt kuralı ise modele güveniyor.

**33. İzolasyonun sınırı?**
B'nin kimliği düzenekten geliyor; kimlik doğrulama modellenmedi. X3 (ortak özet) bu yolla korunamaz; kullanıcı başına özet gerekir.

## H. Sınırlar ve ilgili çalışma
**34. En büyük sınırlar?**
10+10 konu, 5 varyant, çoğunda tek tekrar; iki küçük yerel model; kanarya, mesajlar ve "sır" tanımı tek yazarlı; çoklu test düzeltmesi yok (tek hücrelik p ≈ 0,03 ipucudur); gecikme güvenilmez; fayda ölçüsü işaretçi recall'ı (doğruluk değil).

**35. İlgili çalışmalardan farkınız?**
Ağ/önbellek/donanım yan kanalları (Weiss, Carlini ve Nasr, Whisper Leak, Song, Wu, Gao) ve RAG çıkarma/üyelik saldırıları (Zeng, Qi, Anderson, Liu, RAG-leaks) ya altyapı katmanındadır ya da özel prompt'larla içerik/üyelik çıkarır. Biz uygulama katmanında, meşru mesajlarla, davranışı ölçüyoruz ve savunmaları güvenlik-fayda birlikte puanlıyoruz.

**36. "Bu bir survey mi?"**
Hayır: kendi deney düzeneğimiz (CanaryProbe), kendi ölçümlerimiz ve savunma değerlendirmemiz var; ilgili çalışmalar yalnızca bağlam.

**37. AI desteği nasıl kullanıldı?**
Kod, deney düzeneği, analiz yorumları ve metin taslakları AI desteğiyle hazırlandı; hoca AI desteğine izin verdi. Yöntem, sonuçlar ve sınırlar sana ait olarak savunulmalı; her sayı `verify_numbers.py` ile loglardan doğrulandı.
