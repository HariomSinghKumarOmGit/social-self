# Social Agent — Swipe Review UI

Tinder-style post review for Social Agent.

## Local dev

```bash
npm install
npm run dev
```

Runs on http://localhost:5173 with API proxied to http://127.0.0.1:56823.

## Production build (served by Flask)

```bash
npm run build
```

Then open http://127.0.0.1:56823/review

## Deploy to Vercel

1. Set root directory to `review-ui`
2. Add env var `VITE_API_BASE_URL` = your public Flask API URL
3. Deploy
