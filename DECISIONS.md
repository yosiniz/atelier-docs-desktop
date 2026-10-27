# Teknik Kararlar

## ADR-001 — Electron masaüstü kabuğu

**Karar:** Electron kullanılacak.  
**Gerekçe:** React tabanlı zengin editör, Windows dosya diyalogları ve hızlı iterasyon için en düşük entegrasyon riski. Tauri daha küçük paket üretse de Python sidecar paketleme ve geliştirme karmaşıklığını artırıyor.

## ADR-002 — Yerel Python belge motoru

**Karar:** FastAPI yalnızca `127.0.0.1` üzerinde çalışan modüler monolith olacak.  
**Gerekçe:** PyMuPDF, pypdf, Pillow ve Office ekosistemi belge işleme için olgun. İşlem sınırını HTTP ile ayırmak renderer çökmesi ve bellek kullanımını izole ediyor.

## ADR-003 — PDF mevcut metin düzenleme

**Karar:** Doğrudan güvenilir biçimde yeniden yazılamayan içerikte PyMuPDF redaksiyonu + yeniden oluşturma kullanılacak.  
**Gerekçe:** PDF içerik operatörlerini font alt kümeleri ve karakter eşlemeleri nedeniyle yerinde değiştirmek çoğu belgede güvenilir değildir. Redaksiyon eski operatörü kalıcı kaldırır; görsel kaplama gibi gizli metin bırakmaz.

## ADR-004 — Harici servis yok

**Karar:** Dosya içeriği üçüncü taraf API'lere gönderilmeyecek.  
**Gerekçe:** Gizlilik gereksinimi ve masaüstü/çevrimdışı kullanım hedefi.

## ADR-005 — Paketlenmiş yerel servis ve oturum anahtarı

**Karar:** Python motoru PyInstaller ile tek çalıştırılabilir sidecar olarak paketlenecek; Electron boş bir localhost portu ve süreç başına rastgele API anahtarı üretip servisi görünmez başlatacak.  
**Gerekçe:** Son kullanıcının Python kurmasını gerektirmemek ve aynı makinedeki başka süreçlerin belge API'sine yetkisiz erişimini engellemek.

## ADR-006 — Office dönüşümünde yetenek bazlı yerel motor

**Karar:** Windows'ta kurulu Microsoft Word, Excel ve PowerPoint yüksek uyumlu PDF dönüşümü için salt okunur ve makrolar kapalı biçimde kullanılacak; Office yoksa açıkça belgelenmiş yerel metin/tablo/slayt dönüşümü çalışacak.  
**Gerekçe:** Kullanıcının kurulu Office motoru özgün sayfa düzenini en yüksek doğrulukla üretir. Ayrı işlem, zaman aşımı ve seri dönüşüm kilidi uygulama kararlılığını korur; geri dönüşüm bağımlılık yokluğunda temel işlevi sürdürür.

## ADR-007 — Sınırlı yerel iş kuyruğu

**Karar:** Uzun PDF sıkıştırma işlemleri süreç içi, en fazla iki işçili kuyrukta çalışacak; iş durumu, ilerleme ve kooperatif iptal sunulacak.  
**Gerekçe:** Tek kullanıcılı masaüstü uygulamasında Redis/Celery gibi ayrı altyapı gereksizdir. Sınırlı havuz arayüzün yanıt vermesini korurken kaynak tüketimini sınırlar.

## ADR-008 — OCR yalnızca yerel ve isteğe bağlı

**Karar:** OCR dosyayı harici servise göndermeden yerel Tesseract ile çalışacak. Windows kurulumuna motor ile Türkçe/İngilizce dil verileri gömülecek; mevcut metinli sayfalar varsayılan olarak atlanacak.
**Gerekçe:** Hassas belge gizliliğini korumak. Dil paketi veya çalıştırılabilir yoksa kullanıcıya açık hata verilmesi sessiz ve düşük kaliteli sonuç üretmekten daha güvenlidir.

## ADR-009 — Yerel Canvas katman modeli

**Karar:** Görsel düzenleyicide ağır bir grafik framework'üne bağlı kalmadan React ile yönetilen küçük bir Canvas katman modeli kullanılacak.  
**Gerekçe:** Metin/dikdörtgen, taşıma, sıralama ve undo/redo kapsamı için daha küçük paket, öngörülebilir dışa aktarım ve düşük bakım yüzeyi sağlar.

## ADR-010 — Tek kullanıcı kapsamlı yerel yükseltme

