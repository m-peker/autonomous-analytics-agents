# ☁️ Autonomous Analytics Agents — Sıfırdan GCP Deployment Rehberi

> Bu rehber, Google Cloud'u **hiç kullanmamış** biri için yazıldı.
> Her adımda ne yaptığını ve neden yaptığını açıklıyorum.
> Toplam süre: ~30 dakika.

---

## 📋 İçindekiler

1. [GCP Hesabı Açma](#1-gcp-hesabı-açma)
2. [gcloud CLI Kurulumu](#2-gcloud-cli-kurulumu)
3. [Proje Oluşturma](#3-proje-oluşturma)
4. [Faturalandırmayı Etkinleştirme](#4-faturalandırmayı-etkinleştirme)
5. [API'leri Etkinleştirme](#5-apileri-etkinleştirme)
6. [API Key'leri Secret Manager'a Yükleme](#6-api-keyleri-secret-managera-yükleme)
7. [Storage Bucket Oluşturma](#7-storage-bucket-oluşturma)
8. [Docker Build & Push](#8-docker-build--push)
9. [Cloud Run'a Deploy](#9-cloud-runa-deploy)
10. [Test Etme](#10-test-etme)
11. [Önemli Linkler & Monitoring](#11-önemli-linkler--monitoring)

---

## 1. GCP Hesabı Açma

Google Cloud'da yeniysen:

1. https://cloud.google.com adresine git
2. **"Get started for free"** butonuna tıkla
3. Google hesabınla giriş yap
4. Kredi kartı bilgilerini gir *(ücretsiz kullanım için gerekiyor, ücret kesilmez)*
5. **$300 bedava kredi** hesabına yüklenir (90 gün geçerli)

> 🎉 Free tier sayesinde bu proje ayda **$0** maliyetle çalışır.
> Cloud Run: 2 milyon istek/ay bedava. Storage: 5 GB bedava. Secret Manager: 6 secret bedava.

---

## 2. gcloud CLI Kurulumu

`gcloud`, Google Cloud'u terminalden yönetmeni sağlayan komut satırı aracı.

### Windows (PowerShell)

```powershell
# PowerShell'i Yönetici olarak aç ve çalıştır:
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& "$env:Temp\GoogleCloudSDKInstaller.exe"
```

Kurulum sihirbazını takip et. **"Run gcloud init"** seçeneğini işaretle.

### macOS / Linux

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

> ❓ **Bu adım ne yapıyor?** Google Cloud ile konuşabilmek için bilgisayarına istemci kuruyor.

---

## 3. Proje Oluşturma

GCP'de her şey bir "proje" altında toplanır. Proje = senin çalışma alanın.

### Web'den (önerilen):

1. https://console.cloud.google.com adresine git
2. Üstteki proje seçiciye tıkla → **"NEW PROJECT"**
3. Proje adı: `analytics-agents` (veya istediğin bir isim)
4. **"CREATE"** butonuna tıkla
5. Proje ID'sini bir yere not et (örnek: `analytics-agents-123456`)

### Terminalden:

```bash
gcloud projects create analytics-agents-${RANDOM} --name="Autonomous Analytics Agents"
```

> ❓ **Proje ID'si nedir?** Global olarak benzersiz bir isim. `analytics-agents-123456` gibi bir şey. Tüm komutlarda kullanacağız.

---

## 4. Faturalandırmayı Etkinleştirme

Cloud Run ve Storage kullanabilmek için faturalandırma hesabı bağlaman gerekir *(free tier içinde kalsan bile)*.

```bash
# Önce projeyi seç
gcloud config set project SENIN_PROJE_IDN

# Faturalandırma hesaplarını listele
gcloud billing accounts list

# Çıkan ID'yi kullanarak bağla (genelde XXXXXX-XXXXXX-XXXXXX formatında)
gcloud billing projects link SENIN_PROJE_IDN --billing-account=XXXXXX-XXXXXX-XXXXXX
```

Veya web'den: https://console.cloud.google.com/billing → projeyi seç → fatura hesabına bağla.

> ❓ **Ücret kesilir mi?** Free tier limitleri aşmadığın sürece hayır. Bu proje free tier içinde kalır.

---

## 5. API'leri Etkinleştirme

GCP'de her servis için API'yi açman gerekir. Tek seferlik bir işlem.

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com
```

> ❓ **Bunlar ne?** Cloud Run (uygulama çalıştırma), Artifact Registry (Docker image deposu), Secret Manager (şifre saklama), Cloud Storage (dosya deposu), Cloud Build (otomatik build).

---

## 6. API Key'leri Hazırlama (Opsiyonel: Secret Manager veya Env Var)

API anahtarlarını cloud'a yüklemek için **iki yol** var:

### 🟢 Seçenek A: Doğrudan Environment Variable (Basit & Önerilen)

Bu yöntemde API key'ler deploy sırasında doğrudan env var olarak geçilir. Cloud Run'da güvenli bir şekilde saklanır.

```bash
# Deploy adımında (Section 9) doğrudan geçersin.
# Başka bir adım gerekmiyor.
```

### 🟣 Seçenek B: Secret Manager (İleri Güvenlik)

Eğer ekstra güvenlik istiyorsan, API key'leri Secret Manager'a yükleyebilirsin:

```bash
echo -n "sk-senin-openai-keyin" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- --replication-policy=automatic
```

> ⚠️ **Secret Manager vs Env Var?**
> - **Env Var (önerilen)**: Deploy sırasında `--set-env-vars` ile geç. Basit, çalışır.
> - **Secret Manager**: `.env` dosyasına almamak isteyenler için. Ekstra kompleks.
> - **⚠️ HİPERİ ÖNEMLI**: İkisini karıştırma! Secret olarak yüklü olan bir key'i env var olarak geçmek hata verir (`Cannot update ... to string literal because it has already been set with a different type`). Eğer eski deployment'ında Secret var, önce `--clear-secrets` flag'i ile temizle.

---

## 7. Storage Bucket Oluşturma

Yüklenen dosyalar ve ChromaDB verileri için bir depo (bucket) oluşturuyoruz.

```bash
gcloud storage buckets create gs://SENIN_PROJE_IDN-analytics-agents-storage \
  --location=us-central1
```

> ❓ **Bucket nedir?** Bulutta klasör gibi düşün. Dosyaların kalıcı olarak saklandığı yer. Cloud Run'ın kendi diski geçicidir, bucket kalıcıdır.

---

## 8. Docker Build & Push

Uygulamayı Docker ile paketleyip Artifact Registry'ye yüklüyoruz.

```bash
# Önce Artifact Registry'de Docker repo'su oluştur
gcloud artifacts repositories create analytics-agents \
  --repository-format=docker \
  --location=us-central1

# Docker'ı GCP'ye yetkilendir
gcloud auth configure-docker us-central1-docker.pkg.dev

# Proje klasöründe Docker image'ı build et
docker build -t us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest .

# Image'ı GCP'ye push et (yükle)
docker push us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest
```

> ⏱️ Bu adım 3-5 dakika sürebilir. İlk build'de tüm Python paketleri indirilir.
>
> ❓ **Docker nedir?** Uygulamanı bir kutuya koyup her yerde aynı şekilde çalıştırmanı sağlar. GCP bu kutuyu alıp Cloud Run'da çalıştırır.

---

## 9. Cloud Run'a Deploy

Artık her şey hazır. Uygulamayı Cloud Run'a deploy ediyoruz.

```bash
gcloud run deploy analytics-agents \
  --image=us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=900 \
  --max-instances=3 \
  --set-env-vars="GCP_PROJECT=SENIN_PROJE_IDN,GCS_BUCKET_NAME=SENIN_PROJE_IDN-analytics-agents-storage,LLM_PROVIDER=openai,OPENAI_API_KEY=sk-senin-openai-keyin" \
  --clear-secrets
```

Komut çalıştıktan sonra şöyle bir çıktı göreceksin:

```
✓ Deploying new service...
  ✓ Creating Revision...
  ✓ Routing traffic...
  ✓ Setting IAM Policy...
Done.
Service URL: https://analytics-agents-xxxxxxxx-uc.a.run.app
```

> 🎉 **O URL senin canlı uygulaman!** Tarayıcıda aç.
>
> ⚠️ **Eğer hata verirse:** "Cannot update environment variable [OPENAI_API_KEY] to string literal because it has already been set with a different type." → Eski deployment'ında Secret var. Yukarıdaki komuta `--clear-secrets` flag'i ekle ve tekrar çalıştır.

---

## 10. Test Etme

```bash
# Tarayıcıda aç
# https://analytics-agents-xxxxxxxx-uc.a.run.app

# Veya terminalden test et
curl -I https://analytics-agents-xxxxxxxx-uc.a.run.app
# HTTP/2 200 gelmeli

# Logları görüntüle
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=analytics-agents" --limit=10
```

Bir Excel veya CSV dosyası yükle, bir soru yaz ve "Run 9-Agent Pipeline" butonuna tıkla. Agent'lar çalışmaya başlayacak!

---

## 11. Önemli Linkler & Monitoring

| Ne | Link |
|----|------|
| Cloud Run dashboard | https://console.cloud.google.com/run |
| Secret Manager | https://console.cloud.google.com/security/secret-manager |
| Cloud Storage | https://console.cloud.google.com/storage |
| Logs Explorer | https://console.cloud.google.com/logs |
| Billing (maliyet) | https://console.cloud.google.com/billing |

---

## 🔄 Güncelleme Yapma (Update)

Kodda değişiklik yaptığında tekrar deploy etmek için:

```bash
# 1. Yeni Docker image build et
docker build -t us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest .

# 2. Push et
docker push us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest

# 3. Cloud Run'ı güncelle
gcloud run deploy analytics-agents \
  --image=us-central1-docker.pkg.dev/SENIN_PROJE_IDN/analytics-agents/analytics-agents:latest \
  --region=us-central1
```

> Ya da tek komutla: `./scripts/deploy-gcp.sh`

---

## 🗑️ Temizleme (Her Şeyi Sil)

Projeyi silmek ve fatura gelmemesini garantilemek için:

```bash
# Cloud Run servisini sil
gcloud run services delete analytics-agents --region=us-central1 --quiet

# Storage bucket'ı sil
gcloud storage rm --recursive gs://SENIN_PROJE_IDN-analytics-agents-storage

# Secret'ları sil
gcloud secrets delete OPENAI_API_KEY --quiet
gcloud secrets delete ANTHROPIC_API_KEY --quiet
gcloud secrets delete GROQ_API_KEY --quiet

# Artifact Registry'yi sil
gcloud artifacts repositories delete analytics-agents --location=us-central1 --quiet

# Veya GCP projesini komple sil (her şeyi temizler):
# gcloud projects delete SENIN_PROJE_IDN
```

> ⚠️ Projeyi silersen **TÜM veriler kalıcı olarak silinir**. Emin olmadan yapma.

---

## 🐛 Sorun Giderme (Troubleshooting)

### "Permission denied" hatası
```bash
gcloud auth login
gcloud config set project SENIN_PROJE_IDN
```

### "Docker push" başarısız
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Cloud Run 503 hatası veriyor
```bash
# Logları kontrol et
gcloud logging read "resource.type=cloud_run_revision" --limit=20
# Büyük ihtimalle API key eksik veya yanlış
```

### Streamlit "Please wait..." de takılı kaldı
- Cloud Run memory'sini 4Gi yaptığından emin ol (2Gi bazen yetmez)
- `--timeout=900` olduğundan emin ol

### Fatura kesilir mi korkusu
- https://console.cloud.google.com/billing → "Budgets & alerts" → bütçe alarmı kur
- Örnek: $5 aylık bütçe, %50'de email alarmı


