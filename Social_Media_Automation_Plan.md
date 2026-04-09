# Social Media Automation — Free Tier Plan

## Architecture Overview

FastCron (daily trigger) → Render Free API → Google Drive Check → Groq Caption Gen → Post to Instagram + LinkedIn

Total cost: $0/month

---

## Tech Stack

| Component         | Service                | Cost | Notes                                      |
|--------------------|------------------------|------|--------------------------------------------|
| Cron trigger       | FastCron               | Free | 1 daily HTTP call to your API              |
| Backend API        | Render free web service| Free | 750 hrs/month, sleeps after 15min idle     |
| File storage       | Google Drive API       | Free | Shared folder with service account         |
| Caption generation | Groq API (Llama 3)     | Free | 14.4K tokens/min, more than enough         |
| Instagram posting  | Instagram Graph API    | Free | Requires Business/Creator account          |
| LinkedIn posting   | LinkedIn API           | Free | OAuth 2.0, post to personal profile        |

---

## Phase 1 — Accounts & API Keys (Day 1)

### 1.1 Google Cloud (Drive API)
- Go to console.cloud.google.com
- Create a new project "social-media-bot"
- Enable Google Drive API
- Create a Service Account → download JSON key
- Create a Drive folder for your posts
- Share that folder with the service account email (viewer access is enough)

### 1.2 Groq API
- Sign up at console.groq.com
- Get free API key
- Model to use: llama-3.3-70b-versatile (or latest available)

### 1.3 Instagram Graph API
- You need an Instagram Business or Creator account (link to a Facebook Page)
- Go to developers.facebook.com → create app → add Instagram Graph API
- Generate a long-lived access token (valid 60 days, auto-refresh in code)
- Required permissions: instagram_basic, instagram_content_publish, pages_read_engagement

### 1.4 LinkedIn API
- Go to linkedin.com/developers → create app
- Request "Share on LinkedIn" (w_member_social) permission
- Set up OAuth 2.0 flow to get access token
- Store refresh token for auto-renewal

### 1.5 Render
- Sign up at render.com (GitHub login)
- Will deploy later in Phase 3

### 1.6 FastCron
- Sign up at fastcron.com (free plan)
- Will configure later in Phase 3

---

## Phase 2 — Build the App (Day 2-3)

### 2.1 Project Structure

```
Social_Media_Postings/
├── app.py                  # Main Flask/FastAPI app
├── services/
│   ├── drive_checker.py    # Google Drive polling
│   ├── caption_generator.py# Groq LLM caption generation
│   ├── instagram_poster.py # Instagram Graph API posting
│   └── linkedin_poster.py  # LinkedIn API posting
├── utils/
│   ├── token_manager.py    # OAuth token refresh logic
│   └── state.py            # Track last checked timestamp
├── requirements.txt
├── render.yaml             # Render deployment config
├── .env.example            # Template for env vars
└── README.md
```

### 2.2 Core Flow (/api/run endpoint)

```
1. Receive HTTP GET from FastCron
2. Load last_checked timestamp (from env var or small JSON file)
3. Query Google Drive API: list files modified after last_checked
4. If no new files → return 200 "No new posts"
5. For each new file:
   a. Download the image from Drive
   b. Read companion .txt file (if exists) for context/topic
   c. Send context to Groq API → get Instagram caption + LinkedIn caption
   d. Upload image to Instagram container → publish
   e. Upload image + caption to LinkedIn → publish
   f. Log success/failure
6. Update last_checked to now
7. Return 200 with summary
```

### 2.3 Drive Folder Structure

```
My Posts/
├── post_2025_01_15.png          # Image to post
├── post_2025_01_15.txt          # Optional: topic/context for caption
├── post_2025_01_20.jpg
├── post_2025_01_20.txt
└── ...
```

Rules:
- Each post = 1 image file (png/jpg)
- Optional .txt file with same name = context for AI caption
- If no .txt file, caption is generated from image filename + generic prompt

### 2.4 Caption Generation Prompt (Groq)

