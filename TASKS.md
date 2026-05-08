# Social Agent Implementation Tasks

This file converts `rodemapv2.md` into actionable engineering tickets.

## Milestone 1 - Core Stability (In Progress)

- [x] Stabilize `/pending` flow to be filter-first, not auto-spam list
- [x] Add source filters: All, Instagram, Twitter, YouTube, Other
- [x] Add sort options: newest, top score, most likes
- [x] Add keyword query support in `/pending <query>`
- [x] Make "next pending" respect active filter/sort/query
- [x] Add hard stop command `/stop`
- [ ] Add missing Telegram queue commands: `/schedule`, `/preview`, `/list`, `/cancel`
- [ ] Add one-instance startup guard to avoid Telegram polling conflicts
- [ ] Add explicit restart script for backend + bot (single command)

## Milestone 2 - Smart Filtering

- [ ] Add account-level filters after platform selection
- [ ] Add minimum engagement filter controls
- [ ] Add category filter controls (Educational/Promotional/etc.)
- [ ] Persist per-user filter preferences across restarts
- [ ] Add "saved filter presets" (e.g., Growth, News, Product)

## Milestone 3 - Scheduling Intelligence

- [ ] Recommend best slots by platform and history
- [ ] Suggest schedule automatically but require approval
- [ ] Add conflict detection (same platform close time overlap)
- [ ] Add timezone-aware scheduling profile
- [ ] Add schedule confidence score

## Milestone 4 - Browser Execution

- [ ] Define JSON queue contract consumed by browser layer
- [ ] Build browser overlay panel for queue operations
- [ ] Implement platform page detection with selector strategy
- [ ] Add safe publish pipeline with preview verification
- [ ] Add failure reason sync back to Telegram and DB

## Milestone 5 - Reporting and Optimization

- [ ] Weekly report: posted, failed, pending, top topics
- [ ] Track performance by topic/category/platform
- [ ] Add feedback loop to improve relevance scoring
- [ ] Export audit log for all moderation and publish actions

## Next Up (Active)

1. Implement `/schedule`, `/preview`, `/list`, `/cancel` in Telegram bot.
2. Add one-instance startup guard and startup health checks.
3. Add account-level filter step after selecting platform.
