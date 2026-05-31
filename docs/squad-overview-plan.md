# Squad Performance Overview — Implementation Plan

## 1. Component Audit

### 1.1 Existing & Ready

| Component | Data Source | API Endpoint | Notes |
|-----------|-------------|-------------|-------|
| **Match Banner** | Match data, team stats | `MatchAPI.getMatchReport(matchId)` + `TeamAPI.getTeamSummary(teamId, matchId)` | Returns teams, score, date, match stats (possession, shots, xG, passes, pressures) |
| **KPI Strip** (8 cards) | Team-level aggregates | `TeamAPI.getTeamSummary(teamId, matchId)` → `team_stats` | avg_overall_score, total_xg, pass_accuracy, total_pressures all available. Dribbles/VAEP not in team summary — must aggregate from player scores |
| **Squad Table base** | Player list + scores | `PlayerAPI.getPlayerList()` + `PlayerAPI.getPlayerScore(id)` per player | Player name, position_group, 7 dimension scores, overall_score, vaep_rating all available |
| **Position filter** | position_group field | Client-side filtering | Same pattern as PlayerList.js |
| **Search filter** | player_name field | Client-side filtering | Same pattern as PlayerList.js |
| **Trend badge** | `performance_trend` field | `PlayerAPI.getPlayerScore(id)` → `performance_trend` | Values: "Improving"/"Declining"/"Stable" |
| **VAEP column** | `vaep.vaep_rating` | `PlayerAPI.getPlayerScore(id)` → `vaep.vaep_rating` | Available per player per match |
| **xG column** | `shooting.total_xg` | `PlayerAPI.getPlayerStats(id)` → `shooting.total_xg` | Available per player per match |
| **Position Benchmarks** | Position averages | `BenchmarkAPI.getBenchmark(position_group)` → `averages` | Already has 4 position groups |
| **Season Score Distribution** | Match report all_players[] scores | `MatchAPI.getMatchReport(matchId)` → `all_players[].overall_score` | Distribution of all player scores in a match |
| **Squad Season Trend** | History across matches | Aggregation across all players' `PlayerAPI.getPlayerHistory(id)` | Can compute weekly average |

### 1.2 Buildable with Existing Resources

| Component | What's Needed | Approach |
|-----------|--------------|----------|
| **Last 5 Sparkline** | Last 5 matches' overall_score per player | `PlayerAPI.getPlayerHistory(playerId)` → `matches[].overall_score`, take last 5. Requires **1 API call per player**. Recommended: add `?last_n=5` query param to `/player/{id}/history` or create a batch endpoint |
| **Pass Accuracy column** | `pass_accuracy` | `PlayerAPI.getPlayerStats(playerId)` → `passing.pass_accuracy`. Same per-player call issue |
| **Dribble Success % column** | `dribble_success_rate` | NOT in current stats API's `movement` block (which uses `total_carries`). Must add `dribble_success_rate` to the stats response, or extract via raw `computed_features.parquet` |
| **Player Cluster badge** | `player_cluster` | `PlayerAPI.getPlayerScore(id)` → `player_cluster`. The HTML uses different cluster labels (creator/presser/engine/anchor/dribbler/stopper/keeper) — map existing cluster labels or rename |
| **Player avatar color** | Deterministic color per player | Compute HSL color from player_id hash — consistent across sessions |
| **Trend value (numeric)** | Slope of recent scores | Compute from `PlayerAPI.getPlayerHistory(id)` → recent N matches' score deltas |
| **AI Match Insights** | Derived from data | Top Performer = max score; Most Improved = max ∆ from previous match; Declining = min trend; Below avg = below season mean |
| **KPI: Dribbles count** | Player-level dribble aggregate | `PlayerAPI.getPlayerStats(id)` for each player, sum `dribble_success_rate` × actions or sum raw dribbles |
| **KPI: Team VAEP** | Player VAEP aggregate | Sum `vaep_rating` across all players from `PlayerAPI.getPlayerScore(id)` for each player |

### 1.3 Not Buildable — Deferred

