# Atelier Docs Desktop

Atelier Docs; PDF ve görselleri cihazdan çıkarmadan düzenlemek, dönüştürmek, birleştirmek, bölmek ve optimize etmek için geliştirilen Türkçe masaüstü uygulamasıdır.

## Bugünkü çalışan kapsam

- Electron tabanlı Windows ve macOS masaüstü kabuğu
- React + TypeScript ile nötr, sade ve açık/koyu temalı masaüstü arayüz
- Yerel FastAPI belge motoru
- PDF yükleme, çok sayfalı önizleme, küçük resimler ve yakınlaştırma
- PDF metin bloklarını koordinatlarıyla algılama
- Seçilen metni **redaksiyon ile içerik akışından kaldırıp** yeni metni gömülü Unicode fontla yeniden yazma
- PDF sayfa döndürme, bölme, birleştirme, sürükle-bırak sıralama ve kayıpsız nesne optimizasyonu
- PDF sayfa silme, sıralama, kırpma, boş sayfa, üstbilgi/altbilgi ve sayfa numarası
- Yeni metin, gerçek PDF resim nesnesi, şekil, bağlantı, filigran, imza ve serbest çizim
- Kalıcı alan redaksiyonu, undo/redo ve orijinal dosyayı koruma
- Bul/tümünü değiştir; metin kutusu taşıma, boyutlandırma, yaygın font eşleme ve stil seçenekleri
- Kalite profilli PDF sıkıştırma ve gömülü görselleri yeniden örnekleme
- Arka plan iş kuyruğu, ilerleme, iptal ve işlem geçmişi
- PDF → DOCX/XLSX/PPTX/PNG/JPG; Microsoft Office motoruyla yüksek uyumlu Office → PDF ve görsel → PDF dönüşümleri
- DOCX, XLSX/CSV ve PPTX için yerel temel düzenleyiciler
- AES-256 şifreli kopya, parola ile kilit açma ve metadata düzenleme
- PNG/JPG/WebP dönüşümü, piksel ayarları, crop, hedef KB sıkıştırma ve toplu ZIP işlemleri
- Katmanlı Canvas görsel editörü; metin, dikdörtgen, sıralama, taşıma ve undo/redo
- Taranmış PDF sayfalarını otomatik algılayan yerel Türkçe + İngilizce OCR; kelime koordinatları, güven skoru ve seçilebilir/düzenlenebilir metin katmanı
- JPG, PNG, BMP, WebP ve çok sayfalı TIFF taramalarını doğrudan aranabilir PDF'e dönüştürme
- Yerel dosya kaydetme diyaloğu
- Resmi WhatsApp Business Cloud API webhook'u; dosya ve Türkçe komutla dönüşüm, sonucu aynı sohbete gönderme

Windows kurulum paketi Tesseract OCR motorunu ve `tur+eng` dil verilerini içerir; ayrı kurulum gerekmez. Geliştirme ortamında `winget install UB-Mannheim.TesseractOCR` kullanılabilir. macOS'ta OCR için `brew install tesseract tesseract-lang` gerekir. Word, Excel ve PowerPoint kurulu Windows sistemlerinde Office → PDF, belgeleri salt okunur açan yerel Microsoft Office motorunu kullanır; Office bulunmayan sistemlerde açıkça sınırlı yerel geri dönüşüm devreye girer.

## Geliştirme kurulumu (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
npm run dev
```

Testler:

```powershell
npm test
```

Üretim frontend derlemesi:

```powershell
npm run build
```

Windows kurulum paketi:

```powershell
npm run dist:win
```

`dist:win` en yeni kurulum paketini ve içine gömülü OCR motorunu üretir, eski kullanıcı sürümünü kaldırır, yeni sürümü mevcut kullanıcıya sessizce kurar ve uygulamayı başlatır. Başarılı kurulumdan sonra eski yerel kurulum paketleri de temizlenir; yalnızca güncel sürüm tutulur. Çıktı `release/Atelier-Docs-0.3.0-Setup.exe` konumuna yazılır. Üretim sidecar API'si Electron tarafından her oturumda üretilen rastgele anahtarla korunur. Mevcut çıktı kod imzalama sertifikası olmadığı için Authenticode imzasızdır.

## macOS DMG paketleri

GitHub Actions iş akışı Windows EXE ile Apple Silicon (`arm64`) ve Intel (`x64`) için ayrı DMG paketleri üretir. GitHub üzerindeki **Build Desktop Installers** iş akışı elle çalıştırıldığında testleri yürütür, yerel Python belge motorunu her hedef mimaride paketler, DMG'yi bağlar ve içindeki gerçek uygulamayı backend ile birlikte başlatan smoke testini geçmeden yayına izin vermez.

Yerel macOS geliştirme ortamında paket oluşturmak için:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
npm ci
npm run dist:mac
```

DMG içindeki uygulama bütünlük kontrolü için ad-hoc imzalanır. Apple Developer ID ve noterleme bilgileri yapılandırılmadığından internetten indirilen paketin ilk açılışında macOS Gatekeeper uyarı gösterebilir. Doğru paketi seçin: M1/M2/M3/M4/M5 için `arm64`, Intel işlemcili Mac için `x64`. DMG'yi açıp **Atelier Docs** uygulamasını **Applications/Uygulamalar** klasörüne sürükleyin; ilk açılış engellenirse Finder'da uygulamaya sağ tıklayıp **Aç** seçin.

## WhatsApp botu

WhatsApp üzerinden dosya dönüştürme servisi, resmi Meta Cloud API ile çalışır. Kurulum, güvenlik, ortam değişkenleri ve desteklenen komutlar için [WHATSAPP.md](WHATSAPP.md) belgesine bakın.

## Gizlilik

Belge işlemleri `127.0.0.1` üzerinde çalışan ve oturum anahtarıyla korunan yerel motorda gerçekleşir. Uygulama dosya içeriğini üçüncü taraf servislere göndermez. Geçici dosyalar işletim sisteminin geçici dizinindeki `atelier-docs` klasöründe, rastgele kimlikli çalışma alanlarında tutulur; 72 saatten eski uygulama çalışma alanları güvenli biçimde temizlenir.
