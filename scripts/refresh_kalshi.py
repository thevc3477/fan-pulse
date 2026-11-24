#!/usr/bin/env python3
"""
Fetch live Kalshi prediction-market odds, score the verified X snapshot,
compute crowd-vs-market divergences, and build data/snapshot.json + index.html.
"""
import datetime
import json
import re
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RAW_COUNTS_PATH = ROOT / "raw" / "x_counts.json"
RAW_POSTS_PATH = ROOT / "raw" / "x_posts.json"
SNAPSHOT_PATH = ROOT / "data" / "snapshot.json"
TEMPLATE_PATH = ROOT / "src" / "template.html"
OUT_HTML_PATHS = [ROOT / "index.html", ROOT / "web" / "index.html"]

CT_TZ = ZoneInfo("America/Chicago")


def fetch_kalshi_event(event_ticker: str) -> dict:
    url = f"https://api.elections.kalshi.com/trade-api/v2/events/{event_ticker}?with_nested_markets=true"
    req = urllib.request.Request(url, headers={"User-Agent": "FanPulseTracker/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))["event"]


def mid_price(mkt: dict) -> float:
    bid = mkt.get("yes_bid_dollars")
    ask = mkt.get("yes_ask_dollars")
    last = mkt.get("last_price_dollars")
    if bid is not None and ask is not None:
        return (float(bid) + float(ask)) / 2.0
    if last is not None:
        return float(last)
    return 0.0


def score_post_direction(event_id: str, text: str) -> str:
    """
    Transparent, deterministic rule-based directional classifier.
    Returns 'A', 'B', or 'N' (neutral / two-sided / meta-commentary).
    """
    t = " " + text.lower().replace("&amp;", "&") + " "

    if event_id == "KXNFLGAME-26NOV25GBLAR":
        if re.search(r"(packers will beat|packers \+\d|packers ml|if packers beat rams|micah parsons.*returning)", t):
            return "A"
        if re.search(r"(rams will (beat|crash|take down)|picking the la rams|rooting for la rams|mop the floor with the packers|my pick to win: the rams|prediction: los angeles rams win|rams just cause|beat the packers!|not the better team when they go against the la rams)", t):
            return "B"
        return "N"

    if event_id == "KXNFLGAME-26NOV26CHIDET":
        if re.search(r"(chicago bears \(thursday\) mlp|bears -\d|most of the ais flipped to chicago|lightskin qbs win:.*bears|chicago has won five straight)", t) and "lions will beat" not in t:
            return "A"
        if re.search(r"(lions will beat the chicago bears|lions \+\d|ai average still says detroit lions|five in a row for the detroit lions|our detroit lions host.*#onepride|rude awakening on thanksgiving)", t):
            return "B"
        return "N"

    if event_id == "KXNFLGAME-26NOV26PHIDAL":
        if re.search(r"(cowboys should win out|cowboys -\d|lightskin qbs win:.*cowboys|streak worth changing against philadelphia)", t) and "won't" not in t and "isn't gonna happen" not in t:
            return "B"
        if re.search(r"(eagles aren't beating|eagles are not in win now)", t):
            return "B"
        if re.search(r"(cowboys won't make playoffs|isn't gonna happen|still managed to lose)", t):
            return "A"
        return "N"

    if event_id == "KXNFLGAME-26NOV26KCBUF":
        if re.search(r"(fade patrick mahomes|chiefs \+\d|lightskin qbs win:.*chiefs|bills will never win a super bowl|last time the bills beat the chiefs in the playoffs|yall should beat them)", t) and "bills moneyline" not in t:
            return "A"
        if re.search(r"(buffalo bills moneyline|bills mafia all the way|go bills|please beat the chiefs|money behind the chiefs.*first time following football|must-win for the bills)", t):
            return "B"
        return "N"

    if event_id == "KXNBAGAME-26NOV25MINOKC":
        if re.search(r"(no world where okc should be ahead of minnesota|timberwolves.*first play|wolves win|wolves actually have a higher ortg|more consistent recently|wolvesgiving)", t):
            return "A"
        if re.search(r"(thunder win this one|thunder run the west|37% more talented roster|spurs, rockets then thunder)", t):
            return "B"
        return "N"

    if event_id == "KXNCAAFGAME-26NOV27TEXTXAM":
        if re.search(r"(texas longhorns -\d|texas -\d|ags lose this one|no chance to win|didn't texas beat|operation hook em|longhorns.*five-game winning streak)", t):
            return "A"
        if re.search(r"(aggies will beat|battered aggie|bench marcel reed)", t):
            if "aggies will beat" in t:
                return "B"
            return "A"
        return "N"

    if event_id == "KXNCAAFGAME-26NOV28MICHOSU":
        if re.search(r"(michigan doesn't beat ohio state|guaranteeing a win over ohio state|can legit beat ohio state|pick ttun to win|whooped your ass|michigan wolverines beats ohio state)", t):
            return "A"
        if re.search(r"(reassuring to an ohio state win|go bucks|go buckeyes|got caught cheating|michigan sucks)", t):
            return "B"
        return "N"

    if event_id == "KXNFLMVP-27":
        if re.search(r"(brock purdy is the mvp|brock purdy is who everyone thinks|pick.*brock purdy as his nfl mvp|positive epa rate|purdy is really carrying)", t):
            return "A"
        if re.search(r"(isn't in joe burrow mvp talks|joe burrow is the best|joe burrow is going to end up winning mvp|joe burrow is mvp|1 - joe burrow)", t):
            return "B"
        return "N"

    if event_id == "KXHEISMAN-27":
        if re.search(r"(1\.\) jeremiah smith|1\. jeremiah smith|jeremiah smith.*56%|jeremiah smith \(63%\)|highest ticket% 1\. jeremiah smith|over 80% on kalshi)", t):
            return "A"
        if re.search(r"(dampier should be the heisman|1 devon dampier|can't give the heisman to smith|dampier takes our top spot|1\. darian mensah)", t):
            return "B"
        return "N"

    if event_id == "KXOSCARPIC-27":
        if re.search(r"(the odyssey \(winner\)|1\. the odyssey|1- the odyssey|early pick\? the odyssey|clear best picture frontrunner)", t):
            return "A"
        if re.search(r"(1\. la bola negra|la bola negra - winner)", t):
            return "B"
        return "N"

    return "N"


EVENTS_META = [
    {
        "id": "KXNFLGAME-26NOV25GBLAR",
        "category": "NFL",
        "tag": "NFL · THANKSGIVING EVE",
        "title": "Packers at Rams",
        "subtitle": "Wed Nov 25, 7:15 PM CT · Netflix",
        "side_a": {"label": "Green Bay Packers", "short": "GB", "kalshi_sub": "Green Bay", "x_series": "packers"},
        "side_b": {"label": "Los Angeles Rams", "short": "LAR", "kalshi_sub": "Los Angeles R", "x_series": "rams"},
        "headline": "Packers draw 54.8% of X buzz after Micah Parsons returns and Rams lose Puka Nacua, while Kalshi holds LA as 55.5% favorite.",
        "story_bullets": [
            "Green Bay activated Micah Parsons for Wednesday night, while LA ruled out Puka Nacua (knee) and TE Terrance Ferguson (ankle).",
            "Matt LaFleur is 5-0 vs. Sean McVay, yet Kalshi's Rams share stays above 55% even as Packers contracts make up nearly 80% of market volume.",
            "Netflix broadcasts the game with a U2 halftime show, creating a prime live-watch cultural moment."
        ],
        "activation_angle": "Run a 'Health vs. History' live prediction prop during Netflix's U2 halftime show. Packers fans dominate X chatter and contract flow, so a live second-half market booth or watch-party challenge in Chicago/Milwaukee taps huge Midwest demand."
    },
    {
        "id": "KXNFLGAME-26NOV26CHIDET",
        "category": "NFL",
        "tag": "NFL · THANKSGIVING EARLY",
        "title": "Bears at Lions",
        "subtitle": "Thu Nov 26, 12:00 PM CT · CBS · Wu-Tang Halftime",
        "side_a": {"label": "Chicago Bears", "short": "CHI", "kalshi_sub": "Chicago", "x_series": "bears"},
        "side_b": {"label": "Detroit Lions", "short": "DET", "kalshi_sub": "Detroit", "x_series": "lions"},
        "headline": "Both NFC North leaders enter 8-2. Bears own 58.7% of 7-day X volume (17,825 posts), while Lions fans lean slightly louder in pick threads.",
        "story_bullets": [
            "Highest-buzz matchup on the Thanksgiving slate: 30,388 combined X posts across both teams in 7 days.",
            "Kalshi prices Chicago at 55.5% (Bears -2.5 on the road), tracking closely with Chicago's 58.7% X buzz share.",
            "Detroit's #OnePride fanbase floods reply threads on the 92nd anniversary of the 1934 Bears-Lions Thanksgiving game, with Wu-Tang Clan headlining halftime."
        ],
        "activation_angle": "Chicago hometown opportunity: host a Thanksgiving midday Bears vs. Lions watch party with Vinyl Collectiv-style culture programming (tying into the Wu-Tang halftime show) and live NFC North odds boards."
    },
    {
        "id": "KXNFLGAME-26NOV26PHIDAL",
        "category": "NFL",
        "tag": "NFL · THANKSGIVING LATE",
        "title": "Eagles at Cowboys",
        "subtitle": "Thu Nov 26, 3:30 PM CT · FOX · Miranda Lambert Halftime",
        "side_a": {"label": "Philadelphia Eagles", "short": "PHI", "kalshi_sub": "Philadelphia", "x_series": "eagles"},
        "side_b": {"label": "Dallas Cowboys", "short": "DAL", "kalshi_sub": "Dallas", "x_series": "cowboys"},
        "headline": "Kalshi prices Dallas at 79.5% against a slumping Philadelphia squad, but X buzz is split 45/55 as fans remain skeptical of 5-6 Dallas.",
        "story_bullets": [
            "Big gap between market certainty (Dallas ~80%) and X skepticism: fans openly doubt Dallas can string wins together despite Dak Prescott's record chase.",
            "Eagles fanbase remains active on X (7,282 weekly posts) even with Philly struggling, creating asymmetric contrarian conversation.",
            "Miranda Lambert headlines the 30th Salvation Army Red Kettle Kickoff halftime show alongside Lauren Daigle on the anthem."
        ],
        "activation_angle": "Classic 'Skeptical Crowd vs. Heavy Favorite' setup. Brands activating on the afternoon FOX window can lean into live in-game momentum props (will Dallas hold the lead?) rather than pre-game winner hype."
    },
    {
        "id": "KXNFLGAME-26NOV26KCBUF",
        "category": "NFL",
        "tag": "NFL · THANKSGIVING NIGHT",
        "title": "Chiefs at Bills",
        "subtitle": "Thu Nov 26, 7:20 PM CT · NBC · Goo Goo Dolls Halftime",
        "side_a": {"label": "Kansas City Chiefs", "short": "KC", "kalshi_sub": "Kansas City", "x_series": "chiefs"},
        "side_b": {"label": "Buffalo Bills", "short": "BUF", "kalshi_sub": "Buffalo", "x_series": "bills"},
        "headline": "X buzz is deadlocked at 49.9% KC / 50.1% BUF across 25,576 posts, while Kalshi prices the 9-1 Bills as a 58.5% favorite for the AFC #1 seed.",
        "story_bullets": [
            "Nearly identical 7-day X post volume (12,761 KC vs. 12,815 BUF) reflects classic 'Bills regular season vs. never fade Mahomes' tension.",
            "Kalshi gives 9-1 Buffalo a ~58.5% edge at Highmark Stadium with the AFC bye on the line.",
            "Buffalo hometown band Goo Goo Dolls performs at halftime on NBC primetime."
        ],
        "activation_angle": "Primetime Thanksgiving night delivers maximum family-room second-screen engagement. A simple 'Mahomes Magic vs. Bills #1 Seed' single-question social poll synced to NBC halftime drives huge organic sharing."
    },
    {
        "id": "KXNBAGAME-26NOV25MINOKC",
        "category": "NBA",
        "tag": "NBA CUP · WEST GROUP B",
        "title": "Timberwolves at Thunder",
        "subtitle": "Wed Nov 25, 6:30 PM CT · Paycom Center",
        "side_a": {"label": "Minnesota Timberwolves", "short": "MIN", "kalshi_sub": "Minnesota", "x_series": "timberwolves"},
        "side_b": {"label": "Oklahoma City Thunder", "short": "OKC", "kalshi_sub": "Oklahoma City", "x_series": "thunder"},
        "headline": "Kalshi prices OKC as a razor-thin 50.5% coin flip, while X pick sentiment swings heavily toward 13-5 Minnesota despite OKC holding higher total mention volume.",
        "story_bullets": [
            "Minnesota enters 13-5 (even missing Anthony Edwards), while 10-8 OKC just dropped a 125-120 loss to Indiana despite Shai Gilgeous-Alexander's 38 points.",
            "Fans in NBA Cup reply threads push back hard on OKC being favored, yet national SGA/OKC chatter drives 57.6% of total 7-day X volume.",
            "Grassroots proof point: Minneapolis fans organized 'Wolvesgiving', a Nov 25 watch party and vendor market at Fowling Warehouse around this exact game."
        ],
        "activation_angle": "Local fan markets like 'Wolvesgiving' show how NBA Cup nights already spawn IRL watch parties. Kalshi can co-sponsor fan-organized cup watch parties with custom group-stage probability boards."
    },
    {
        "id": "KXNCAAFGAME-26NOV27TEXTXAM",
        "category": "CFB",
        "tag": "CFB · BLACK FRIDAY RIVALRY",
        "title": "Texas at Texas A&M",
        "subtitle": "Fri Nov 27, 6:30 PM CT · Kyle Field",
        "side_a": {"label": "Texas Longhorns", "short": "TEX", "kalshi_sub": "Texas", "x_series": "texas"},
        "side_b": {"label": "Texas A&M Aggies", "short": "TXAM", "kalshi_sub": "Texas A&M", "x_series": "texas_am"},
        "headline": "Tightest market-crowd alignment on the board: Kalshi puts Texas at 80.5% and X buzz runs 79.7% Longhorns (8,615 vs. 2,191 posts).",
        "story_bullets": [
            "9-2 Texas enters off a 45-3 rout with Arch Manning rolling, while 4-7 A&M faces a QB shakeup between Marcel Reed and Brady Hart.",
            "Even with massive consensus on Texas, viral Aggie underdog stunts (like the '12th Cran' cranberry sauce bet with 64k+ views) drive high engagement.",
            "Benchmark control event: when the favorite is dominant on both the field and the timeline, X buzz share tracks Kalshi within ~1 percentage point."
        ],
        "activation_angle": "When odds are lopsided (80/20), pre-game winner polls are dull. Activate around rivalry fan stunts, over/under margin props, and tailgate challenges in College Station."
    },
    {
        "id": "KXNCAAFGAME-26NOV28MICHOSU",
        "category": "CFB",
        "tag": "CFB · THE GAME",
        "title": "Michigan at Ohio State",
        "subtitle": "Sat Nov 28, 11:00 AM CT · Ohio Stadium",
        "side_a": {"label": "Michigan Wolverines", "short": "MICH", "kalshi_sub": "Michigan", "x_series": "michigan"},
        "side_b": {"label": "Ohio State Buckeyes", "short": "OSU", "kalshi_sub": "Ohio St.", "x_series": "ohio_state"},
        "headline": "LARGEST DIVERGENCE: Kalshi prices Ohio State at 77.5% (-10.5), yet X buzz (58.8% Michigan) and fan sentiment back the Wolverines after OSU's loss to Nebraska.",
        "story_bullets": [
            "Ohio State lost 31-28 to Nebraska on Nov 21 (3 losses in 4 games) and hasn't beaten Michigan at home since 2018; Ryan Day sits 2-4 in the rivalry.",
            "Even Ohio State fan accounts note Buckeye supporters picking Michigan on the timeline, creating a 35+ point gap between X crowd sentiment and Kalshi's 22.5% Michigan price.",
            "Michigan upset No. 4 UCLA last weekend, fueling 'rivalry chaos' narratives all week across 19,849 combined X posts."
        ],
        "activation_angle": "Flagship divergence activation: 'The Timeline vs. The Money.' Set up tailgate/campus activation content in Columbus and Big Ten watch bars asking fans why they doubt a 77.5% favorite."
    },
    {
        "id": "KXNFLMVP-27",
        "category": "Futures",
        "tag": "NFL FUTURES · $50.1M VOL",
        "title": "2026 NFL MVP Race",
        "subtitle": "Head-to-Head Focus: Brock Purdy vs. Joe Burrow",
        "side_a": {"label": "Brock Purdy", "short": "PURDY", "kalshi_sub": "Brock Purdy", "x_series": "purdy_mvp", "raw_cents": True},
        "side_b": {"label": "Joe Burrow", "short": "BURROW", "kalshi_sub": "Joe Burrow", "x_series": "burrow_mvp", "raw_cents": True},
        "headline": "Purdy just overtook Burrow on Kalshi (39.5c vs 36.5c; 52.0% H2H) after Burrow's MNF loss, yet X volume (57.9% Burrow) and MVP debate threads still lean heavily toward Burrow.",
        "story_bullets": [
            "KalshiSports broke the flip on Nov 24 at 9:31 AM CT (135k+ views): Purdy surged ahead after 49ers hit 9-1 and Cincinnati fell 22-20 to Washington.",
            "Bengals fans and neutral NFL accounts overwhelmingly argue Burrow is 'more valuable' to a weaker roster, keeping X sentiment ~64% Burrow in head-to-head debate.",
            "Massive $50.1M contract volume ($868.5k in 24h) makes MVP the sharpest real-time narrative market on Kalshi."
        ],
        "activation_angle": "Turn live QB prime-time performances into dynamic MVP ticker graphics for sports podcasts and creator partners; narrative lag between X sentiment and live market repricing creates instant debate fuel."
    },
    {
        "id": "KXHEISMAN-27",
        "category": "Futures",
        "tag": "CFB FUTURES · $49.8M VOL",
        "title": "2026 Heisman Trophy",
        "subtitle": "Frontrunner vs. Top Challengers (Smith vs. Dampier & Mensah)",
        "side_a": {"label": "Jeremiah Smith", "short": "SMITH", "kalshi_sub": "Jeremiah Smith", "x_series": "smith_heisman", "raw_cents": True},
        "side_b": {"label": "Dampier & Mensah", "short": "FIELD", "kalshi_sub_list": ["Devon Dampier", "Darian Mensah"], "x_series": "dampier_mensah_heisman", "raw_cents": True},
        "headline": "Strong consensus on Ohio State WR Jeremiah Smith (79.5c on Kalshi; 80.7% H2H vs top 2 QBs), though undefeated Utah QB Devon Dampier draws vocal underdog support.",
        "story_bullets": [
            "Jeremiah Smith commands 72.6% of top-contender X volume (1,089 posts) and holds ~80% implied odds on Kalshi ($49.8M total market volume).",
            "Contrarian CFB analysts argue 10-0 Utah's Devon Dampier deserves the award over a 7-4 Ohio State receiver, sparking lively debate before rivalry Saturday.",
            "If Michigan upsets Ohio State on Nov 28, both The Game and Heisman markets will reprice simultaneously."
        ],
        "activation_angle": "Pair The Game (Michigan-OSU) with live Heisman odds tracking: every Jeremiah Smith touchdown or stop in Columbus moves a $50M awards market in real time."
    },
    {
        "id": "KXOSCARPIC-27",
        "category": "Culture",
        "tag": "CULTURE · 99TH OSCARS · $13.8M VOL",
        "title": "Oscars Best Picture",
        "subtitle": "The Odyssey vs. You Can See Everything & Dune: Part Three",
        "side_a": {"label": "The Odyssey", "short": "ODYSSEY", "kalshi_sub": "The Odyssey", "x_series": "odyssey_oscar", "raw_cents": True},
        "side_b": {"label": "YCSE & Dune 3", "short": "FIELD", "kalshi_sub_list": ["You Can See Everything", "Dune: Part Three"], "x_series": "dune_ycse_oscar", "raw_cents": True},
        "headline": "Christopher Nolan's The Odyssey leads both Kalshi (52.5c; 61.4% H2H) and Film Twitter buzz (71.9% vs. Dune/YCSE), while Nathan Fielder's You Can See Everything is surging on Nov 24.",
        "story_bullets": [
            "Market and Film Twitter agree on the frontrunner: Nolan's The Odyssey sits around 53% on Kalshi and tops critics' early Oscar ballots.",
            "Fastest riser on X: A24's You Can See Everything (23.5c) grew from 43 daily posts a week ago to 157 posts on Nov 24, alongside Dune: Part Three (9.5c) teaser buzz.",
            "Demonstrates how prediction markets quantify non-sports cultural momentum months before awards night."
        ],
        "activation_angle": "Culture-first Kalshi activation: partner with indie theaters, film festivals, and awards podcasts (similar to a Miami Art Week / screening room activation) with live 'Best Picture Stock Exchange' boards."
    }
]


def main():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ct = now_utc.astimezone(CT_TZ)

    x_counts = json.loads(RAW_COUNTS_PATH.read_text(encoding="utf-8"))
    x_posts = json.loads(RAW_POSTS_PATH.read_text(encoding="utf-8"))

    events_out = []
    for meta in EVENTS_META:
        eid = meta["id"]
        ev_api = fetch_kalshi_event(eid)
        mkts = ev_api.get("markets", [])
        by_sub = {m.get("yes_sub_title"): m for m in mkts}

        # Side A Kalshi mid
        m_a = by_sub[meta["side_a"]["kalshi_sub"]]
        raw_a = mid_price(m_a)

        # Side B Kalshi mid (single market or sum of listed challengers)
        if "kalshi_sub_list" in meta["side_b"]:
            m_b_list = [by_sub[s] for s in meta["side_b"]["kalshi_sub_list"] if s in by_sub]
            raw_b = sum(mid_price(m) for m in m_b_list)
        else:
            m_b = by_sub[meta["side_b"]["kalshi_sub"]]
            raw_b = mid_price(m_b)

        denom_k = raw_a + raw_b
        kalshi_a_pct = round((raw_a / denom_k) * 100.0, 1) if denom_k > 0 else 50.0
        kalshi_b_pct = round(100.0 - kalshi_a_pct, 1)

        total_contracts = sum(float(m.get("volume_fp") or 0) for m in mkts)
        vol_24h = sum(float(m.get("volume_24h_fp") or 0) for m in mkts)

        # Volume skew (contracts on A vs B when head-to-head)
        vol_a = float(m_a.get("volume_fp") or 0)
        if "kalshi_sub_list" in meta["side_b"]:
            vol_b = sum(float(m.get("volume_fp") or 0) for m in m_b_list)
        else:
            vol_b = float(m_b.get("volume_fp") or 0)
        vol_a_share = round((vol_a / (vol_a + vol_b)) * 100.0, 1) if (vol_a + vol_b) > 0 else 50.0

        # X 7-day buzz counts
        cnt_a = x_counts["series"][meta["side_a"]["x_series"]]["total"]
        cnt_b = x_counts["series"][meta["side_b"]["x_series"]]["total"]
        buzz_a_pct = round((cnt_a / (cnt_a + cnt_b)) * 100.0, 1)
        buzz_b_pct = round(100.0 - buzz_a_pct, 1)

        # X sample sentiment scoring (deduplicated 1 vote per unique author handle)
        posts_raw = x_posts["events"].get(eid, [])
        author_votes = {}
        scored_posts = []
        for p in posts_raw:
            direction = "N" if p["author"] == "KalshiSports" else score_post_direction(eid, p["text"])
            handle = p["author"]
            scored_posts.append({
                "author": handle,
                "url": f"https://x.com/{handle}/status/{p['id']}",
                "created_at": p["created_at"],
                "likes": p["likes"],
                "impressions": p["impressions"],
                "text": p["text"],
                "lean": direction,
            })
            if direction in ("A", "B") and handle not in author_votes:
                author_votes[handle] = direction

        votes_a = sum(1 for v in author_votes.values() if v == "A")
        votes_b = sum(1 for v in author_votes.values() if v == "B")
        dir_total = votes_a + votes_b
        if dir_total >= 3:
            sent_a_pct = round((votes_a / dir_total) * 100.0, 1)
            sent_b_pct = round(100.0 - sent_a_pct, 1)
            crowd_a_pct = round(0.5 * buzz_a_pct + 0.5 * sent_a_pct, 1)
        else:
            sent_a_pct = buzz_a_pct
            sent_b_pct = buzz_b_pct
            crowd_a_pct = buzz_a_pct
        crowd_b_pct = round(100.0 - crowd_a_pct, 1)

        div_pp = round(crowd_a_pct - kalshi_a_pct, 1)
        abs_div = round(abs(div_pp), 1)
        if abs_div >= 12.0:
            regime = "HIGH DIVERGENCE"
        elif abs_div >= 5.0:
            regime = "MODERATE SPLIT"
        else:
            regime = "CONSENSUS"

        # Pick top representative non-neutral posts for UI evidence (1 A, 1 B, plus top engagement)
        side_a_posts = sorted([p for p in scored_posts if p["lean"] == "A"], key=lambda x: (x["likes"], x["impressions"]), reverse=True)
        side_b_posts = sorted([p for p in scored_posts if p["lean"] == "B"], key=lambda x: (x["likes"], x["impressions"]), reverse=True)
        neutral_posts = sorted([p for p in scored_posts if p["lean"] == "N"], key=lambda x: (x["likes"], x["impressions"]), reverse=True)
        evidence = []
        if side_a_posts:
            evidence.append(side_a_posts[0])
        if side_b_posts:
            evidence.append(side_b_posts[0])
        for pool in (side_a_posts[1:], side_b_posts[1:], neutral_posts):
            for item in pool:
                if len(evidence) < 3 and item not in evidence:
                    evidence.append(item)

        events_out.append({
            "id": eid,
            "category": meta["category"],
            "tag": meta["tag"],
            "title": meta["title"],
            "subtitle": meta["subtitle"],
            "kalshi_url": f"https://kalshi.com/events/{eid}",
            "side_a": {
                "label": meta["side_a"]["label"],
                "short": meta["side_a"]["short"],
                "kalshi_raw_cents": round(raw_a * 100.0, 1),
                "kalshi_h2h_pct": kalshi_a_pct,
                "x_posts_7d": cnt_a,
                "x_buzz_pct": buzz_a_pct,
                "x_sentiment_votes": votes_a,
                "x_sentiment_pct": sent_a_pct,
                "x_crowd_pct": crowd_a_pct,
                "kalshi_vol_share_pct": vol_a_share,
                "daily_series": x_counts["series"][meta["side_a"]["x_series"]]["daily"],
            },
            "side_b": {
                "label": meta["side_b"]["label"],
                "short": meta["side_b"]["short"],
                "kalshi_raw_cents": round(raw_b * 100.0, 1),
                "kalshi_h2h_pct": kalshi_b_pct,
                "x_posts_7d": cnt_b,
                "x_buzz_pct": buzz_b_pct,
                "x_sentiment_votes": votes_b,
                "x_sentiment_pct": sent_b_pct,
                "x_crowd_pct": crowd_b_pct,
                "kalshi_vol_share_pct": round(100.0 - vol_a_share, 1),
                "daily_series": x_counts["series"][meta["side_b"]["x_series"]]["daily"],
            },
            "is_multi_outcome": bool(meta["side_a"].get("raw_cents")),
            "total_contracts": round(total_contracts),
            "vol_24h_contracts": round(vol_24h),
            "x_total_7d": cnt_a + cnt_b,
            "sample_posts_n": len(posts_raw),
            "sample_directional_n": dir_total,
            "divergence_pp": div_pp,
            "abs_divergence_pp": abs_div,
            "regime": regime,
            "divergence_summary": (
                f"Crowd +{abs_div:.1f} pp on {meta['side_a']['short']}"
                if div_pp > 0
                else f"Crowd +{abs_div:.1f} pp on {meta['side_b']['short']}"
                if div_pp < 0
                else "0.0 pp exact match"
            ),
            "headline": meta["headline"],
            "story_bullets": meta["story_bullets"],
            "activation_angle": meta["activation_angle"],
            "evidence_posts": evidence,
        })

    # Sort copy of top divergences for summary stats
    ranked_div = sorted(events_out, key=lambda e: e["abs_divergence_pp"], reverse=True)
    snapshot = {
        "kalshi_updated_ct": now_ct.strftime("%b %d, %Y at %I:%M %p CT"),
        "kalshi_updated_iso": now_ct.isoformat(),
        "x_snapshot_ct": "Nov 24, 2026 at 4:57 PM CT",
        "x_window_label": "7-day X window (Nov 17 - Nov 24, 2026)",
        "total_events": len(events_out),
        "total_x_posts_7d": sum(e["x_total_7d"] for e in events_out),
        "total_kalshi_contracts": sum(e["total_contracts"] for e in events_out),
        "top_divergences": [
            {
                "id": e["id"],
                "title": e["title"],
                "abs_divergence_pp": e["abs_divergence_pp"],
                "divergence_summary": e["divergence_summary"],
                "kalshi_label": f"{e['side_a']['short']} {e['side_a']['kalshi_h2h_pct']:.1f}%",
                "crowd_label": f"{e['side_a']['short']} {e['side_a']['x_crowd_pct']:.1f}%",
            }
            for e in ranked_div[:3]
        ],
        "events": events_out,
    }

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    # Build HTML if template exists
    if TEMPLATE_PATH.exists():
        import base64
        tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
        for font_name, token in [
            ("archivo.woff2", "__FONT_ARCHIVO__"),
            ("archivoblack.woff2", "__FONT_ARCHIVO_BLACK__"),
            ("dmmono.woff2", "__FONT_DMMONO__"),
        ]:
            fp = ROOT / "src" / font_name
            if fp.exists():
                b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
                tpl = tpl.replace(token, f"data:font/woff2;base64,{b64}")
        tpl = tpl.replace("__SNAPSHOT_JSON__", json.dumps(snapshot))
        for out_p in OUT_HTML_PATHS:
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(tpl, encoding="utf-8")

    # Print diagnostic summary
    for e in ranked_div:
        print(
            f"{e['abs_divergence_pp']:5.1f} pp | {e['regime']:15} | {e['title']:24} | "
            f"Kalshi {e['side_a']['short']}={e['side_a']['kalshi_h2h_pct']:4.1f}% | "
            f"X Buzz={e['side_a']['x_buzz_pct']:4.1f}% ({e['side_a']['x_posts_7d']}/{e['side_b']['x_posts_7d']}) | "
            f"X Sent={e['side_a']['x_sentiment_pct']:4.1f}% ({e['side_a']['x_sentiment_votes']}A/{e['side_b']['x_sentiment_votes']}B, n={e['sample_posts_n']}) | "
            f"Crowd={e['side_a']['x_crowd_pct']:4.1f}%"
        )


if __name__ == "__main__":
    main()
