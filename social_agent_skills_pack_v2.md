# 🤖 Social Media Agent — Skills Pack v2
> Updated with: Scraped Posts page, Full preview modal, Smart default time, Telegram confirmation + UI link

---

## 📦 SKILL 1 — Python Project Architecture & Database
*(unchanged from v1 — see previous skills pack)*

---

## 📦 SKILL 2 — Web Scraping & Social Media Data Fetching
*(unchanged from v1 — see previous skills pack)*

---

## 📦 SKILL 3 — Telegram Bot (UPDATED)

**What changed:** After approving a post, bot asks when to post it with smart default time. After scheduling, sends a confirmation + link to calendar UI.

```
SKILL: Telegram Bot Developer (python-telegram-bot v20) — Smart Scheduler

You are building a Telegram bot for a social media automation agent.
Library: python-telegram-bot==20.7 (async)

SMART DEFAULT TIME BEHAVIOUR:
- Store the last used schedule time in SQLite table: user_preferences(key, value)
- key = 'default_post_time', value = '19:00' (24hr format)
- On first use: show full time picker (buttons for each slot in POST_TIMES config)
- On every use after: show the default time as the FIRST button, pre-selected
- User can tap default to confirm OR tap "Change time" to see all options
- Whenever user picks a time, save it as the new default immediately

APPROVAL FLOW (step by step):
1. Bot sends post preview card with ✅ Approve | ❌ Reject buttons
2. User taps ✅ Approve
3. Bot replies:
   "📅 When to post this?
    Last used: 7:00 PM  ← tap to confirm
    [✅ 7:00 PM]  [🕐 Change time]"
4. If user taps the default time → confirm and schedule
5. If user taps "Change time" → show all time slot buttons from POST_TIMES
6. After scheduling, bot sends:
   "✅ Scheduled for [DATE] at [TIME]
    Platform: [Instagram/Twitter/YouTube]
    📆 View your calendar → http://[YOUR_EC2_IP]:5000"

TELEGRAM MESSAGE TEMPLATES:

Post preview card:
---
{ICON} *{AUTHOR}*
📊 Score: {score}/100 | 👍 {likes} | 💬 {comments}

{content_preview — first 200 chars}...
---
[✅ Approve]  [❌ Reject]

Time confirmation:
---
📅 *When should this go out?*

Last used: *{default_time}*
[✅ Use {default_time}]  [🕐 Change]
---

Scheduled confirmation:
---
✅ *Scheduled!*

📸/🐦/📺 {author} — {platform}
🗓 {date} at {time}

View your schedule:
👉 http://{EC2_IP}:5000
---

CALLBACK DATA FORMAT:
- approve:{post_id}
- reject:{post_id}
- use_default_time:{post_id}
- change_time:{post_id}
- schedule:{post_id}:{time_24hr}:{date_iso}

COMMANDS:
/start    — welcome + instructions
/pending  — show all pending posts (5 at a time, paginated)
/scheduled — show today's queue
/status   — last scrape time, posts queued, next post time
/settime  — manually set your default time
/help     — all commands

RULES:
- Always await query.answer() before sending follow-up messages
- Use ParseMode.MARKDOWN_V2 — escape: . ! ( ) - = + # | { }
- If media download fails → send text-only preview
- All errors: log + send "⚠️ Something went wrong, try /pending again"
- Store default_time in DB — never hardcode it
```

---

## 📦 SKILL 4 — Playwright Browser Automation
*(unchanged from v1 — see previous skills pack)*

---

## 📦 SKILL 5 — Flask Web UI (UPDATED — 2 pages + modal)

**What changed:** Two separate pages (Scraped Posts feed + Calendar), full post preview modal with Post It button, schedule picker in modal with smart default time.

