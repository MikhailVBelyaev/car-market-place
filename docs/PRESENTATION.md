# UzVehicles Market — Investor & Partner Pitch

## The Problem

**Every family in Uzbekistan faces the same question: what is my car actually worth?**

- 3.5+ million registered vehicles in Uzbekistan
- Cars trade hands every 1–3 years — faster than most asset classes
- Sellers systematically overprice; buyers have no data to negotiate
- No structured price database exists in the market
- Hidden cost: depreciation is invisible — owners only discover losses at sale time

---

## The Solution

**UzVehicles Market: the first data-driven car intelligence platform for Uzbekistan**

A three-layer platform that turns 14+ months of real market data into actionable intelligence:

```
Layer 1 — Bot (@MVehicleBot)          Real-time price prediction + car analysis
Layer 2 — Analytics Channel           Weekly market intelligence for 10,000+ followers
Layer 3 — Personal Finance Tools      Own car vs taxi calculator, value forecasts
```

---

## Why Now

**Three converging trends make this the right moment:**

1. **Yandex.Taxi** has reached critical mass in Uzbekistan — owning a car is now a genuine financial choice, not a necessity. People need to calculate whether ownership makes economic sense.

2. **Car prices are volatile.** BYD lost 31% of value in 12 months. Hyundai lost 25%. Chevrolet lost 9%. Owners are bleeding value without knowing it.

3. **Telegram penetration in Uzbekistan exceeds 90%.** Distribution is free. The audience is already there.

---

## Data Advantage

We have what no competitor has: **14+ months of structured OLX listing data.**

| What we collect | What it enables |
|----------------|-----------------|
| Brand, model, year, mileage, gear, color | Precise like-for-like price comparisons |
| Daily price snapshots | Month-by-month depreciation tracking |
| 14-month history | Real annual depreciation rates by brand |
| 25+ attributes per listing | ML price prediction with 85%+ accuracy |

**This dataset does not exist anywhere else in Uzbekistan.**

---

## Product Suite

### 🤖 @MVehicleBot — Telegram Price Bot
- 30-second car price prediction
- Inputs: brand, model, year, km, gear, color
- Shows: current market price (real listings), historical trend chart, price range
- **New:** `/compare` — Own car vs Taxi financial calculator
- **New:** `/forecast` — 3-year value depreciation projection
- **New:** `/fotos` — AI car condition analysis from photos

### 📊 @UzVehiclesMarket — Analytics Channel
- **Monday:** Top brands by listing volume + week-over-week change
- **Wednesday:** Biggest price movers (which models rose/fell)
- **Friday:** Full weekly digest — brand rankings, YoY depreciation, market snapshot
- Bilingual: Uzbek + Russian
- Every post links back to the bot → flywheel growth

### 💡 Own Car vs Taxi Calculator
Answers Uzbekistan's most common financial question:
> "Is it worth owning a car, or should I use Yandex.Taxi?"

Inputs: daily km driven, car model, taxi price per km
Output: monthly cost comparison, 3-year cumulative chart, break-even analysis

### 📉 Value Forecast Tool
Shows how much a specific car will lose in value over 1–3 years, based on real market data — not guesses.

---

## Market Opportunity

| Segment | Size |
|---------|------|
| Uzbekistan car owners | 3.5M+ |
| Annual new car registrations | ~250,000 |
| OLX.uz monthly active users | 2M+ |
| Telegram users in Uzbekistan | 15M+ |
| Yandex.Taxi rides/day (Tashkent) | 500,000+ |

Even 1% of Telegram users engaging with the channel = **150,000 followers**.

---

## Business Model

**Phase 1 — Audience (now)**
- Free bot and channel
- Build follower base and bot user trust

**Phase 2 — Monetization (6–12 months)**
- Dealer listings: car dealers pay to feature inventory
- Sponsored channel posts: auto parts, insurance, taxi services
- Premium API: banks and insurance companies pay for real-time price data
- Lead generation: "find this car for me" → dealer referral fee

**Phase 3 — Platform (12–24 months)**
- Mobile app (Telegram Mini App) for personal car cost tracking
- Fintech integration: car loan calculators using real market prices
- Fleet management API for corporate clients

---

## Technology Stack

| Component | Technology | Status |
|-----------|-----------|--------|
| Data collection | Python scraper → OLX | Live, daily |
| Database | PostgreSQL 15, 14+ months | Live |
| API | Django REST Framework | Live |
| Price prediction | RandomForest ML model | Live |
| Bot | python-telegram-bot v21 | Live |
| Analytics channel | Automated posting (Airflow) | Live |
| Photo analysis | Claude claude-haiku-4-5 (Anthropic) | Live |
| Infrastructure | Docker Compose, local server | Live |
| Cloud | Azure AKS / GCP ready | Ready |

---

## Why This Is Different from Competitors

| | UzVehicles | OLX.uz | Auto.uz | Colesa.uz |
|---|---|---|---|---|
| Real-time price data | ✅ | ❌ | ❌ | ❌ |
| Historical trend | ✅ | ❌ | ❌ | ❌ |
| Own car vs Taxi calculator | ✅ | ❌ | ❌ | ❌ |
| AI photo analysis | ✅ | ❌ | ❌ | ❌ |
| Weekly analytics channel | ✅ | ❌ | ❌ | ❌ |
| Uzbek language | ✅ | Partial | Partial | Partial |
| Telegram native | ✅ | ❌ | ❌ | ❌ |

---

## Traction

- 14 months of data collected
- Bot live at @MVehicleBot
- Channel launched: @UzVehiclesMarket
- Automated weekly posting running
- Working ML model with gear/color/brand inputs
- Full hedonic pricing model for like-for-like comparisons

---

## The Team Ask

We are looking for:
- **Partnership:** Dealerships, insurance companies, Yandex.Taxi integration
- **Distribution:** Media partners to amplify the analytics channel
- **Investment:** To scale infrastructure and build mobile app

---

## One Slide Summary

> Uzbekistan has 3.5 million car owners, no price transparency, and 90% Telegram penetration.
> We built the data infrastructure to serve all three.
> The bot is live. The data is real. The market is ready.

**@MVehicleBot · @UzVehiclesMarket**