| Component | Reason | Resolution |
|-----------|--------|-----------|
| **FIFA 16 Rating** | No FIFA rating data in any backend dataset or 3rd-party integration | **Remove column** from table. Replace with "Position Fit" column using existing `position_fit_score` |
| **Δ vs FIFA** | Depends on FIFA 16 data | Remove with FIFA column |
| **Squad number (#2, #10…)** | HTML mock uses `Math.random()`; real squad numbers not in data | **Remove** from player name cell — only show name + position label |
| **6 distinct cluster badge styles** | HTML has custom labels `creator`/`presser`/`engine`/`anchor`/`dribbler`/`stopper`/`keeper` — API has different cluster names from model_scores | Map existing `player_cluster` values to simplified short labels. If API values are descriptive strings (e.g., "Creative Playmaker"), create a mapping table. If missing entirely, **omit cluster column** as secondary |

### Assumptions Made

1. The "current match" context for the banner defaults to the latest match. Match selector dropdown uses real match IDs from `matches.parquet`.
2. Trend values (numeric, e.g. +0.8, -0.4) are computed client-side from history data as `last_score - avg_of_previous_N` or similar slope.
3. The `BenchmarkAPI.getBenchmark()` endpoint returns position-group level averages that can be displayed as horizontal bars.
4. The `performance_trend` field in model_scores uses "Improving"/"Declining"/"Stable" — HTML uses "up"/"dn"/"st" — these map directly.

---

## 2. Technical Implementation Plan

### 2.1 Component Breakdown

```
SquadOverview (page component)
├── MatchBanner
│   ├── Team display (name, badge, home/away)
│   ├── Score display
│   ├── Match stats row (possession, shots, xG, result)
│   └── Match selector (dropdown + prev/next buttons)
├── KPIStrip
│   └── KPI card × 8
├── AIInsights
│   └── InsightCard × 4 (Top Performer, Improved, Declining, Below Baseline)
├── SquadTable (main)
│   ├── FilterBar (search input, position buttons, trend buttons)
│   ├── Table header (sortable columns, 15 columns)
│   ├── PlayerRow × N
│   │   ├── PlayerNameCell (avatar + name + position label)
│   │   ├── PositionBadge (GK/DF/MF/FW)
│   │   ├── MLScorePill (elite/great/good/avg/poor)
│   │   ├── ScoreDisplay × 5 (pass/shoot/pos/press/move)
│   │   ├── MetricCell (VAEP, xG, pass acc, dribble %)
│   │   ├── ClusterBadge
│   │   └── Sparkline (last 5)
│   └── Table footer (row count)
├── PositionBenchmarks
│   ├── Position group section × 3 (FW, MF, DF) — GK omitted
│   ├── BenchmarkRow per metric (ML Score, xG/Shot, Drib%, Pass Acc, Press%, Distance)
│   └── Match/Season selector toggle
└── SeasonOverview
    ├── ScoreDistribution (histogram bars)
    ├── SeasonTrend (mini bar chart per week)
    └── SeasonStats summary (avg, best, worst)
```

### 2.2 Data Requirements

#### PlayerRow (core data structure per row)
```typescript
interface PlayerRow {
  player_id: number;
  player_name: string;
  team_name: string;
  position_group: 'GK' | 'Defender' | 'Midfielder' | 'Attacker';
  position_label: string;        // short label like "RW", "ST", "CM"
  overall_score: number;         // 0-10
  scores: {
    passing: number;
    shooting: number;
    positioning: number;
    pressing: number;
    movement: number;
  };
  vaep_rating: number;
  total_xg: number;
  pass_accuracy: number;         // 0-100
  dribble_success_rate: number;  // 0-100
  player_cluster: string;
  performance_trend: 'Improving' | 'Declining' | 'Stable';
  trend_value: number;           // computed numeric delta
  last_5_scores: number[];       // up to 5 recent overall_scores
}
```

#### MatchContext (for banner + KPIs)
```typescript
interface MatchContext {
  match_id: number;
  match_date: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  match_week: number;
  team_stats: {
    avg_overall_score: number;
    total_xg: number;
    pass_accuracy: number;
    total_pressures: number;
    possession_pct: number;
    total_shots: number;
    shots_on_target: number;
  };
}
```

#### AIInsight
```typescript
interface AIInsight {
  type: 'top_performer' | 'most_improved' | 'declining' | 'below_baseline';
  player_name: string;
  value: string;         // displayed value like "8.2 / 10" or "+1.6 pts"
  description: string;   // human-readable insight text
}
```

### 2.3 API / Endpoint Mapping

| Frontend Need | Endpoint | Request | Response Fields Used | Performance |
|--------------|----------|---------|---------------------|-------------|
| Load all players for table | `GET /player/list` | none | `player_items[].player_id, player_name, team_name` | 1 call |
| Get player scores + cluster + vaep | `GET /player/{id}/score?match_id={matchId}` | player_id, optional match_id | `scores{overall_score, passing_score, shooting_score, positioning_score, pressing_score, movement_score}, vaep{vaep_rating}, player_cluster, performance_trend` | N calls (one per player) — **HIGH COST** |
| Get player stats (xg, pass_accuracy) | `GET /player/{id}/stats?match_id={matchId}` | player_id, optional match_id | `passing.pass_accuracy, shooting.total_xg, ...dribble_success_rate?` | N calls — **HIGH COST** |
| Get player history (last 5, trend) | `GET /player/{id}/history` | player_id | `matches[].overall_score, season_avg` | N calls — **HIGH COST** |
| Get match context | `GET /match/{matchId}/report` | match_id | `match_date, home_team, away_team, score, all_players[]` | 1 call |
| Get team stats (KPIs) | `GET /team/{teamId}/summary?match_id={matchId}` | team_id, match_id | `team_stats{avg_overall_score, total_xg, pass_accuracy, total_pressures}` | 1 call |
| Get benchmarks | `GET /benchmark/{position_group}` | position_group | `averages{...}` | 1 call per group (3-4 calls) |
| **NEW: Batch squad scores** | `GET /player/squad-scores?match_id={matchId}` | match_id | Returns array of PlayerRow for all players in one call | **1 call** |
| **NEW: Add dribble_success_rate** to stats | Extend stats endpoint | — | Add `movement.dribble_success_rate` to `/player/{id}/stats` | Free |

> **⚠ Performance Issue**: The naive approach requires 2N+3 API calls (N = number of players, ~18). **Critical**: Add a `GET /player/squad-scores?match_id={matchId}` batch endpoint that returns all player rows in one response by aggregating scores, stats, and history in the backend.

### 2.4 New Backend Endpoint: `GET /player/squad-scores`

```python
# api/routes/squad.py (NEW FILE)
@router.get("/player/squad-scores")
def get_squad_scores(match_id: int = None):
    """
    Returns all players with their scores, stats, clusters, and last-5 history
    in a single response. This is the primary data source for the Squad Overview page.
    """
```

**Response shape:**
```json
{
  "match_id": 265839,
  "match_context": {
    "match_date": "2016-01-30",
    "home_team": "FC Barcelona",
    "away_team": "Atlético Madrid",
    "home_score": 3,
    "away_score": 1,
    "match_week": 21
  },
  "team_stats": {
    "avg_overall_score": 7.0,
    "total_passes": 856,
    "total_shots": 18,
    "shots_on_target": 8,
    "total_xg": 2.31,
    "possession_pct": 61.4,
    "total_pressures": 118,
    "pressure_regains": 34,
    "total_dribbles": 47,
    "dribble_success_pct": 68.1,
    "team_vaep": 5.82
  },
  "players": [
    {
      "player_id": 123,
      "player_name": "L. Suárez",
      "team_name": "FC Barcelona",
      "position_group": "Attacker",
      "position_label": "ST",
      "overall_score": 8.2,
      "scores": {
        "passing": 7.1,
        "shooting": 9.2,
        "positioning": 8.8,
        "pressing": 6.1,
        "movement": 8.4
      },
      "vaep_rating": 1.88,
      "total_xg": 1.12,
      "pass_accuracy": 80.2,
      "dribble_success_rate": 58.0,
      "player_cluster": "Dribbler",
      "performance_trend": "Improving",
      "trend_value": 0.8,
      "last_5_scores": [7.0, 7.4, 7.8, 7.9, 8.2]
    }
  ],
  "insights": {
    "top_performer": { "player_name": "L. Suárez", "score": 8.2 },
    "most_improved": { "player_name": "A. Iniesta", "delta": 1.6, "prev": 5.8, "current": 7.4 },
    "declining": { "player_name": "S. Roberto", "delta": -0.8, "trend_over": 4 },
    "below_baseline_count": 3
  },
  "season_stats": {
    "season_avg": 7.0,
    "best_match_avg": 8.4,
    "worst_match_avg": 5.6,
    "weekly_averages": [6.2, 6.8, ...],
    "score_distribution": { "3-5": 4, "5-6": 8, "6-7": 28, "7-8": 42, "8-9": 16, "9+": 2 }
  }
}
```

### 2.5 Dependencies & Integration Points

| Component | Depends On | Connects To |
|-----------|-----------|-------------|
| `SquadOverview` (page) | New `squad-scores` endpoint | Fetch on mount + on match change |
| `SquadTable` | `players[]` from squad-scores | Row click → `onSelectPlayer(player_name, player_id)` → navigates to Player Profile |
| `MatchBanner` | `match_context` + `team_stats` from squad-scores | Match selector dropdown changes `match_id` → re-fetches |
| `KPIStrip` | `team_stats` from squad-scores | Pure display |
| `AIInsights` | `insights` from squad-scores | Pure display |
| `PositionBenchmarks` | `BenchmarkAPI.getBenchmark(pos)` | Fetches independently on mount |
| `SeasonOverview` | `season_stats` from squad-scores | Pure display |
| **Integration with existing** | `App.js` PAGES constant + navigation | Add `PAGES.SQUAD_OVERVIEW`; render `<SquadOverview />` in AppLayout |
| **Integration with existing** | Sidebar "Squad Performance" nav item | Links to `PAGES.SQUAD_OVERVIEW` |

### 2.6 Build Sequence

```
Phase 1: Backend
  Step 1 — Create GET /player/squad-scores batch endpoint in api/routes/squad.py
  Step 2 — Add dribble_success_rate to /player/{id}/stats response (modify existing route)
  Step 3 — Aggregate team_stats, insights, season_stats computation
  Step 4 — Register new route in main.py

Phase 2: Frontend — Data Layer
  Step 5 — Add squadAPI.getSquadOverview(matchId) to api.js
  Step 6 — Define TypeScript interfaces (PlayerRow, MatchContext, etc.)

Phase 3: Frontend — Components (bottom-up)
  Step 7 — Build PositionBenchmarks component
  Step 8 — Build AIInsights component  
  Step 9 — Build KPIStrip component (reusable KPICard)
  Step 10 — Build MatchBanner component (match selector + team display)
  Step 11 — Build SquadTable with all sub-cells (PlayerNameCell, ScoreDisplay, Sparkline, etc.)
  Step 12 — Build SeasonOverview (distribution chart + season trend)
  Step 13 — Build SquadOverview page (compose all sub-components)

Phase 4: Integration
  Step 14 — Add PAGES.SQUAD_OVERVIEW to AppContext
  Step 15 — Wire sidebar + page tabs to new route
  Step 16 — Add squad-scores API client method
  Step 17 — Build and verify
```

### 2.7 Validation & Error Handling

| Component | Validation | Edge Cases |
|-----------|-----------|------------|
| `SquadTable` | Sort function handles null/undefined values | Empty roster → "No players available" message |
| `MatchBanner` | Match selector has "Loading…" state | No matches in database → disable selector |
| `KPIStrip` | Missing KPI values show "—" | Partial data from API → individual KPI cards render with available data |
| `AIInsights` | Insights object may be partially null | Each insight card independently skips if its data is missing |
| `PositionBenchmarks` | Benchmark endpoint per position | Missing benchmark for a position → skip that section |
| `SeasonOverview` | Score distribution may be empty | Show "Not enough data" placeholder |
| **API error** | Top-level error boundary | Show ErrorAlert with retry button |
| **Loading** | Skeleton state for each section | Shimmer placeholder for table, cards |

### 2.8 Functional Completeness Check

All visible elements from the HTML reference:

| Element | Status | Notes |
|---------|--------|-------|
| ✅ Sidebar with nav items | Existing (Navigation component) | Just need to add link |
| ✅ Top bar with title, export buttons | Existing (App.js layout) | Export CSV/Report can be stubbed |
| ✅ Page tabs (Squad Overview active) | New | Add to existing page-tab system |
| ✅ Match Banner (teams, score, stats, selector) | New component | Full data available |
| ✅ KPI Strip (8 metric cards) | New component | Full data available |
| ✅ AI Insights (4 cards) | New component | Computed from player data |
| ✅ Search input | Reuse PlayerList pattern | Same debounced search hook |
| ✅ Position filter buttons (All/GK/DF/MF/FW) | Reuse pattern | Same as filter-by-position in existing code |
| ✅ Trend filter buttons (Improving/Declining) | New but trivial | Simple array filter |
| ✅ Player name + avatar + position label | New composite cell | Avatar color from player_id hash |
| ✅ Position badge (GK/DF/MF/FW) | New component | 4 color styles |
| ✅ ML Score (pill + bar) | New display | Use existing score ranges |
| ❌ FIFA 16 Rating | **Removed** | No FIFA data available. Replaced with Position Fit Score |
| ❌ Δ vs FIFA | **Removed** | No FIFA data available |
| ✅ Trend badge (up/down/stable + value) | New component | Data available |
| ✅ Passing, Shooting, Positioning, Pressing, Movement scores | New score cells | Each with colored bar |
| ✅ VAEP value | New cell | Available |
| ✅ xG value | New cell | From stats endpoint |
| ✅ Pass Accuracy % | New cell | From stats endpoint |
| ✅ Dribble Success % | New cell | Added to stats endpoint |
| ✅ Cluster badge | New component | Map API cluster values to short labels |
| ✅ Last 5 sparkline | New component | From player history |
| ✅ Position Benchmarks (FW/MF/DF) | New component | From benchmark endpoint |
| ✅ Season Score Distribution histogram | New component | From squad-scores `score_distribution` |
| ✅ Season Trend mini-chart | New component | From squad-scores `weekly_averages` |
| ✅ Season Stats summary (avg/best/worst) | New component | From squad-scores `season_stats` |
| ✅ Row count | New footer element | Derived from filtered data |

### 2.9 Files to Create / Modify

**New files:**
- `front-end/src/components/SquadOverview.js` — main page component
- `front-end/src/components/MatchBanner.js`
- `front-end/src/components/KPIStrip.js`
- `front-end/src/components/AIInsights.js`
- `front-end/src/components/SquadTable.js`
- `front-end/src/components/PositionBenchmarks.js`
- `front-end/src/components/SeasonOverview.js`

**Modified files:**
- `front-end/src/api.js` — add `squadAPI.getSquadOverview(matchId)`
- `front-end/src/App.js` — add `PAGES.SQUAD_OVERVIEW` route
- `front-end/src/context/AppContext.js` — add `PAGES.SQUAD_OVERVIEW` constant
- `front-end/src/components/Navigation.js` (or equivalent side nav) — add link
- `api/routes/squad.py` — **NEW BACKEND FILE**: `GET /player/squad-scores`
- `api/main.py` — register squad router
- `api/routes/player.py` — add `dribble_success_rate` to stats response

### 2.10 Styling Strategy

The HTML reference uses a dark theme with custom CSS variables. The current app uses a light theme with Tailwind classes. **Do not replicate the dark theme**. Instead:

- Use existing Tailwind utility classes (already in `index.css`)
- Apply the `surface` / `surface-muted` / `metric-card` patterns already established
- The squad table can reuse and extend the `squad-tbl` CSS class defined in `index.css` (it already exists in the `@layer components` section)
- Color coding: `score-bar` with gradient `from-brand-500 to-cyan-500` pattern (existing) — but use per-dimension colors inline as the HTML shows (blu for passing, red for shooting, grn for positioning, org for pressing, pur for movement)
