# Deployment & Authentication Setup Guide

This guide walks you through deploying the AI Image Generator to Railway with Docker and enabling Google Workspace SSO via Google OAuth 2.0.

---

## Prerequisites

- A [Railway](https://railway.app) account
- Your GitHub repository connected to Railway
- A Google Cloud project (can be the same one that provides your `GOOGLE_API_KEY`)
- Google Workspace domain (optional — needed only if you want to restrict access to your org)

---

## Part 1 — Set up Google OAuth credentials

### 1.1 Open Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Select the project you want to use (or create a new one).

### 1.2 Enable the required API

1. In the left sidebar go to **APIs & Services → Library**.
2. Search for **Google+ API** (or **People API**) and enable it.
   *(The OAuth scopes we use — `openid`, `email`, `profile` — are included automatically.)*

### 1.3 Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **Internal** if you only want Google Workspace users from your domain to log in.
   Choose **External** if you want to allow any Google account (you can still restrict by domain via `GOOGLE_ALLOWED_DOMAIN`).
3. Fill in:
   - **App name**: e.g. `AI Image Generator`
   - **User support email**: your email
   - **Developer contact**: your email
4. Under **Scopes**, click **Add or remove scopes** and add:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
5. Save and continue.

### 1.4 Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**.
2. Click **+ Create Credentials → OAuth client ID**.
3. Application type: **Web application**.
4. Name: e.g. `AI Image Generator - Railway`.
5. Under **Authorized redirect URIs**, add:
   ```
   https://your-app.railway.app
   ```
   *(Replace with your actual Railway domain. Add `http://localhost:8501` as well for local testing.)*
6. Click **Create**.
7. Copy the **Client ID** and **Client Secret** — you will need these in the next step.

> **Note:** The redirect URI must exactly match your `APP_URL` environment variable (no trailing slash).

---

## Part 2 — Deploy to Railway

### 2.1 Connect your GitHub repository

1. Log in to [railway.app](https://railway.app).
2. Click **New Project → Deploy from GitHub repo**.
3. Authorize Railway to access your GitHub account and select the `nano-banana-stand` repository.
4. Railway will detect the `Dockerfile` automatically (via `railway.toml`).

### 2.2 Add a persistent volume

Images, the SQLite database, and reference files need to survive deployments.

1. In your Railway project, click on the service.
2. Go to the **Volumes** tab → **Add Volume**.
3. Set the mount path to `/data`.
4. Railway will provision a persistent disk and mount it there.

### 2.3 Set environment variables

In the Railway service → **Variables** tab, add the following:

| Variable | Value | Required |
|---|---|---|
| `GOOGLE_API_KEY` | Your Google Gemini API key | For image generation |
| `OPENAI_API_KEY` | Your OpenAI key | Optional placeholder if you later enable DALL-E |
| `GOOGLE_CLIENT_ID` | OAuth Client ID from step 1.4 | For auth |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret from step 1.4 | For auth |
| `APP_URL` | `https://your-app.railway.app` | For auth — **no trailing slash** |
| `GOOGLE_ALLOWED_DOMAIN` | `yourcompany.com` | Optional — restricts to your Workspace domain |
| `DB_PATH` | `/data/db.sqlite3` | Persistent storage |
| `STORAGE_DIR` | `/data/images` | Persistent storage |
| `REFERENCES_DIR` | `/data/references` | Persistent storage |
| `PRESETS_PATH` | `/data/presets.yaml` | Persistent storage |

> **Tip:** Set `GOOGLE_ALLOWED_DOMAIN` to your Google Workspace domain (e.g. `acme.com`) to ensure only employees can sign in, even if the consent screen is set to External.

### 2.4 Deploy

1. Push your code to the branch connected to Railway, or trigger a manual redeploy.
2. Railway will build the Docker image and start the container.
3. Once deployed, click **View** to get your public URL (e.g. `https://your-app.railway.app`).
4. Go back to **Google Cloud Console → Credentials** and confirm that URL is listed as an authorized redirect URI.

---

## Part 3 — How authentication works

Once `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set:

1. Any visitor who is not signed in sees only a **"Sign in with Google"** button.
2. Clicking it starts the standard Google OAuth consent flow.
3. After consent, Google redirects back to your app with an auth code.
4. The app exchanges the code for user info, creates a server-side session in SQLite, and stores the session token in a browser cookie (7-day expiry).
5. Subsequent visits restore the session from the cookie — no re-login needed for 7 days.
6. If `GOOGLE_ALLOWED_DOMAIN` is set, users from other domains are rejected after the Google consent screen.
7. Users can sign out via the **Sign out** button in the sidebar.

### Disabling authentication (local dev)

Authentication is entirely opt-in. If `GOOGLE_CLIENT_ID` is not set in the environment the app runs in open-access mode — no login required. This is the default for local development.

---

## Part 4 — Local development with OAuth

To test the OAuth flow locally:

1. Copy `.env.example` to `.env` and fill in `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and set:
   ```
   APP_URL=http://localhost:8501
   ```
2. In Google Cloud Console, add `http://localhost:8501` as an authorized redirect URI for your OAuth client.
3. Run the app:
   ```bash
   streamlit run app.py
   ```

> **Important:** Google OAuth requires HTTPS in production. Railway provides HTTPS automatically on its `.railway.app` domains.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `redirect_uri_mismatch` error from Google | The `APP_URL` env var doesn't exactly match the URI registered in Google Cloud Console. Check for trailing slashes or `http` vs `https`. |
| "Access restricted to @domain accounts" | The user signed in with a personal Gmail. Share the app URL only with workspace members, or switch the consent screen to **Internal**. |
| Images/database lost after redeploy | The Railway volume is not mounted. Confirm `/data` is the mount path and all four `*_PATH`/`*_DIR` env vars point to `/data/...`. |
| Blank page / app won't start | Check Railway logs. The most common cause is a missing env var (`GOOGLE_CLIENT_ID` present without `GOOGLE_CLIENT_SECRET`, or vice versa). |
| Cookie not persisting between page refreshes | Make sure `APP_URL` uses the exact public HTTPS URL — cookies set on a different origin are discarded. |