```
SKILL: Flask Web Developer — 2-Page Social Agent Dashboard

You are building a 2-page Flask dashboard for a social media automation agent.
Backend: Flask + SQLite. Frontend: Vanilla JS + CSS. No React needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 1 — /posts  (Scraped Posts Feed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PURPOSE: Show all scraped posts. User browses, clicks a post, previews it,
         clicks "Post it" → picks time → it goes to calendar.

LAYOUT:
- Top nav bar: [📸 Instagram] [🐦 Twitter] [📺 YouTube] filter tabs + [All]
- Search bar (filter by keyword in caption)
- Masonry or 3-column card grid of post cards
- Each card shows: thumbnail image, platform badge, author name,
  engagement score bar (0-100), caption preview (first 80 chars), date scraped

POST CARD CLICK → MODAL:
- Full-screen overlay modal (not a new page)
- Modal contains:
  LEFT SIDE: large image/thumbnail
  RIGHT SIDE:
    - Platform icon + author name
    - Full caption (scrollable if long)
    - Engagement stats: 👍 likes  💬 comments  🔁 shares  👁 views
    - Score badge (colour: green>70, amber 40-70, red<40)
    - Original post link (open in new tab)
    - [Post it] button (primary, teal)  [Skip] button (ghost)

POST IT BUTTON → SCHEDULE PICKER (inside same modal, replaces content):
- Title: "When do you want to post this?"
- Shows: default time as a large highlighted button at top
  Example: [⭐ 7:00 PM  (last used)]
- Below it: grid of other available time slots
  Example: [9:00 AM]  [1:00 PM]  [6:00 PM]  [9:00 PM]
- Date picker: defaults to today, can pick next 7 days
- [Confirm Schedule] button
- On confirm: POST to /api/posts/schedule → close modal → show toast "✅ Scheduled!"
- Save chosen time as new default via /api/preferences/default_time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 2 — /calendar  (Schedule Calendar)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PURPOSE: See all scheduled posts in a weekly calendar view.
         Drag to reschedule. Click to edit or delete.

LAYOUT:
- Top nav: week selector (← prev week | This Week | next week →)
- 7 column grid (Mon–Sun), each column has a date header
- Today's column has a subtle highlight background
- Each scheduled post is a card in the correct day column

POST CARD IN CALENDAR:
- Thumbnail (small, 48x48)
- Platform icon (colored: pink=Instagram, blue=Twitter, red=YouTube)
- Scheduled time badge (e.g. "7:00 PM")
- Author name
- Caption first 40 chars
- On click → small popover with: full caption, [Edit time] [Delete] [Post Now]

DRAG & DROP:
- SortableJS from CDN (https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js)
- Dragging a card to another day column → calls POST /api/posts/reschedule
- Toast notification confirms new time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHARED NAV BAR (top of both pages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Left:  🤖 Social Agent  (logo/title)
Center: [📋 Posts]  [📆 Calendar]  (nav links, highlight active)
Right:  🔄 Run Scraper Now  |  🟢 System: OK  (status dot)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLASK API ROUTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET  /posts                   → render posts.html
GET  /calendar                → render calendar.html
GET  /api/posts/scraped       → JSON: all posts (status=pending), filterable by platform/keyword
GET  /api/posts/scheduled     → JSON: scheduled posts grouped by date
POST /api/posts/schedule      → body: {post_id, date, time} → schedule post
POST /api/posts/reschedule    → body: {post_id, new_date, new_time}
POST /api/posts/delete        → body: {post_id}
POST /api/posts/post-now      → body: {post_id} → trigger immediate posting
GET  /api/preferences         → return user preferences JSON
POST /api/preferences/default_time → body: {time} → save default time
GET  /api/status              → {last_scrape, posts_queued, system_ok}
POST /api/scraper/run         → trigger manual scrape run

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theme: Dark (#0f0f0f bg, #1a1a1a cards, #2a2a2a borders)
Accent colors:
  - Instagram: #E1306C (pink)
  - Twitter:   #1DA1F2 (blue)
  - YouTube:   #FF0000 (red)
  - Primary action: #00C896 (teal)
  - Warning: #F5A623 (amber)

Typography: system-ui, -apple-system, sans-serif
Modal overlay: rgba(0,0,0,0.85) backdrop, card slides up on open
Toasts: bottom-right, auto-dismiss after 3s, green=success red=error
Mobile responsive: cards stack to 1 column on <600px

JAVASCRIPT:
- Fetch all data via REST API on page load
- Re-fetch every 60 seconds (auto-refresh)
- Store default_time in localStorage as backup cache
- Keyboard: Escape closes modal
- After scheduling: remove card from pending grid, show toast
```

---

## 📦 SKILL 6 — DevOps: AWS Free Tier Deployment
*(unchanged from v1 — see previous skills pack)*

---

## 📦 SKILL 7 — Smart Default Time Logic (NEW)

**Use this when:** Building the schedule time picker in both the web UI AND the Telegram bot.

