# İlerleme

## 27 Ekim 2026 — 0.3.2 otomatik biçim koruma

- Metin değiştirirken ve taşırken otomatik kaynak biçimi koruma varsayılan açıldı. Dijital PDF'de kaynak punto, renk, kalınlık/italik ve satır tabanı korunuyor; uygun gömülü font yeniden kullanılıyor.
- Taramalarda görünmez OCR fontu yerine asıl sayfa görüntüsü örnekleniyor. Koyu mürekkep piksellerinden renk tonu, harf yüksekliğinden punto, yerel font şablonlarından yakın font ve kenar piksellerinden kâğıt tonu tahmin ediliyor.
- Elle biçim değiştirme ve biçim yapıştırma destekleniyor. Asenkron biçim önizlemesi seçim değişiminde iptal ediliyor; backend kaydetmeden önce kaynak biçimini tekrar okuyor.
- 65 backend ve 4 frontend testi geçti. Dijital metin testinde tam punto/renk/satır tabanı; gri ve mavi tarama testlerinde ±1 punto/±3 RGB toleransında eşleşme doğrulandı. Önce/sonra görüntüleri gözle kontrol edildi.
- Windows paketinin gerçek API'sinde taramadan biçim okuma → sayıyı otomatik biçimle değiştirme → yeni punto ve rengi doğrulama → kalıcı silme akışı geçti (`automatic_style: passed`).

## 27 Ekim 2026 — 0.3.1 OCR geliştirmeleri

- 300 DPI varsayılan, 200/400 DPI seçimi; Türkçe/İngilizce, otomatik/düz metin/tablo/seyrek yerleşim profilleri ve tek sayfa/tüm belge kapsamı eklendi.
- OpenCV ile gölge/kontrast iyileştirme, ±7 derece küçük açı düzeltme ve tanıma görüntüsünde form çizgisi ayıklama eklendi. Orijinal PDF görünümü korunuyor; ters dönüşüm koordinat kaymasını önlüyor.
- OCR sözcük kutuları font ölçüleriyle iki eksende eşleniyor. Döndürülmüş sayfalar normalize ediliyor; güvenler kalıcı sayfa verisinde tutuluyor ve düşük güvenli sözcükler arayüzde işaretlenebiliyor.
- OCR metin değişimi artık görünmez katmanla birlikte alttaki eski görüntü piksellerini kaldırıyor. Eski OCR katmanını yeniden tanıma kopya metin üretmiyor. Sayfa numaralı hibrit taramalar destekleniyor.
- Arka plan OCR işi sayfa ilerlemesi, iptal, 24 MP raster sınırı ve geçiş başına 90 saniye zaman aşımı içeriyor. Boş sonuç başarı olarak raporlanmıyor.
- Soluk, 1,7 derece eğik Türkçe tablo örneğinde 20 sözcük, %93,7 motor güveni; tutar ve fatura numarası doğrulandı. OCR öncesi/sonrası sayfa rasteri birebir aynı; sözcük kutularının güven verileri yeniden açıldığında korundu. Bu sentetik örnektir, kullanıcı belgelerinde doğruluk garantisi değildir.
- 59 backend ve 4 frontend testi geçti; OCR için koordinat, döndürme, yeniden tanıma, piksel silme, güven verisi, iptal ve hibrit sayfa senaryoları doğrulandı. Paketlenmiş ve kurulu 0.3.1 kopyaları bağımsız native backend süreçlerinde gerçek dosya yükleme → kuyruk → OCR → PDF indirme → metin doğrulama akışıyla kontrol edildi.
- Metin değişimi/bul-değiştir/redaksiyon sırasında kaldırılan kelimeler OCR güven metadata verisinden de temizleniyor; eski metnin ham çıktı dosyasında ve sayfa metninde kalmadığı ayrıca test ediliyor.
- Windows 0.3.1 kurulum paketi üretildi, eski sürüm resmi kaldırıcıyla güncellendi ve yeni uygulama otomatik açıldı.

## 26 Ekim 2026

- 0.3.0 OCR: Taranmış PDF sayfaları görsel kapsama ve metin katmanına göre algılanıyor; yalnızca gerekli sayfalara Türkçe + İngilizce, koordinatlı ve güven skorlu görünmez metin katmanı ekleniyor.
- JPG/PNG/BMP/WebP ve çok sayfalı TIFF taramalarını görüntüyü koruyarak aranabilir PDF'e dönüştüren yeni ana sayfa aracı ve API eklendi.
- Tesseract motoru Windows EXE paketine `tur`, `eng` ve `osd` dil verileriyle birlikte ekleniyor; Türkçe karakterli Windows profil yolları için ASCII OCR dil önbelleği kullanılıyor.

## 27 Ekim 2026

- Windows kullanıcı adındaki Türkçe karakterlerin Tesseract geçici dosya yolunda `utf-8 decode` hatası oluşturması giderildi; OCR girdi ve dil önbelleği `C:\ProgramData\AtelierDocs\OCR` altındaki ASCII yola alındı.
- Sessiz yükseltme öncesinde yalnızca Atelier Docs ve kendi backend süreçleri sonlandırılıyor; eski backend'in bellekte kalıp yeni arayüze hizmet vermesi engellendi.
- 4 frontend ve 49 backend testi geçti. Paketlenmiş OCR motoru gerçek tarama ile %95,1 ortalama güvenle doğrulandı; kurulu uygulamanın sağlık yanıtı `available: true`, `turkish: true`, diller `eng, osd, tur` olarak kontrol edildi.

## 23 Ekim 2026

- 0.2.1 macOS dağıtımı: DMG içeriği ad-hoc imzaya geçirildi; minimum macOS 12 belirtildi; Apple Silicon ve Intel işlerinde DMG bağlama, derin kod imzası kontrolü, yerel backend varlık/mimari kontrolü ve paketlenmiş uygulama smoke testi yayın kapısı yapıldı.
- `v0.2.1` yayın doğrulaması tamamlandı: Apple Silicon uygulama/backend ikilisi `arm64`, Intel uygulama/backend ikilisi `x86_64` olarak doğrulandı; iki DMG de `codesign --verify --deep --strict` ve gerçek açılış smoke testini geçti (`ok: true`, başlık `Atelier Docs`, arayüz metni 1198 karakter).
- Apple Silicon DMG: `Atelier-Docs-0.2.1-arm64.dmg` — SHA-256 `48dfd51c473bf9aa7bd913970aa57af5794d47eed286198f32a2b89f3f4f5fd2`
- Intel DMG: `Atelier-Docs-0.2.1-x64.dmg` — SHA-256 `7d522341693b89d46d7c7c0e76bb11fea0d18773d731551e9a0b10797eacb41e`
- GitHub Release: `https://github.com/yosiniz/atelier-docs-desktop/releases/tag/v0.2.1`
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
