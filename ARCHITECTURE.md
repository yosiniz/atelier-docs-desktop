# Mimari

## Karar

Uygulama modüler monolith olarak tasarlanmıştır. Electron yalnızca güvenli masaüstü kabuğu ve yerel kaydetme diyaloğunu sağlar. React arayüzü belge işleme yapmaz; bellek/CPU ağırlıklı işler yerel Python motorunda izole servis modüllerine ayrılır.

```text
Electron (contextIsolation + sandbox)
  └─ React / TypeScript UI
       └─ HTTP 127.0.0.1:<dinamik-port> + oturum anahtarı
            └─ FastAPI
                 ├─ storage (doğrulama ve güvenli çalışma alanı)
                 ├─ jobs (sınırlı iş parçacığı havuzu, ilerleme ve iptal)
                 └─ services
                      ├─ pdf_service (PyMuPDF + pypdf)
                      ├─ image_service (Pillow)
                      ├─ conversion_service (python-docx + yerel dönüştürücüler)
                      ├─ office_service (DOCX/XLSX/CSV/PPTX düzenleme)
                      └─ ocr_service (isteğe bağlı yerel Tesseract)
```

## PDF metin düzenleme yaklaşımı

PDF akış tabanlı bir kelime işlemci formatı değildir. Motor önce metin bloklarının koordinatlarını ve baskın stilini çıkarır. Kullanıcı düzenleme yaptığında ilgili dikdörtgene gerçek PDF redaksiyonu uygulanır; bu adım kesişen metin operatörlerini içerik akışından siler. Ardından Unicode destekli yerel font gömülerek yeni metin aynı alana yazılır. Sonuç temizleme, çöp toplama ve deflate ile yeni revizyona kaydedilip yeniden açılarak doğrulanır.

Bu yöntem yalnızca beyaz kutu bindirme değildir. Karmaşık alt-küme fontları, dikey yazı, form XObject içindeki içerik ve akış tabanlı paragraf yeniden dizimi ayrıca ele alınmalıdır.

## Güvenlik sınırları

- Electron renderer içinde Node entegrasyonu kapalı, context isolation ve sandbox açıktır.
- Dosya adları normalize edilir; belge kimlikleri yalnızca 32 haneli hex kabul eder.
- Yükleme 250 MB ile sınırlıdır ve uzantı yanında içerik doğrulaması yapılır.
- İşlem çıktısı önce staging dosyasına yazılır ve doğrulamadan sonra atomik olarak etkin revizyona geçirilir.
- Harici servis ve telemetry yoktur.
- Üretim sidecar API'si her uygulama oturumunda üretilen rastgele anahtarı zorunlu tutar.
- PDF değişiklikleri revision klasörlerinde tutulur; staging çıktı doğrulanmadan etkin dosyanın yerini almaz.
- OOXML paketleri giriş sayısı ve toplam açılmış boyut sınırlarıyla ZIP bombalarına karşı kontrol edilir.
- Ağır sıkıştırma işlemleri iki işçiyle sınırlı kuyrukta çalışır; durum, ilerleme ve iptal API'si sunulur.
- Uygulamanın UUID biçimli ve 72 saatten eski geçici çalışma alanları başlangıçta temizlenir.
