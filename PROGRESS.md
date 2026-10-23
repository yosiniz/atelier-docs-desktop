# İlerleme

## 23 Ekim 2026

- 0.2.1 macOS dağıtımı: DMG içeriği ad-hoc imzaya geçirildi; minimum macOS 12 belirtildi; Apple Silicon ve Intel işlerinde DMG bağlama, derin kod imzası kontrolü, yerel backend varlık/mimari kontrolü ve paketlenmiş uygulama smoke testi yayın kapısı yapıldı.
- Electron başlatıcısı Windows ve macOS için platform bağımsız yerel backend seçimine geçirildi.
- macOS sistem fontları ve iki platformun yol ayıraçlarını güvenli işleyen dosya adı temizleme desteği eklendi.
- Kaynak kod `yosiniz/atelier-docs-desktop` adlı yeni özel GitHub reposuna yüklendi.
- GitHub Actions üzerinde Apple Silicon ve Intel çalıştırıcılarında 4 frontend ve 41 backend testi ayrı ayrı geçti.
- `Atelier-Docs-0.1.8-arm64.dmg` ve `Atelier-Docs-0.1.8-x64.dmg` üretildi; SHA-256 dosyasıyla birlikte `v0.1.8` GitHub Release olarak yayımlandı.
- Resmi WhatsApp Business Cloud API için webhook doğrulama, HMAC imza kontrolü, medya indirme/yükleme ve yanıt dosyası gönderme modülü eklendi.
- Dosya ile komut aynı mesajda veya 30 dakika içinde art arda gönderilebilir; komut ve dosya sırası bağımsızdır.
- PDF→Word/PNG/JPG, PDF sıkıştırma, görsel format/PDF ve Office→PDF komutları mevcut dönüşüm motoruna bağlandı.
- Numara izin listesi, mesaj tekilleştirme, gerçek dosya türü ve SHA-256 doğrulaması, boyut sınırları ve işlem sonrası geçici dosya temizliği eklendi.
- WhatsApp entegrasyonuyla birlikte 47 backend ve 4 frontend testi geçti; Docker Compose yapılandırması statik olarak doğrulandı.

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

- Dosya: `release/Atelier-Docs-0.2.0-Setup.exe`
- Boyut: 182.183.762 bayt (173,74 MiB)
- SHA-256: `ed3fc6587bcbfc06eedce8f309224bcfc585751e700016d5d2ea0b870d32ba69`
- Durum: 4 frontend ve 47 backend testi Windows, Apple Silicon ve Intel CI ortamlarında geçti. 0.2.0 kullanıcı profiline kuruldu, eski sürüm ve kurulum paketi kaldırıldı; kurulu uygulama smoke testi geçti ve pencere başlatıldı.
- Apple Silicon DMG: `Atelier-Docs-0.2.0-arm64.dmg` — 201.569.731 bayt — SHA-256 `09cf9fc3dd53d2cb6dc05ce8098b16ba9d627892aaefc9f29ed2cffb283b46d0`
- Intel DMG: `Atelier-Docs-0.2.0-x64.dmg` — 209.732.682 bayt — SHA-256 `25da334a41450b46d7b9afe5065061ed57283386289ed4bcf54cd86d86a4de5e`
- GitHub Release: `https://github.com/yosiniz/atelier-docs-desktop/releases/tag/v0.2.0`

## Harici gereksinim veya ileri kapsam

1. Windows ve Apple Developer kod imzalama/noterleme kimlikleri sağlandığında imzalı paketler ve internet üzerinden otomatik güncelleme.
2. Tesseract çalıştırılabiliri/dil paketleri sağlandığında dağıtım ortamında gerçek taranmış belge kabul testi.
3. Microsoft Office bulunmayan Windows sistemlerinde yüksek uyum için paketlenebilir LibreOffice alternatifi.
4. Paketlenmiş Electron arayüzü için ayrı tam otomatik UI E2E test paketi.
