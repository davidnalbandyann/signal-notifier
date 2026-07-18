# Trading Chart AI Monitor — User Flows

## Page Inventory & Entry Points

| # | Page | Route | Auth Guard | Entry Points |
|---|---|---|---|---|
| 1 | Login | `/login` | Guest only | Any unauthenticated URL redirects here |
| 2 | Dashboard | `/` | Required | Login success, sidebar logo click |
| 3 | Charts | `/charts` | Required | Sidebar nav |
| 4 | History | `/history` | Required | Sidebar nav, Dashboard "View all" link |
| 5 | Analysis Detail | `/analysis/:id` | Required | History row click, notification row click |
| 6 | Notifications | `/notifications` | Required | Sidebar nav |
| 7 | Settings | `/settings` | Required | Sidebar nav |
| 8 | C++ Engine | `/engine` | Required | Sidebar nav |
| 9 | Strategy | `/strategy` | Required | Sidebar nav |
| 10 | (Catch-all) | `/*` | — | Any unknown path → redirect to `/` |

---

## Global Shell

Every authenticated page (`/` and all routes except `/login`) renders inside a persistent shell:
- **Sidebar** — always visible on the left. Collapsible to icon-only (toggle button at bottom). Contains nav links to all 7 pages + two global actions ("Pause/resume scan loop", "Run scan now").
- **Top bar** — sticky. Shows breadcrumb (`MONITOR · Current page`), theme toggle (dark/light), user info pill with logout button.

---

## 1. Login Flow

1. User lands on any protected URL → redirected to `/login`.
2. User sees username field (pre-filled "admin") + password field (empty) + "Sign in" button.
3. On submit → POST `/api/auth/login` with `{username, password}`.
4. **Success** → token stored in localStorage → redirect to `/`.
5. **Failure** → inline error message "Invalid credentials. Try admin / admin123" shown below password field; user can retry.
6. If already authenticated and user navigates to `/login` → redirect to `/`.

---

## 2. Dashboard Flow

**Purpose**: System overview. First thing user sees after login.

**What the user sees:**
- System running/paused indicator (pill with animated dot)
- 4 stat cards: total charts, analyses today, signals sent, average score
- Countdown timer to next automatic scan
- "Run scan now" button (triggers immediate scan) + "Pause/Resume" toggle
- Two panels side by side:
  - **Recent analyses** (last 5) — clickable rows → navigates to `/analysis/:id`
  - **Recent signals** (last 5, filtered to score ≥ 7.0)

**User actions:**
- Click "Run scan now" → triggers POST `/api/scan/trigger` → toast confirmation
- Click "Pause scan" → pauses scheduler → state indicator updates
- Click "Resume scan" → resumes scheduler → countdown starts
- Click an analysis row → navigate to `/analysis/:id`
- Click "View all" (recent analyses card) → navigate to `/history`
- Click sidebar nav → navigate to any other page

**Data source**: GET `/api/status` on load.

---

## 3. Charts Flow

**Purpose**: Manage the list of TradingView chart URLs being monitored.

**What the user sees:**
- Header with "+ Add chart" button
- List of chart rows (if any) or empty state with call to action
- Each row shows: favicon, chart name, URL, last score, last scanned date, active/paused status, Edit/Delete buttons

**User actions:**
- **Add chart** → modal opens:
  1. Enter TradingView URL (required)
  2. Enter optional friendly name
  3. Click "Add chart" → POST `/api/charts` → list refreshes
  4. Click "Cancel" or backdrop → modal closes
- **Edit chart** → modal opens:
  1. Modify name, URL, or enable/disable toggle
  2. Click "Save changes" → PUT `/api/charts/:id` → list refreshes
- **Delete chart** → native `confirm()` dialog → DELETE `/api/charts/:id` → list refreshes

**Data source**: GET `/api/charts` on load.

---

## 4. History Flow

**Purpose**: Browse all past analyses with filtering, sorting, and pagination. Perform actions on individual records.

**What the user sees:**
- Header with total row count and disabled "Export CSV" button
- Filter bar: chart dropdown, direction dropdown, min score slider (0–10), date range (from/to), "Signals only" toggle
- Data table (paginated) with columns: Timestamp, Chart, Direction, Score (bar + number), Sent status, Notification ID, Actions (Resend/Reanalyze/Delete)
- Pagination footer with page controls and page size selector

**User actions:**
- **Apply any filter** → page resets to 1, table re-fetches with filter params
- **Sort a column** → click column header → toggles asc/desc → re-fetches
- **Click a row** → navigate to `/analysis/:id`
- **Resend** → POST `/api/analyses/:id/resend` → toast "Notification resent"
- **Reanalyze** → POST `/api/analyses/:id/reanalyze` → toast "Re-analysis started"
- **Delete** → native `confirm()` → DELETE `/api/analyses/:id` → list refreshes
- **Change page** → click page number / prev/next → re-fetches
- **Change page size** → dropdown (12/25/50/100) → page resets to 1, re-fetches

**Data source**: GET `/api/analyses` with query params on load and on every filter/sort/page change.

---

## 5. Analysis Detail Flow

**Purpose**: Full view of a single analysis — AI reasoning, entry/exit levels, and the chart screenshot.

**Entry point**: Click a row in History or Notifications.

**What the user sees:**
- Header: chart name, timestamp, analysis ID, sent/skipped status pill
- Left panel: direction chip, score bar, timestamps, entry/stop-loss/take-profit (if available), notification ID
- Right panel: chart screenshot image (if available) or placeholder
- Full-width section: AI reasoning text (freeform, from vision model)
- Action buttons: Back, Resend notification, Reanalyze, Delete