**Karar:** Windows kurulumları yalnızca mevcut kullanıcı kapsamına yapılacak. Yeni yerel paket üretildiğinde önce eski kullanıcı kurulumu resmi NSIS kaldırıcıyla temizlenecek, en yeni paket sessizce kurulacak, doğrulanacak ve uygulama otomatik başlatılacak.  
**Gerekçe:** Sistem-geneli ve kullanıcı-geneli çift kurulumların, eski kısayolların ve sürüm çakışmalarının tekrar oluşmasını önlemek; geliştirme teslimlerini yönetici izni olmadan güvenilir biçimde güncellemek.

## ADR-011 — PDF → Word koordinat korumalı hibrit yerleşim

**Karar:** PDF sayfasındaki metinler normal Word akışına çevrilmeyecek; her metin span'ı PDF koordinatlarında düzenlenebilir Word çerçevesi olarak oluşturulacak. Metin dışı çizimler, tablo zeminleri ve görseller metni kaldırılmış sayfa arka planında korunacak.  
**Gerekçe:** PDF sabit yerleşimlidir. Normal paragraf akışı makbuz, form ve tabloların tamamını kaydırır; hibrit yaklaşım görünümü korurken metnin Word içinde düzenlenebilir kalmasını sağlar.

## ADR-012 — Dönüşümlerde görsel doğruluk ve düzenlenebilirlik katmanları

**Karar:** PDF → PNG/JPG doğrudan opak RGB sayfa renderı üretir. PDF → PPTX, metinsiz kayıpsız sayfa arka planı ile koordinatlı düzenlenebilir metni birleştirir. PDF → XLSX, kayıpsız görünümü ve koordinat tabanlı düzenlenebilir hücreleri ayrı sekmelerde sunar.  
**Gerekçe:** PNG/JPG için hedef birebir görsel sonuçtur. PowerPoint sabit tuval olduğundan hibrit model uygulanabilir. Excel sabit tuval olmadığından görünümü ve düzenlenebilir veriyi tek bir çalışma sayfasında güvenilir biçimde aynı anda korumak mümkün değildir; iki görünüm yanlış yerleşim iddiasını önler.

## ADR-013 — Nötr ve tek vurgulu masaüstü tasarım sistemi

**Karar:** Arayüz sıcak nötr yüzeyler, mürekkep tonları ve yalnızca etkileşim/seçim için kullanılan sakin yeşil vurgudan oluşacak. Araç kategorileri farklı renklerle kodlanmayacak; gradyan ve parlak gölgeler kullanılmayacak.  
**Gerekçe:** Belge düzenleme uygulamasında asıl içerik kullanıcı belgesidir. Nötr arayüz belgeyle görsel rekabeti azaltır, açık/koyu temayı tutarlı kılar ve uzun süreli kullanımda daha sakin bir çalışma alanı sağlar.
# ADR-014 — macOS paketlerini yerel mimaride CI üzerinde üretme

- **Karar:** Apple Silicon ve Intel DMG paketleri ayrı macOS GitHub Actions çalıştırıcılarında üretilecek.
- **Gerekçe:** PyInstaller ile paketlenen Python motorunun Electron uygulamasıyla aynı CPU mimarisinde olması gerekir. Windows üzerinde güvenilir ve doğrulanabilir DMG üretimi desteklenmez.
- **Sonuç:** Her DMG kendi mimarisine ait yerel backend ikilisini içerir. Uygulama ad-hoc imzalanır; CI, DMG'yi bağlayıp kod imzasını ve gerçek uygulama/backend açılışını doğrular. Apple Developer kimlik bilgileri sağlanana kadar Developer ID imzası ve noterleme yapılamaz.

# ADR-015 — WhatsApp için resmi Cloud API ve bağımsız bot servisi

- **Karar:** Kişisel WhatsApp Web otomasyonu yerine resmi WhatsApp Business Cloud API kullanılacak; bot aynı FastAPI kod tabanında fakat bağımsız Docker servisi olarak çalıştırılabilecek.
- **Gerekçe:** Webhook imzası, medya kimlikleri, kurallı gönderim akışı ve hesap uyumluluğu resmi API ile sürdürülebilir biçimde yönetilebilir.
- **Sonuç:** Masaüstü dönüşüm motoru yeniden kullanılır. Canlı bağlantı yalnızca ortam değişkenlerinden alınan Meta kimlik bilgileriyle etkinleşir; gizli bilgiler repoya girmez.

## ADR-016 — Tarama görünümünü koruyan OCR iyileştirmeleri

OpenCV yalnızca OCR girdisinde gölge/kontrast düzeltme, küçük açı düzeltme ve form çizgisi ayıklama için kullanılır. Ters koordinat dönüşümü kelime kutularını asıl sayfaya yerleştirir. Düşük güvenli sonuçlar kullanıcının kontrolüne sunulur; el yazısı için doğruluk iddiası yapılmaz. Eski OCR yeniden tanımada kaldırılır; tarama metninin düzenlenmesi görüntü piksellerine de redaksiyon uygular.

