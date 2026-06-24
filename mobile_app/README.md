# UzVehicles Mobile App

## Decision: Telegram Mini App (not native Android/iOS)

### Why NOT native app

| Concern | Reality for Uzbekistan |
|---------|----------------------|
| Android/iOS both needed | 2 codebases, 6+ months, $30,000+ |
| App store approval | 2–4 weeks, can be rejected |
| Users must install it | 60–80% drop-off at install step |
| Uzbekistan iOS penetration | ~25% — most users are Android |
| Maintenance | Every OS update may break the app |

### Why Telegram Mini App wins

| Advantage | Impact |
|-----------|--------|
| Zero installation | User taps a button inside Telegram — done |
| Uzbekistan Telegram penetration: 90% | Your audience is already there |
| Shared authentication | User identity from Telegram — no login needed |
| One codebase (HTML/JS/React) | Build once, works on all phones |
| Bot can launch it inline | Natural extension of @MVehicleBot |
| Can access camera, location | Same capability for this use case |
| Telegram handles updates | Users always get latest version |

**Build native app only if:** product grows to 100,000+ users and you need background GPS mileage tracking or OBD scanner integration.

---

## What the Mini App Does

**Personal Car Cost Tracker** — the data the bot can't collect itself.

The user logs their own expenses over time. The backend stores this per-user and provides analysis.

### Features

1. **Fuel Log** — each time they fill up:
   - Date, odometer reading, liters filled, total cost
   - Auto-calculates: L/100km, cost/km

2. **Expense Log** — maintenance, repairs, insurance:
   - Date, category, cost, description

3. **Summary Dashboard:**
   - Total spent this month / year
   - Real fuel consumption (their car, their driving)
   - Cost per km (actual, not estimated)
   - Comparison vs Telegram bot estimate

4. **Sell/Keep Decision:**
   - Pulls current market price from bot API
   - Shows: "You spent $X owning this car for Y months"
   - "Current market value: $Z"
   - "Net cost of ownership: $X − $Z = real loss"

---

## Architecture

```
Telegram Bot @MVehicleBot
        │
        │ sendWebAppButton()
        ▼
Telegram Mini App (React SPA)
        │
        │ HTTPS API calls
        ▼
Django backend (new /api/user/* endpoints)
        │
        ▼
PostgreSQL (new user_expenses table)
```

Authentication: Telegram `initData` — the Mini App receives the user's Telegram ID automatically. No passwords needed.

---

## File Structure

```
mobile_app/
├── README.md           ← this file
├── index.html          ← Mini App entry point
├── src/
│   ├── App.jsx         ← Main React component
│   ├── pages/
│   │   ├── FuelLog.jsx
│   │   ├── Expenses.jsx
│   │   └── Dashboard.jsx
│   ├── api.js          ← Django API calls
│   └── telegram.js     ← Telegram WebApp SDK wrapper
├── public/
│   └── manifest.json
└── package.json
```

---

## How to Launch the Mini App from the Bot

In `tg_bot/bot.py`, add a button that opens the Mini App:

```python
from telegram import WebAppInfo

keyboard = InlineKeyboardMarkup([[
    InlineKeyboardButton(
        "📱 Open Car Tracker",
        web_app=WebAppInfo(url="https://yourdomain.com/app/")
    )
]])
await update.message.reply_text("Track your car expenses:", reply_markup=keyboard)
```

The Mini App URL must be served over HTTPS. Use ngrok for development.

---

## Backend Endpoints Needed (Django)

```
POST /api/user/fuel-log/         Log a fuel fill-up
GET  /api/user/fuel-log/         Get fuel history
POST /api/user/expense/          Log a repair/maintenance expense
GET  /api/user/expense/summary/  Monthly/yearly summary
GET  /api/user/dashboard/        Full dashboard data
```

Authentication via Telegram `initData` header (validated with bot token HMAC).

---

## Development Setup

```bash
# Install dependencies
cd mobile_app
npm install

# Start dev server
npm run dev

# The app will be available at http://localhost:5173
# Use ngrok to expose it: ngrok http 5173
# Set the ngrok URL as the WebApp URL in the bot
```

---

## Timeline

| Phase | Work | Time |
|-------|------|------|
| 1 | Django user endpoints + auth | 2 days |
| 2 | Basic React app (fuel log + expenses) | 3 days |
| 3 | Dashboard + charts | 2 days |
| 4 | Bot integration button | 1 day |
| 5 | Deploy to production | 1 day |

**Total: ~2 weeks for MVP**
