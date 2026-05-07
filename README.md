# 🧠 Social Media Automation Agent

A fully automated, **100% free** social media scraping → curation → scheduling → posting pipeline.

Monitor Instagram, Twitter/X, and YouTube creators → get the best posts sent to Telegram for approval → auto-post to your own accounts via browser automation.

---

## 📐 Architecture

```
SCHEDULER (cron)
    │
    ▼
SCRAPER MODULE ──▶ FILTER & SCORE ──▶ TELEGRAM BOT
(IG / X / YT)       (0-100)           (approve/reject)
                                           │
                                           ▼
                                      SQLITE DB
                                      (schedule)
                                        │    │
                                        ▼    ▼
                                  CALENDAR  AUTO-POSTER
                                  WEB UI    (Playwright)
```

---

## 🚀 Quick Start (Local)

### 1. Clone & install

```bash
git clone <your-repo-url> social-self
cd social-self
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Create `.env`

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
APIFY_API_TOKEN=your_apify_token_here
```

### 3. Run everything

```bash
python main.py
```

This starts:
- **Flask Web UI** on `http://localhost:5000`
- **Telegram Bot** in polling mode
- **Scheduler** — scrapes daily at 08:00, checks posting queue every hour

---

## 🤖 Creating a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name and username
4. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`
5. Send a message to your bot, then visit:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
6. Find your `chat_id` from the response and put it in `.env` as `TELEGRAM_CHAT_ID`

---

## 📸 Adding Accounts to Monitor

Edit `config.py` and replace the placeholder usernames:

```python
ACCOUNTS = {
    "instagram": ["therock", "selenagomez", ...],
    "twitter":   ["elonmusk", "naval", ...],
    "youtube":   ["mkbhd", "veritasium", ...],
}
```

Or use the Web UI dashboard to manage source/posting accounts dynamically.

---

## 📅 Web UI

Open `http://localhost:5000` to access:
- **Calendar View** — see all scheduled posts in a weekly grid
- **Post Cards** — platform-color-coded cards with content preview
- **Post Now** — one-click trigger for immediate posting
- **Drag & Drop** — reschedule posts visually

---

## 📡 Telegram Commands

| Command      | Action                          |
|-------------|---------------------------------|
| `/start`    | Show welcome message            |
| `/pending`  | View all pending posts          |
| `/scheduled`| View approved scheduled posts   |
| `/status`   | System health summary           |
| `/help`     | List all commands               |

Each pending post has **✅ Approve** and **❌ Reject** buttons. On approval, pick a time slot.

---

## ☁️ AWS Deployment (Free Tier)

### Requirements
- AWS account with EC2 access
- t2.micro instance (free tier eligible)
- Ubuntu 22.04 AMI

### Steps

1. Launch EC2 instance and SSH in
2. Upload your project to `/home/ubuntu/social-self`
3. Run the setup script:

```bash
chmod +x deploy/setup_aws.sh
sudo bash deploy/setup_aws.sh
```

4. Add port **5000** to your EC2 Security Group (inbound TCP)
5. Access Web UI at `http://<your-ec2-ip>:5000`

### Managing the Service

```bash
sudo systemctl status social-agent    # Check status
sudo systemctl restart social-agent   # Restart
sudo journalctl -u social-agent -f   # Tail logs
```

---

## 📂 Project Structure

```
social-self/
├── main.py                  # Entry point — runs all subsystems
├── config.py                # Account lists & settings
├── scheduler.py             # Cron-like job runner
├── database.py              # SQLite ORM layer
│
├── scrapers/
│   ├── instagram.py         # Apify-based Instagram scraper
│   ├── twitter.py           # Nitter RSS Twitter scraper
│   └── youtube.py           # YouTube RSS scraper
│
├── filters/
│   └── scorer.py            # Engagement scoring (0-100)
│
├── telegram_bot/
│   ├── bot.py               # Bot bootstrap
│   └── handlers.py          # Approve/reject/schedule handlers
│
├── poster/
│   ├── browser_poster.py    # Shared Playwright session manager
│   ├── instagram_post.py    # Instagram posting automation
│   ├── twitter_post.py      # Twitter posting automation
│   └── youtube_post.py      # YouTube posting automation
│
├── web_ui/
│   ├── app.py               # Flask API + calendar routes
│   ├── templates/
│   │   └── calendar.html    # Dashboard UI
│   └── static/
│       └── style.css
│
├── deploy/
│   └── setup_aws.sh         # EC2 setup script
│
├── requirements.txt
├── .env                     # Secrets (never commit)
└── README.md
```

---

## 🔧 Troubleshooting

### Bot not responding
- Verify `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Make sure no other bot instance is running (only one poller allowed)

### Scrapers returning nothing
- Instagram: Check your Apify free tier limits
- Twitter: Nitter hosts go down frequently; check `NITTER_HOSTS` in `scrapers/twitter.py`
- YouTube: RSS feeds use `?user=` param; some channels need `?channel_id=` instead

### Playwright login issues
- First run opens a visible browser for manual login
- After login, session cookies are saved to `sessions/`
- Delete `sessions/*.json` to force re-login

### Web UI not loading
- Check Flask is running on port 5000
- On AWS: ensure Security Group allows inbound TCP 5000
- Check logs: `journalctl -u social-agent -f`

---

## 📜 License

MIT — Use freely. Built for personal automation.
