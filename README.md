# Fan Pulse: X Crowd Sentiment vs. Kalshi Market Odds

Independent showcase project by **Virginia Shipp** ([LinkedIn](https://www.linkedin.com/in/virginia-s-66202b189) | [Kalshi Activations Pitch](https://thevc3477.github.io/kalshi-activations/)). Not affiliated with, endorsed by, or sponsored by Kalshi.

## What It Does

Compares real-time **Kalshi prediction-market probabilities** against **7-day X fan conversation volume and deduplicated directional sentiment** across 10 major Thanksgiving Week 2026 sports and culture events (NFL Thanksgiving slate, NBA Cup, CFB Rivalry Week, NFL MVP, Heisman Trophy, and 99th Oscars Best Picture).

## Methodology

1. **Kalshi Market Odds:** Pulled live from Kalshi's public v2 events API (`/trade-api/v2/events/{ticker}?with_nested_markets=true`). Head-to-head shares normalize live bid/ask midpoints across the two compared sides while displaying raw contract prices in cents for multi-outcome futures.
2. **7-Day X Buzz Share:** Exact 7-day English non-retweet post counts per contender (`-is:retweet lang:en`).
3. **Sampled X Sentiment:** Non-spam sampled posts scored by a deterministic Python rule-based lexicon (`scripts/refresh_kalshi.py`), excluding `@KalshiSports` market-news posts and deduplicated to max 1 directional vote per unique X handle.
4. **Composite Crowd Score & Divergence:** `Crowd % = 0.50 * Buzz Share % + 0.50 * Sample Sentiment %`; `Divergence = Crowd % - Kalshi H2H %`.

## Refresh Live Kalshi Odds

```bash
python3 scripts/refresh_kalshi.py
```

This fetches live Kalshi prices, updates `data/snapshot.json` with a fresh `America/Chicago` timestamp, and rebuilds the self-contained static `index.html`. A GitHub Actions workflow (`.github/workflows/refresh-odds.yml`) also runs this script every 6 hours while keeping the X dataset pinned to its verified snapshot.