**User actions:**
- **Back** → browser history back
- **Resend** → POST `/api/analyses/:id/resend` → toast
- **Reanalyze** → POST `/api/analyses/:id/reanalyze` → toast
- **Delete** → native `confirm()` → DELETE → redirect to previous page

**Data sources**: GET `/api/analyses/:id` (analysis data), GET `/api/analyses/:id/screenshot` (PNG blob).

---

## 6. Notifications Flow

**Purpose**: Audit trail of all Telegram notifications sent.

**What the user sees:**
- Header with total count
- List of notification rows (paginated)
- Each row: chart name + direction, score + caption, timestamp, ok/error status pill, Delete button

**User actions:**
- **Click a row** → navigate to `/analysis/:id`
- **Delete** → native `confirm()` → DELETE `/api/notifications/:id` → list refreshes
- **Page through** → prev/next buttons, page info shown

**Data source**: GET `/api/notifications` with page/page_size.

---

## 7. Settings Flow

**Purpose**: Configure all system parameters. Single long-scrolling page with sticky section nav.

**What the user sees:**
- Sticky left nav with 5 section links (Scan timing, Threshold, Browser, AI provider, Telegram)
- Content area with 5 collapsible section cards

**User actions per section:**

**Scan Timing:**
- Adjust `CHECK_INTERVAL_SECONDS` (number, 1–3600)
- Adjust `AI_CALL_DELAY` (number, 0–30, step 0.5)
- Toggle scan loop on/off (with Run scan now shortcut)
- Click "Save" → PUT `/api/settings` → toast

**Threshold:**
- Adjust `NOTIFICATION_THRESHOLD` via slider (0–10, step 0.1)
- Toggle Long/Short/Neutral direction filters
- Toggle C++ bypass AI gate
- Click "Save"

**Browser:**
- Toggle headless mode
- Set viewport width × height
- Set capture wait time (seconds)
- Set retry count + retry delay
- Click "Save"

**AI Provider:**
- Set model name (text)
- Set API key (password masked, show/hide toggle)
- Click "Save"

**Telegram:**
- Set bot token (password masked, show/hide toggle)
- Set chat ID
- Toggle send screenshot
- Set quiet hours start/end (24h format)
- Click "Save"

**Data source**: GET `/api/settings` on load (secret fields masked), PUT `/api/settings` on save.

---

## 8. C++ Engine Flow

**Purpose**: Monitor and control the external C++ signal process.

**What the user sees:**
- Status bar: running/stopped indicator, PID, uptime
- Last C++ signal banner (chart name, direction, entry, score)
- Engine logs scrollable viewport (polls every 2s while running)
- Signal history table with columns: Symbol, Dir, Entry, BW, VolR, RSI, Score, Time, Status

**User actions:**
- **Start Engine** → POST `/api/cpp-engine/start` → status updates, log polling begins
- **Stop Engine** → POST `/api/cpp-engine/stop` → status updates, log polling stops
- View logs (auto-refresh while running)
- View signal history (fetched once on page load)

**Data sources**: GET `/api/cpp-engine/status`, POST `/api/cpp-engine/start`, POST `/api/cpp-engine/stop`, GET `/api/cpp-engine/logs` (polled), GET `/api/cpp-engine/signals`.

---

## 9. Strategy Flow

**Purpose**: Edit the AI system prompt used for every chart analysis.

**What the user sees:**
- Info banner: "This is the system prompt sent to the AI model for every chart analysis. Edit with care."
- Large textarea pre-filled with current strategy content
- "Save strategy" button

**User actions:**
- Edit text in textarea (plain markdown, spellcheck off)
- Click "Save strategy" → PUT `/api/strategy` → toast "Strategy updated"

**Data source**: GET `/api/strategy` on load.

---

## Sidebar Global Actions

Available from any authenticated page (not engine-specific):

| Action | What happens |
|---|---|
| Click sidebar nav item | Router navigate to target page |
| **Pause loop** | POST `/api/scan/pause` → indicator changes |
| **Resume loop** | POST `/api/scan/resume` → indicator changes |
| **Run scan now** | POST `/api/scan/trigger` → immediate scan |
| Toggle sidebar collapse | Local state toggle, persisted |
| Toggle theme (topbar) | Local state toggle, persisted on `<html data-theme>` |
| Logout (topbar) | Clear token from localStorage → redirect to `/login` |

---

## Auth Redirection Summary

| Condition | Result |
|---|---|
| Not authenticated → any protected route | Redirect to `/login` with `?redirect=` (implicit) |
| Authenticated → `/login` | Redirect to `/` |
| Unknown path | Redirect to `/` (catch-all) |
| Login success | Redirect to `/` |
| Token expires/missing | Guard catches → redirect to `/login` on next navigation |

---

## Data Flow Diagram (textual)

```
Login → stores JWT in localStorage → every API client reads token from store

Dashboard (/) → GET /api/status → stat cards + recent lists
Charts (/charts) → GET/POST/PUT/DELETE /api/charts → CRUD
History (/history) → GET /api/analyses?filters → filtered table
Analysis (/analysis/:id) → GET /api/analyses/:id + /screenshot → full detail
Notifications (/notifications) → GET /api/notifications → audit list
Settings (/settings) → GET/PUT /api/settings → config
Engine (/engine) → GET/POST /api/cpp-engine/* → process control
Strategy (/strategy) → GET/PUT /api/strategy → prompt editor

All writes → Toast confirmation at bottom-right
All data pages → Spinner while loading, empty state when no data
```
