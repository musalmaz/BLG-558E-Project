# Sunum (İngilizce)

Canlı sürüm (gizli bağlantı, yalnızca sahibi açabilir): https://claude.ai/artifact/RwhpTNur9Ddeo3Gw613aZp

Bu klasör sunumun kaynağıdır:
- `deck.json`: slayt sırası, bölümler ve yazı tipleri.
- `slides/<id>.html`: her slayt bir dosya (1920x1080 tuval, satır içi stil); konuşmacı notları `<aside>` içinde.

Sayfa düzeni için slayt sırası `deck.json` içindeki `order` alanındadır. PowerPoint veya PDF için sunum sayfasındaki Share/Export menüsünü kullanın.
Kapaktaki `[Name Surname] · [Date]` alanı doldurulmayı bekliyor.

## Dosyalar
- `presentation.pptx`: **8 slaytlık** PowerPoint sürümü (ödev sınırı: en çok 8 sayfa, 6 dk anlatım + 4 dk soru). Konuşmacı notları dahil.
- `presentation_full19.pptx`: 19 slaytlık uzun sürüm (arşiv).
- `build_pptx.py`: 8 slaytlık dosyayı üretir (`python-pptx`; ayrı bir sanal ortamda `pip install python-pptx`).
- `deck.json` ve `slides/`: web sürümünün (19 slayt) kaynağı.
