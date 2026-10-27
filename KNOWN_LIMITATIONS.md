# Bilinen Sınırlamalar

- PDF bir akış belgesi değildir; mevcut metin değişikliği seçilen metin alanını kalıcı redaksiyonla kaldırıp yeniden oluşturarak yapılır. Paragrafın geri kalanını Word gibi otomatik akıtmaz.
- Karmaşık Type3/font-alt-kümesi metinleri, eğri üzerindeki metin, dikey yazı ve bazı Form XObject içerikleri henüz düzenlenemez.
- Taranmış PDF sayfaları algılanır; Windows kurulumuyla gelen yerel Tesseract ve Türkçe/İngilizce dil verileriyle OCR uygulanır. OCR metni seçilebilir ve editörde düzenlenebilir; düşük kaliteli/eğri taramalarda sonuç kullanıcı kontrolü gerektirir.
- Office → PDF dönüşümü Microsoft Word/Excel/PowerPoint kurulu Windows sistemlerinde uygulamanın kendi PDF motorunu kullanır. Office bulunmazsa yerel metin/tablo/slayt geri dönüşümü devreye girer ve karmaşık stiller birebir korunmayabilir. Animasyonlar ile makrolar PDF çıktısında çalışmaz; kaynak dosya salt okunur açılır ve makrolar kapatılır.
- Dengeli ve küçük PDF sıkıştırma profilleri uygun gömülü görselleri yeniden örnekler. Zaten optimize edilmiş, vektör ağırlıklı veya alfa kanallı belgeler küçülmeyebilir.
- Şifreli PDF kopyası, metadata ve URI bağlantısı ekleme desteklenir; sertifika tabanlı dijital imza, mevcut bağlantı silme/düzenleme, PDF katmanları ve form alanı düzenleme henüz yoktur.
- Windows kurulum dosyası üretilebilir ancak kod imzalama sertifikası olmadığı için paket Authenticode imzasızdır ve SmartScreen uyarısı gösterebilir.
- PDF → DOCX dönüşümü çizgi, tablo zemini ve görselleri sayfa arka planında korur; metinleri PDF koordinatlarında ayrı düzenlenebilir Word çerçeveleri olarak yerleştirir. Döndürülmüş/eğri metin, Type3 fontlar ve bazı özel PDF efektleri Word içinde sadeleştirilebilir.
- PDF → PPTX aynı koordinat korumalı hibrit yaklaşımı kullanır. PDF sayfaları farklı boyutlardaysa PowerPoint'in sabit slayt boyutuna orantılı ölçeklenir. Eğri/döndürülmüş metin ve özel efektler sadeleştirilebilir.
- PDF → XLSX çıktısında kayıpsız sayfa görünümü ayrı bir sekmede, düzenlenebilir metin ise koordinat tabanlı hücre ızgarasında tutulur. Excel bir sabit sayfa tuvali olmadığı için karmaşık tablo birleşimleri ve formüller PDF'den otomatik olarak yeniden oluşturulmaz.
- Görsel editörü metin ve dikdörtgen katmanlarını destekler; serbest vektör kalem, gelişmiş maske, akıllı seçim ve ML tabanlı arka plan kaldırma yoktur.
- PDF editöründe mevcut metin kutuları ve gömülü raster görseller sürüklenebilir; mevcut serbest vektör çizimleri ve karmaşık Form XObject grupları henüz tek nesne olarak taşınamaz.
- İş kuyruğu süreç içidir; uygulama tamamen kapatılırsa bekleyen işler kalıcı olarak devam etmez.
- Yerel geliştirme paketlemesi eski kullanıcı sürümünü kaldırır, yenisini kurar ve uygulamayı otomatik açar. İnternet üzerinden yeni sürüm arama/indirme ise yayın sunucusu, kod imzalama sertifikası ve dağıtım kimlik bilgileri sağlanmadığından henüz yoktur; kurulum dosyası imzasızdır.
# macOS dağıtımı

- macOS DMG paketleri Apple Silicon ve Intel için ayrı üretilir.
- DMG paketleri ad-hoc imzalıdır ve CI içinde DMG içinden başlatılarak sınanır. Apple Developer sertifikası ve noterleme kimlik bilgileri sağlanmadığı için Gatekeeper ilk açılışta yine kullanıcı onayı isteyebilir; uyarısız çift tıklama deneyimi ancak Developer ID imzası ve Apple noterlemesiyle sağlanabilir.
- LibreOffice gibi harici araçlara bağlı işlevler ayrı kurulum gerektirir. macOS DMG henüz Tesseract ikililerini gömmez; OCR için `brew install tesseract tesseract-lang` gerekir.

# WhatsApp entegrasyonu

- Canlı kullanım için kullanıcıya ait Meta Business hesabı, WhatsApp telefon numarası, erişim anahtarı, uygulama sırrı ve herkese açık HTTPS webhook alan adı gerekir.
- Bu kimlik bilgileri paylaşılmadığı için canlı WhatsApp kabul testi henüz yapılmadı; webhook, imza, oturum ve dönüşüm davranışları otomatik testlerle doğrulandı.
- WhatsApp ve Meta'nın medya biçimi/boyutu politikaları uygulamanın kendi sınırlarından daha dar olabilir.
- Çok sayfalı PDF → görsel dönüşümünde her sayfa ayrı WhatsApp mesajı olarak gönderilir.

