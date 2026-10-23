# Atelier Docs WhatsApp Botu

WhatsApp entegrasyonu, resmi WhatsApp Business Cloud API webhook'u üzerinden gelen dosyaları mevcut Atelier Docs motoruyla dönüştürür ve sonucu aynı kullanıcıya geri gönderir.

## Desteklenen komutlar

- PDF + `Word yap`
- PDF + `PNG yap` veya `JPG yap` (her sayfa ayrı gönderilir)
- PDF + `PDF sıkıştır`
- PNG/JPG/WebP/BMP/TIFF/GIF + `JPG yap`, `PNG yap`, `WEBP yap` veya `PDF yap`
- DOCX/XLSX/CSV/PPTX + `PDF yap`

Komut dosyanın açıklamasına yazılabilir. Dosya ve komut ayrı mesajlarla, herhangi bir sırada ve 30 dakika içinde de gönderilebilir.

## Meta tarafında gerekenler

1. Meta Business hesabında bir uygulama ve WhatsApp ürünü oluşturun.
2. WhatsApp Business telefon numarasının `Phone Number ID` değerini alın.
3. Üretim için süreli deneme anahtarı yerine uygun kalıcı erişim anahtarı oluşturun.
4. Meta uygulamasının `App Secret` değerini alın.
5. Rastgele ve tahmin edilmesi güç bir webhook doğrulama anahtarı belirleyin.

Gizli değerleri repoya yazmayın. `.env.example` dosyasını `.env` olarak kopyalayıp yalnızca sunucuda doldurun:

```env
ATELIER_API_TOKEN=uzun-rastgele-yerel-api-anahtari
WHATSAPP_ACCESS_TOKEN=meta-erisim-anahtari
WHATSAPP_PHONE_NUMBER_ID=telefon-numarasi-kimligi
WHATSAPP_VERIFY_TOKEN=uzun-rastgele-webhook-anahtari
WHATSAPP_APP_SECRET=meta-uygulama-sirri
WHATSAPP_GRAPH_VERSION=v24.0
WHATSAPP_ALLOWED_NUMBERS=905xxxxxxxxx
```

`WHATSAPP_ALLOWED_NUMBERS` boş bırakılırsa işletme numarasına mesaj gönderebilen herkes kabul edilir. İlk kullanımda yalnızca kendi numaranızı yazmanız önerilir. Numaraları `+` ve boşluk olmadan, virgülle ayırın.

## Çalıştırma

```bash
docker compose -f docker-compose.whatsapp.yml up -d --build
```

Sağlık kontrolü:

```bash
curl http://127.0.0.1:8000/api/health
```

Webhook'un Meta tarafından erişilebilmesi için bu servis geçerli TLS sertifikalı, herkese açık bir HTTPS alan adında çalışmalıdır. Callback adresi:

```text
https://alan-adiniz.example/api/integrations/whatsapp/webhook
```

Meta webhook ayarındaki doğrulama anahtarı `WHATSAPP_VERIFY_TOKEN` ile aynı olmalı ve `messages` alanına abone olunmalıdır. POST webhook gövdeleri `X-Hub-Signature-256` ve `WHATSAPP_APP_SECRET` ile doğrulanır.

## Güvenlik ve gizlilik

- Dosya uzantısının yanında gerçek PDF, görsel veya OOXML yapısı da doğrulanır.
- Meta'nın bildirdiği SHA-256 mevcutsa indirilen dosyayla karşılaştırılır.
- Webhook tekrarları mesaj kimliğiyle tekilleştirilir.
- İşlenen dosyalar rastgele geçici klasörde tutulur ve gönderimden sonra silinir.
- Diğer Atelier Docs API uçları `ATELIER_API_TOKEN` ile korunmalıdır.
- Erişim anahtarları ve belge içerikleri loglara yazılmaz.
