Here's your **complete master plan** — fully documented, phase by phase.
new added.

---

# 🧠 PROJECT: Social Media Automation Agent

---

## 📋 REQUIREMENTS DOCUMENT

### Functional Requirements
- Monitor 20 user-defined accounts on Instagram, Twitter/X, YouTube
- Scrape/fetch posts from the past 7 days
- Score and filter posts by engagement
- Send selected posts to user via Telegram with approve/reject buttons
- Store approved posts in a local SQLite database
- Display a calendar/schedule view (web UI)
- Auto-post OR browser-controlled posting via Playwright (no API cost)
- User triggers final post with one click

### Non-Functional Requirements
- **100% free to run**
- Hosted on AWS Free Tier (EC2 t2.micro)
- No paid APIs required
- Browser automation as fallback for posting (Playwright)
- Modular — each platform is a separate module

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────┐
│              SCHEDULER (cron)           │
│         Runs every 24 hours             │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │   SCRAPER MODULE │
        │  Instagram/X/YT  │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  FILTER & SCORE  │
        │  (engagement)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  TELEGRAM BOT    │◄──── You approve/reject
        │  Send previews   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  SQLITE DB       │
        │  Schedule queue  │
        └────────┬────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
┌────▼────┐           ┌──────▼──────┐
│ CALENDAR │           │ AUTO-POSTER  │
│ WEB UI   │           │ Playwright   │
│(schedule)│           │(browser bot) │
└──────────┘           └─────────────┘
```

---

## 📁 PROJECT FILE STRUCTURE

```
social-agent/
├── main.py                  # Entry point
├── config.py                # All settings & account lists
├── scheduler.py             # Cron job logic
├── database.py              # SQLite setup & queries
│
├── scrapers/
│   ├── instagram.py         # Instagram scraper
│   ├── twitter.py           # Twitter/X scraper
│   └── youtube.py           # YouTube scraper
│
├── filters/
│   └── scorer.py            # Engagement scoring logic
│
├── telegram_bot/
│   ├── bot.py               # Telegram bot
│   └── handlers.py          # Approve/reject handlers
│
├── poster/
│   ├── browser_poster.py    # Playwright browser automation
│   ├── instagram_post.py    # Instagram posting logic
│   ├── twitter_post.py      # Twitter posting logic
│   └── youtube_post.py      # YouTube posting logic
│
├── web_ui/
│   ├── app.py               # Flask calendar UI
│   ├── templates/
│   │   └── calendar.html    # Notion-style calendar view
│   └── static/
│       └── style.css
│
├── requirements.txt
├── .env                     # Secrets (never commit)
├── deploy/
│   └── setup_aws.sh         # AWS setup script
└── README.md
```

---

## 🤖 AI BUILD PROMPT (Phase by Phase)

Copy each phase prompt and give it to your AI (Claude, Cursor, etc.)

---

### ✅ PHASE 1 — Project Setup & Database

```
You are a senior Python developer building a social media automation agent.

TASK: Set up the project foundation.

Create the following:

1. `requirements.txt` with these libraries:
   - playwright, apify-client, feedparser
   - python-telegram-bot==20.7
   - flask, flask-cors
   - schedule, python-dotenv
   - sqlite3 (built-in), requests, Pillow

2. `config.py`:
   - ACCOUNTS dict with keys: instagram, twitter, youtube
   - Each is a list of 20 usernames (placeholder values)
   - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (from .env)
   - POST_TIMES list: ["09:00", "13:00", "18:00", "21:00"]
   - LOOKBACK_DAYS = 7

3. `database.py`:
   - SQLite database called agent.db
   - Table: posts (id, platform, author, content, media_url,
     engagement_score, status, scheduled_time, created_at)
   - Status values: 'pending', 'approved', 'rejected', 'posted'
   - Functions: save_post(), get_pending(), approve_post(),
     reject_post(), get_scheduled(), mark_posted()

Output all files completely with no placeholders.
```

---

### ✅ PHASE 2 — Scrapers

```
You are building scrapers for a social media automation agent.
Database schema from Phase 1 is already set up.

TASK: Build 3 scraper modules.

1. `scrapers/youtube.py`:
   - Use YouTube RSS feed (free, no API key):
     https://www.youtube.com/feeds/videos.xml?user=USERNAME
   - Fetch videos from past 7 days
   - Extract: title, video_url, thumbnail, view_count (if available)
   - Save to DB with platform='youtube'

2. `scrapers/twitter.py`:
   - Use nitter.net RSS feeds (free Twitter scraping):
     https://nitter.net/USERNAME/rss
   - Fetch tweets from past 7 days
   - Extract: text, media_url, likes+retweets as engagement
   - Save to DB with platform='twitter'

3. `scrapers/instagram.py`:
   - Use Apify's free Instagram scraper actor via their free tier
   - Actor ID: 'apify/instagram-scraper'
   - Fetch posts from past 7 days for each account
   - Extract: caption, image_url, likes+comments as engagement
   - Save to DB with platform='instagram'

4. `filters/scorer.py`:
   - Score each post 0-100 based on engagement
   - Formula: score = min(100, (likes*1 + comments*3 + shares*2) / 100)
   - Update engagement_score in DB

