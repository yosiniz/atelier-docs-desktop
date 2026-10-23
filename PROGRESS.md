# İlerleme

## 22 Ekim 2026

- Boş repository analiz edildi; Node 24.14 ve Python 3.13 bulundu.
- Docker, Tesseract, LibreOffice, qpdf ve Ghostscript'in sistem PATH'inde bulunmadığı doğrulandı.
- Masaüstü hedefi için Electron + React + yerel FastAPI mimarisi kuruldu.
- PDF metin analizi, içerik-akışı redaksiyonu, yeniden yazma, render, döndürme, bölme, birleştirme ve nesne optimizasyonu uygulandı.
- Görsel dönüşüm/düzenleme servisi ve masaüstü arayüzü uygulandı.
- Backend entegrasyon ve frontend bileşen testleri eklendi.
- Sayfa silme/sıralama/kırpma, yeni metin-resim-şekil ekleme ve kalıcı alan redaksiyonu tamamlandı.
- Her değişiklik öncesi revizyon alan undo/redo akışı ve orijinal dosyayı koruma uygulandı.
- PDF → DOCX, DOCX → PDF, PDF → PNG/JPG ve görsel → PDF dönüşümleri eklendi.
- Gömülü görselleri seçilen kalite profiline göre yeniden örnekleyen PDF sıkıştırma tamamlandı.
- AES-256 şifreli kopya, parola ile kilit açma ve PDF metadata düzenleme eklendi.
- Görsel crop, gri tonlama, sepya, keskinleştirme ve hedef KB optimizasyonu tamamlandı.
- Üretim API'si rastgele oturum anahtarıyla korundu; Electron renderer izolasyonu ve gizli backend sidecar başlatma doğrulandı.
- PDF bağlantıları, kaldırılabilir filigran, imza, vektör serbest çizim ve yaygın font aileleri eklendi.
- PDF sıkıştırma için ilerleme/iptal destekli sınırlı iş kuyruğu ve içerik tutmayan işlem geçmişi eklendi.
- Yerel Tesseract OCR akışı; kelime koordinatları, güven ortalaması ve seçilebilir görünmez metin katmanı eklendi.
- DOCX/XLSX/CSV/PPTX görüntüleme-düzenleme, temel yapısal işlemler ve Office → PDF geri dönüşümleri tamamlandı.
- PDF → XLSX/PPTX, toplu görsel dönüşümü ve toplu PDF/görsel sıkıştırma tamamlandı.
- Katmanlı Canvas görsel editörü; metin/dikdörtgen, taşıma, sıralama ve undo/redo tamamlandı.
- 41 backend entegrasyon/güvenlik/performans testi ve 4 frontend bileşen testi geçti; TypeScript strict kontrolü ve üretim derlemesi başarılı.
- PDF bul/tümünü değiştir, metin kutusu taşıma-boyutlandırma, kalın/italik/altı çizili ve hizalama tamamlandı.
- Görsel kırpma aracı, boş sayfa, üstbilgi/altbilgi ve sayfa numarası akışları eklendi.
- Yerel API anahtarı için güvenlik testi ve 72 saatlik güvenli geçici çalışma alanı temizliği eklendi.
- OOXML ZIP bombası sınırları ve HTTP güvenlik başlıkları eklendi.
- PowerPoint slayt sıralamada bulunan kontrol akışı hatası testle yakalanıp düzeltildi.
- Windows NSIS kurulum paketi yeniden üretildi ve paketlenmiş backend için sağlık, yetkisiz/yetkili erişim smoke testi geçti.
- Kullanılmayan Fabric bağımlılığı kaldırıldı; production bağımlılık denetimi 0 açık bildirdi.
- Atelier Docs görsel kimliğiyle çok çözünürlüklü Windows uygulama ve kurulum ikonu eklendi.
- Electron `file://` üretim yüklemesindeki mutlak Vite asset yolu hatası giderildi; asset yolları göreli hale getirildi.
- Görünmez paketlenmiş Electron smoke testi React kökünün render edildiğini ve kapanışta sidecar süreç kalmadığını doğruladı.
- PDF metin kutuları ve gömülü görseller için sayfa sınırlarına duyarlı, bırakınca otomatik kaydeden sürükle-bırak taşıma eklendi.
- Metin taşıma sırasında alttaki zemin korunur; görselin eski yerleşimi içerikten kaldırılır. Her iki işlem de revizyon/Undo kapsamındadır.
- Mevcut PDF metninin font, punto, renk, kalın/italik/altı çizili ve hizalama özelliklerini tek biçim olarak kopyalayıp mevcut veya yeni metne yapıştırma eklendi.
- Eski `0.1.0` kullanıcı ve `0.1.1` sistem kurulumları resmi kaldırıcılarla temizlendi.
- Yeni paket üretiminden sonra eski kullanıcı sürümünü kaldıran, en yeni sürümü sessiz kuran ve uygulamayı otomatik başlatan yerel yükseltme akışı eklendi.
- PDF metin seçimleri blok yerine gerçek span düzeyine indirildi; tablo hücrelerinin birlikte kayması önlendi ve düzenlenen metin orijinal taban çizgisinde yeniden yazılıyor.
- PDF → Word motoru koordinat korumalı hibrit yerleşime geçirildi; QR/görseller, çizgiler ve tablo zeminleri korunurken metinler düzenlenebilir Word çerçevelerine dönüştürülüyor. Tek ve üç sayfalı çıktılar Microsoft Word renderıyla doğrulandı.
- PDF → PNG çıktısı opak RGB sayfa renderına geçirildi; gerçek makbuz örneğinde kaynak render ile piksel farkının `0.0` olduğu doğrulandı.
- PDF → PowerPoint, metinsiz sayfa çizimleri ve PDF koordinatlarında düzenlenebilir span kutuları kullanan hibrit yerleşime geçirildi. Office ile yeniden PDF renderında ortalama piksel farkı `2.33/255` ölçüldü.
- PDF → Excel tek sütunlu metin dökümü yerine koordinat tabanlı düzenlenebilir hücre ızgarası ve her sayfa için kayıpsız görünüm sekmesi üretir.
- DOCX/XLSX/CSV/PPTX → PDF işlemleri, kurulu Microsoft Word/Excel/PowerPoint motorunu makrolar kapalı ve kaynak salt okunur biçimde kullanacak şekilde yükseltildi; Office yoksa yerel geri dönüşüm korunur.
- PNG/JPG/WebP dönüşümlerinde alfa, EXIF yönü, ICC profili, DPI ve geçersiz boyut doğrulaması denetlendi.
- Arayüz baştan nötr tasarım sistemine geçirildi. Mor gradyanlar ve çok renkli araç kartları kaldırıldı; sıcak gri yüzeyler, mürekkep siyahı, sakin yeşil vurgu, daha küçük köşe yarıçapları ve düz butonlar kullanıldı. Ana sayfa ile açık/koyu tema gerçek tarayıcı görünümünde doğrulandı.

## Son doğrulanan çıktı

- Dosya: `release/Atelier-Docs-0.1.8-Setup.exe`
- Boyut: 181.327.466 bayt (172,93 MiB)
- SHA-256: `EAF96CC8AE6B5AF98CB66DEADDB58BA28A56CDC35349B44FA0080B03654B3EB4`
- Durum: TypeScript strict kontrolü, 4 frontend testi, 41 backend testi ve kurulu uygulama açılış testi geçti. 0.1.8 kullanıcı profiline kuruldu, eski kurulum paketleri kaldırıldı ve uygulama başlatıldı.

## Harici gereksinim veya ileri kapsam

1. Kod imzalama sertifikası ve yayın uç noktası sağlandığında Authenticode ve internet üzerinden otomatik paket indirme/güncelleme.
2. Tesseract çalıştırılabiliri/dil paketleri sağlandığında dağıtım ortamında gerçek taranmış belge kabul testi.
3. Microsoft Office bulunmayan Windows sistemlerinde yüksek uyum için paketlenebilir LibreOffice alternatifi.
4. Paketlenmiş Electron arayüzü için ayrı tam otomatik UI E2E test paketi.