```
You are a social media manager. Generate two captions for this post:

Topic/Context: {context_from_txt_file}
Platform 1: Instagram (casual, emoji, hashtags, max 2200 chars)
Platform 2: LinkedIn (professional, insightful, no hashtags in body, max 3000 chars)

Return JSON:
{
  "instagram": "caption here",
  "linkedin": "caption here"
}
```

### 2.5 Key Environment Variables

```
GOOGLE_SERVICE_ACCOUNT_JSON=<base64 encoded service account key>
DRIVE_FOLDER_ID=<your shared folder ID>
GROQ_API_KEY=<your groq key>
INSTAGRAM_ACCESS_TOKEN=<long-lived token>
INSTAGRAM_ACCOUNT_ID=<your IG business account ID>
LINKEDIN_ACCESS_TOKEN=<oauth token>
LINKEDIN_PERSON_URN=<urn:li:person:YOUR_ID>
LAST_CHECKED=<ISO timestamp, updated after each run>
```

---

## Phase 3 — Deploy & Connect (Day 4)

### 3.1 Deploy to Render
- Push code to github.com/abdulrehmann231/Social_Media_Postings
- Go to Render dashboard → New Web Service
- Connect your GitHub repo
- Settings:
  - Runtime: Python 3
  - Build command: pip install -r requirements.txt
  - Start command: gunicorn app:app (or uvicorn app:app for FastAPI)
  - Plan: Free
- Add all environment variables from 2.5
- Deploy → note your URL: https://social-media-postings.onrender.com

### 3.2 Configure FastCron
- Log into fastcron.com
- Create new cron job:
  - URL: https://social-media-postings.onrender.com/api/run
  - Method: GET
  - Schedule: Once daily (e.g., 9:00 AM your timezone)
  - Timeout: 120 seconds (to handle Render cold start + API calls)
- Enable failure notifications to your email

### 3.3 Test
- Upload a test image + .txt to your Drive folder
- Manually trigger the FastCron job (or hit the URL in browser)
- Verify posts appear on Instagram and LinkedIn
- Check Render logs for any errors

---

## Known Limitations & Workarounds

### Render cold start
- Free tier sleeps after 15 min of inactivity
- FastCron will wait ~30s for cold start, then your code runs
- Set FastCron timeout to 120s to be safe

### Instagram token expiry
- Long-lived tokens last 60 days
- Add auto-refresh logic in token_manager.py
- Groq sends you an email reminder (or add a check in your code)

### LinkedIn token expiry
- OAuth tokens expire (60 days for most apps)
- Store refresh token, auto-renew on each run

### Rate limits
- Groq free: 14,400 tokens/min, 30 requests/min — plenty for 1 post/day
- Instagram: 25 content publishes per 24 hours
- LinkedIn: 100 API calls per day for share endpoints

### Image hosting for Instagram
- Instagram Graph API needs a publicly accessible image URL
- Option A: Use the Google Drive direct link (if file is public)
- Option B: Upload to Imgur free API first, use that URL
- Option C: Use a free image hosting service

---

## Optional Enhancements (Later)

- Add a simple web dashboard (React on Vercel) to preview captions before posting
- Add Twitter/X posting via their free API tier
- Add scheduling (queue posts for specific times)
- Add analytics tracking (store post performance in a free Supabase DB)
- Add image optimization/resizing before posting
- Add A/B testing for captions (generate 2, pick the one with better engagement next cycle)

---

## Quick Start Checklist

- [ ] Create Google Cloud project + service account
- [ ] Create Drive folder, share with service account
- [ ] Get Groq API key
- [ ] Set up Instagram Business account + Facebook Developer app
- [ ] Set up LinkedIn Developer app + OAuth
- [ ] Build the Flask/FastAPI app
- [ ] Test locally with all APIs
- [ ] Push to GitHub repo
- [ ] Deploy on Render (free tier)
- [ ] Set up FastCron daily trigger
- [ ] Upload first test post to Drive
- [ ] Verify end-to-end flow
- [ ] Done! 🚀