All functions must handle errors gracefully and log to console.
```

---

### ✅ PHASE 3 — Telegram Bot

```
You are building a Telegram bot for a social media automation agent.

TASK: Build the full Telegram approval bot.

Using python-telegram-bot v20:

1. `telegram_bot/bot.py`:
   - Bot that polls for updates
   - On /start: show instructions
   - On /pending: show all pending posts
   - Each post shown as a message with:
     * Platform icon (📸 🐦 📺)
     * Author name
     * Content preview (first 200 chars)
     * Engagement score
     * Media image if available
     * Two inline buttons: ✅ Approve | ❌ Reject
   - On approve: ask user to pick a time slot from POST_TIMES
   - On time selected: save to DB as 'approved' with scheduled_time
   - On reject: mark as 'rejected' in DB
   - Send confirmation message after each action

2. `telegram_bot/handlers.py`:
   - CallbackQueryHandler for approve/reject/time buttons
   - All button callbacks properly handled
   - Error handling for network issues

The bot should feel clean and easy to use on mobile.
```

---

### ✅ PHASE 4 — Browser Poster (Playwright)

```
You are building a browser automation posting module.

TASK: Build Playwright-based auto-poster for Instagram, Twitter, YouTube.

1. `poster/browser_poster.py`:
   - Playwright async browser controller
   - Headless=False option (so user can see what's happening)
   - Session cookies saved to sessions/ folder per platform
   - Login once, reuse session

2. `poster/instagram_post.py`:
   - Function: post_to_instagram(image_path, caption)
   - Uses Playwright to open Instagram web
   - Navigates to upload flow
   - Uploads image, pastes caption, submits
   - Returns success/failure

3. `poster/twitter_post.py`:
   - Function: post_to_twitter(text, media_path=None)
   - Uses Playwright to open Twitter web
   - Types tweet text, attaches media if provided
   - Clicks post button
   - Returns success/failure

4. `poster/youtube_post.py`:
   - Function: post_to_youtube(video_path, title, description)
   - Uses Playwright to open YouTube Studio
   - Uploads video, fills title/description
   - Sets visibility, submits
   - Returns success/failure

IMPORTANT:
- Save login sessions as cookies to avoid re-login every time
- Add random delays between actions (1-3 seconds) to appear human
- Screenshot on failure for debugging
- All functions are async
```

---

### ✅ PHASE 5 — Calendar Web UI

```
You are building a web UI for a social media scheduling agent.

TASK: Build a Notion-style calendar view using Flask.

1. `web_ui/app.py`:
   - Flask app on port 5000
   - Route GET /: show calendar view
   - Route GET /api/scheduled: return JSON of all scheduled posts
   - Route POST /api/reschedule: change post time
   - Route POST /api/post-now: trigger immediate posting
   - Route GET /api/status: show today's posting status

2. `web_ui/templates/calendar.html`:
   - Clean modern UI (dark or light theme)
   - Weekly calendar grid (Mon-Sun)
   - Each scheduled post shown as a card on its day/time
   - Card shows: platform icon, thumbnail, caption preview
   - Click card: expand to full preview
   - Drag-and-drop to reschedule (use SortableJS CDN)
   - "Post Now" button on each card
   - Color coded by platform: blue=Twitter, pink=Instagram, red=YouTube
   - Mobile responsive

Style it like a professional tool. Clean, minimal, functional.
```

---

### ✅ PHASE 6 — Scheduler & Main Entry

```
You are finalizing a social media automation agent.

TASK: Build the main runner and scheduler.

1. `scheduler.py`:
   - Uses the `schedule` library
   - Every day at 8AM: run all scrapers, score posts, send to Telegram
   - Every hour: check DB for posts due to be posted, trigger browser_poster
   - Run continuously in background thread

2. `main.py`:
   - Start Flask web UI in a thread
   - Start Telegram bot in a thread  
   - Start scheduler in main thread
   - Print startup banner with local IP for web UI
   - Handle graceful shutdown (Ctrl+C)

3. `deploy/setup_aws.sh`:
   - Bash script for AWS EC2 Ubuntu setup
   - Installs Python 3.11, pip, playwright, all requirements
   - Sets up systemd service to auto-start on reboot
   - Opens ports 5000 (web UI) and sets up firewall rules
   - Prints final setup instructions

4. `README.md`:
   - Step by step setup guide
   - How to add accounts to config.py
   - How to get Telegram bot token
   - How to deploy to AWS Free Tier
   - Troubleshooting section
```

---

## 🪜 YOUR STEP-BY-STEP GUIDE

Here's exactly what we'll do together, one step at a time:

**Step 1** → I generate Phase 1 code for you right now
**Step 2** → You set up Python on your computer (I guide you)
**Step 3** → You create your Telegram bot (5 minutes, I walk you through it)
**Step 4** → We run Phase 2 scrapers and test them
**Step 5** → We set up Playwright login sessions for your accounts
**Step 6** → We deploy to AWS Free Tier together
**Step 7** → Full system live test

---

**Ready to start Step 1?**
Just say **"Start Phase 1"** and I'll generate the full working code for the project setup and database right now.