```
SKILL: Smart Default Time — Persistent User Preference

PURPOSE: Every time the user schedules a post, remember the last time they
picked. Pre-fill it next time so they don't have to re-enter it.

DATABASE:
Table: user_preferences
  key   TEXT PRIMARY KEY
  value TEXT
  updated_at DATETIME

Key used: 'default_post_time'   Value format: '19:00' (24hr)
Key used: 'default_post_date_offset'  Value: '0' (0=today, 1=tomorrow, etc.)

PYTHON FUNCTIONS (in database.py):

def get_default_time() -> str:
    """Returns stored default time, or '19:00' if not set yet."""

def set_default_time(time_24hr: str) -> None:
    """Saves new default time. Called every time user confirms a schedule."""

def format_time_display(time_24hr: str) -> str:
    """Converts '19:00' → '7:00 PM' for display."""

def get_time_slots() -> list[dict]:
    """Returns all available time slots from config.POST_TIMES,
    with the default time marked: [{'time':'09:00','display':'9:00 AM','is_default':False}, ...]
    Default slot is always first in the list."""

RULES:
- Default time is ALWAYS shown first / highlighted / pre-selected
- User must actively choose to change it — one tap to confirm default
- Every confirmed schedule → immediately update default (even if same time)
- If user cancels scheduling → do NOT update default
- Display times in 12hr format (7:00 PM) but store in 24hr ('19:00')
- In Telegram: default shown as first inline button with ⭐ prefix
- In Web UI: default shown as large highlighted button above the grid

WEB UI SCHEDULE PICKER HTML PATTERN:
<div class="time-picker">
  <button class="time-btn default" data-time="19:00" onclick="selectTime(this)">
    ⭐ 7:00 PM  (last used)
  </button>
  <div class="time-grid">
    <button class="time-btn" data-time="09:00" onclick="selectTime(this)">9:00 AM</button>
    <button class="time-btn" data-time="13:00" onclick="selectTime(this)">1:00 PM</button>
    <button class="time-btn" data-time="18:00" onclick="selectTime(this)">6:00 PM</button>
    <button class="time-btn" data-time="21:00" onclick="selectTime(this)">9:00 PM</button>
  </div>
</div>

TELEGRAM BUTTON PATTERN:
Row 1: [⭐ 7:00 PM (last used)]        ← callback: use_default_time:{post_id}
Row 2: [9:00 AM] [1:00 PM] [6:00 PM]   ← callback: schedule:{post_id}:{time}
Row 3: [9:00 PM]                        ← callback: schedule:{post_id}:{time}
```

---

## 🗂️ UPDATED BUILD ORDER

| Phase | Skill(s) | What gets built |
|---|---|---|
| Phase 1 | Skill 1 | Project setup, config, database.py with preferences table |
| Phase 2 | Skill 2 | Instagram / Twitter / YouTube scrapers |
| Phase 3 | Skill 3 + 7 | Telegram bot with smart default time |
| Phase 4 | Skill 4 | Playwright browser poster |
| Phase 5 | Skill 5 + 7 | 2-page web UI (Posts feed + Calendar) |
| Phase 6 | Skill 6 | AWS EC2 deployment |

---

## ⚡ UPDATED .env TEMPLATE

```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
APIFY_API_TOKEN=your_apify_token_here
FLASK_SECRET_KEY=random_string_here
EC2_PUBLIC_IP=your_ec2_ip_here

# Time slots shown to user (comma separated, 24hr format)
POST_TIMES=09:00,13:00,18:00,19:00,21:00
LOOKBACK_DAYS=7
```

---

## 📋 UPDATED DATABASE SCHEMA

```sql
-- Posts table
CREATE TABLE posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,          -- 'instagram' | 'twitter' | 'youtube'
  author TEXT,
  content TEXT,
  media_url TEXT,
  post_url TEXT,
  likes INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  views INTEGER DEFAULT 0,
  engagement_score REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',   -- 'pending' | 'approved' | 'rejected' | 'scheduled' | 'posted'
  scheduled_date TEXT,             -- ISO date: '2024-01-15'
  scheduled_time TEXT,             -- 24hr: '19:00'
  posted_at DATETIME,
  scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User preferences (default time, settings)
CREATE TABLE user_preferences (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Scrape log
CREATE TABLE scrape_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT,
  accounts_scraped INTEGER,
  posts_found INTEGER,
  ran_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  success INTEGER DEFAULT 1
);
```

---

*Skills Pack v2 — Social Media Automation Agent*
*Updated: 2-page UI, smart default time, Telegram confirmation with calendar link*
