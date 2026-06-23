# ☁️ Autonomous Analytics Agents — Zero to GCP Deployment Guide

> This guide is written for someone who has **never used Google Cloud** before.
> Each step explains what you're doing and why.
> Total time: ~30 minutes.

---

## 📋 Table of Contents

1. [Create a GCP Account](#1-create-a-gcp-account)
2. [Install gcloud CLI](#2-install-gcloud-cli)
3. [Create a Project](#3-create-a-project)
4. [Enable Billing](#4-enable-billing)
5. [Enable APIs](#5-enable-apis)
6. [Prepare API Keys (Env Var or Secret Manager)](#6-prepare-api-keys)
7. [Create a Storage Bucket](#7-create-a-storage-bucket)
8. [Docker Build & Push](#8-docker-build--push)
9. [Deploy to Cloud Run](#9-deploy-to-cloud-run)
10. [Test the Deployment](#10-test-the-deployment)
11. [Important Links & Monitoring](#11-important-links--monitoring)

---

## 1. Create a GCP Account

If you're new to Google Cloud:

1. Go to https://cloud.google.com
2. Click the **"Get started for free"** button
3. Sign in with your Google account
4. Enter your credit card details *(required for free tier, you won't be charged)*
5. **$300 free credit** is loaded into your account (valid for 90 days)

> 🎉 Thanks to the free tier, this project runs at **$0/month**.
> Cloud Run: 2 million requests/month free. Storage: 5 GB free. Secret Manager: 6 secrets free.

---

## 2. Install gcloud CLI

`gcloud` is the command-line tool that lets you manage Google Cloud from the terminal.

### Windows (PowerShell)

```powershell
# Open PowerShell as Administrator and run:
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& "$env:Temp\GoogleCloudSDKInstaller.exe"
```

Follow the installation wizard. Check the **"Run gcloud init"** option.

### macOS / Linux

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

> ❓ **What does this step do?** Installs a client on your machine so you can communicate with Google Cloud.

---

## 3. Create a Project

In GCP, everything lives under a "project." A project = your workspace.

### Via Web (recommended):

1. Go to https://console.cloud.google.com
2. Click the project selector at the top → **"NEW PROJECT"**
3. Project name: `analytics-agents` (or any name you like)
4. Click **"CREATE"**
5. Note down the Project ID (example: `analytics-agents-123456`)

### Via Terminal:

```bash
gcloud projects create analytics-agents-${RANDOM} --name="Autonomous Analytics Agents"
```

> ❓ **What is a Project ID?** A globally unique name. Something like `analytics-agents-123456`. We'll use it in all commands.

---

## 4. Enable Billing

To use Cloud Run and Storage, you must link a billing account *(even if you stay within the free tier)*.

```bash
# First, select your project
gcloud config set project YOUR_PROJECT_ID

# List your billing accounts
gcloud billing accounts list

# Link using the ID shown (usually XXXXXX-XXXXXX-XXXXXX format)
gcloud billing projects link YOUR_PROJECT_ID --billing-account=XXXXXX-XXXXXX-XXXXXX
```

Or via web: https://console.cloud.google.com/billing → select project → link to billing account.

> ❓ **Will I be charged?** No, as long as you stay within free tier limits. This project fits comfortably within the free tier.

---

## 5. Enable APIs

In GCP, you must enable the API for each service you want to use. This is a one-time step.

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com
```

> ❓ **What are these?** Cloud Run (run your app), Artifact Registry (store Docker images), Secret Manager (store secrets), Cloud Storage (file storage), Cloud Build (automated builds).

---

## 6. Prepare API Keys

There are **two ways** to provide API keys to the cloud:

### 🟢 Option A: Direct Environment Variables (Simple & Recommended)

With this method, API keys are passed directly as env vars during deployment. They're stored securely in Cloud Run.

```bash
# Pass directly in the deploy step (Section 9).
# No additional setup needed.
```

### 🟣 Option B: Secret Manager (Advanced Security)

If you want extra security, you can upload API keys to Secret Manager:

```bash
echo -n "sk-your-openai-key" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- --replication-policy=automatic
```

> ⚠️ **Secret Manager vs Env Var?**
> - **Env Var (recommended)**: Pass via `--set-env-vars` during deploy. Simple, works.
> - **Secret Manager**: For those who prefer not to use an `.env` file. Extra complexity.
> - **⚠️ CRITICAL**: Don't mix the two! Passing an already-stored Secret as an env var will error out (`Cannot update ... to string literal because it has already been set with a different type`). If a previous deployment used Secrets, clear them first with the `--clear-secrets` flag.

---

## 7. Create a Storage Bucket

Create a bucket for uploaded files and ChromaDB data.

```bash
gcloud storage buckets create gs://YOUR_PROJECT_ID-analytics-agents-storage \
  --location=us-central1
```

> ❓ **What is a bucket?** Think of it as a folder in the cloud. It's the persistent storage location for your files. Cloud Run's local disk is ephemeral (temporary); the bucket is permanent.

---

## 8. Docker Build & Push

Package the app with Docker and upload it to Artifact Registry.

```bash
# First, create a Docker repository in Artifact Registry
gcloud artifacts repositories create analytics-agents \
  --repository-format=docker \
  --location=us-central1

# Authenticate Docker with GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build the Docker image from the project folder
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest .

# Push (upload) the image to GCP
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest
```

> ⏱️ This step may take 3–5 minutes. All Python packages are downloaded during the first build.
>
> ❓ **What is Docker?** It packages your app into a container so it runs the same way everywhere. GCP takes this container and runs it on Cloud Run.

---

## 9. Deploy to Cloud Run

Everything is ready. Now deploy the app to Cloud Run.

```bash
gcloud run deploy analytics-agents \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=900 \
  --max-instances=3 \
  --set-env-vars="GCP_PROJECT=YOUR_PROJECT_ID,GCS_BUCKET_NAME=YOUR_PROJECT_ID-analytics-agents-storage,LLM_PROVIDER=openai,OPENAI_API_KEY=sk-your-openai-key" \
  --clear-secrets
```

After the command runs, you'll see output like this:

```
✓ Deploying new service...
  ✓ Creating Revision...
  ✓ Routing traffic...
  ✓ Setting IAM Policy...
Done.
Service URL: https://analytics-agents-xxxxxxxx-uc.a.run.app
```

> 🎉 **That URL is your live app!** Open it in a browser.
>
> ⚠️ **If you get an error:** "Cannot update environment variable [OPENAI_API_KEY] to string literal because it has already been set with a different type." → Your old deployment has a Secret mapping. Add the `--clear-secrets` flag to the command above and run it again.

---

## 10. Test the Deployment

```bash
# Open in browser
# https://analytics-agents-xxxxxxxx-uc.a.run.app

# Or test from terminal
curl -I https://analytics-agents-xxxxxxxx-uc.a.run.app
# Should return HTTP/2 200

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=analytics-agents" --limit=10
```

Upload an Excel or CSV file, type a question, and click "Run 9-Agent Pipeline." The agents will start working!

---

## 11. Important Links & Monitoring

| What | Link |
|------|------|
| Cloud Run dashboard | https://console.cloud.google.com/run |
| Secret Manager | https://console.cloud.google.com/security/secret-manager |
| Cloud Storage | https://console.cloud.google.com/storage |
| Logs Explorer | https://console.cloud.google.com/logs |
| Billing (costs) | https://console.cloud.google.com/billing |

---

## 🔄 Updating (Redeploy)

When you make code changes, redeploy with:

```bash
# 1. Build new Docker image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest .

# 2. Push
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest

# 3. Update Cloud Run
gcloud run deploy analytics-agents \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/analytics-agents/analytics-agents:latest \
  --region=us-central1
```

> Or with a single command: `./scripts/deploy-gcp.sh`

---

## 🗑️ Tear Down (Delete Everything)

To delete the project and guarantee no charges:

```bash
# Delete Cloud Run service
gcloud run services delete analytics-agents --region=us-central1 --quiet

# Delete Storage bucket
gcloud storage rm --recursive gs://YOUR_PROJECT_ID-analytics-agents-storage

# Delete secrets
gcloud secrets delete OPENAI_API_KEY --quiet
gcloud secrets delete ANTHROPIC_API_KEY --quiet
gcloud secrets delete GROQ_API_KEY --quiet

# Delete Artifact Registry
gcloud artifacts repositories delete analytics-agents --location=us-central1 --quiet

# Or delete the entire GCP project (cleans everything):
# gcloud projects delete YOUR_PROJECT_ID
```

> ⚠️ Deleting the project will **permanently delete ALL data**. Don't do this unless you're sure.

---

## 🐛 Troubleshooting

### "Permission denied" error
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### "Docker push" fails
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Cloud Run returns 503 errors
```bash
# Check the logs
gcloud logging read "resource.type=cloud_run_revision" --limit=20
# Most likely the API key is missing or incorrect
```

### Streamlit stuck on "Please wait..."
- Make sure Cloud Run has 4Gi of memory (2Gi is sometimes not enough)
- Make sure `--timeout=900` is set

### Worried about billing?
- https://console.cloud.google.com/billing → "Budgets & alerts" → set a budget alert
- Example: $5 monthly budget, 50% email alert

---

<p align="center">🎉 <b>Your app is now live on the internet!</b> Share the URL on LinkedIn, your GitHub profile, or your CV.</p>
