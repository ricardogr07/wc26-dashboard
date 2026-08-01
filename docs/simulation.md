# Simulation

> 🏆 **The tournament is over.** The simulate page now shows the final archived
> run (Ricardo 100%, Spain won), and the engine described here no longer runs
> in production. This document describes how it worked during the tournament.

The simulate page answers one question: **given all matches played so far, what is each participant's probability of having the overall tournament winner?**

## What "win probability" means

Each participant was assigned 5 national teams before the tournament started. The simulation runs the remainder of the tournament 10,000 times and counts how often each participant's team lifts the trophy. The result is a single number per participant:

```
{ "ricardo": 0.23, "chuy": 0.18, "jaime": 0.31, ... }
```

These probabilities are *not* guaranteed to sum to 1.0. With 48 teams in the tournament and 5 participants × 5 teams = 25 teams owned, there are 23 unowned teams. In runs where an unowned team wins, nobody gets credited.

## How the engine works

Source: `api/simulation/engine.py` and `api/simulation/bracket.py`.

### Elo-based win probability

Each team has an Elo rating updated after every completed match. The probability that team A beats team B in a neutral-site match is:

```
P(A beats B) = 1 / (1 + 10^((elo_B - elo_A) / 400))
```

This is the standard Elo formula with a 400-point divisor.

### Group stage simulation

For each of the 12 groups (A–L), the engine:

1. **Applies known results**: completed matches contribute their actual goals/winner to points and goal difference tallies.
2. **Simulates pending matches**: each unplayed group match is sampled from the Elo win probability. There is a built-in 25% draw rate: the engine splits the remaining probability between a home win and an away win.
3. **Ranks teams**: by points, then goal difference, then a random tiebreak (stand-in for FIFA's drawing-of-lots tiebreaker).

### Knockout bracket

WC2026 uses a 48-team group stage → 32-team knockout format:
- Top 2 from each group (24 teams) + 8 best 3rd-place teams = 32 qualifiers
- R32 → R16 → QF → SF → Final

The bracket slots follow the official FIFA WC2026 draw structure (see `bracket.py`). The 8 best 3rd-place teams are selected randomly (random tiebreak among the twelve 3rd-place finishers after points and goal difference).

Each knockout match is simulated with the Elo win probability: no draws, one team advances.

### Champion counting

After every simulated run, the engine records who owns the Final winner:

```python
champion = final_winners[0]
if champion in team_owner:
    champion_counts[team_owner[champion]] += 1
```

After all runs, `win_probabilities[participant_id] = champion_counts[participant_id] / n_runs`.

### Caching

The result is stored as `simulationRun_latest` in Cosmos DB. On the next request, if the number of completed matches hasn't changed and no overrides are provided, the cached document is returned immediately; no re-simulation needed. The cache is automatically invalidated when a new match result is synced.

---

## Scenario Builder (historical)

The **Scenario Builder** on the simulate page let you fix hypothetical match outcomes and re-run the simulation. For example: "what if Mexico wins Group A, how does that change Jaime's odds?" The card is still visible on the page as an artifact, but with every match completed there is nothing left to override.

When you selected a winner for one or more future matches, the frontend sent those overrides to `POST /api/simulate`:

```json
{
  "overrides": [
    { "matchId": "tsdb_2391728", "winnerId": "MEX", "homeScore": 1, "awayScore": 0 }
  ],
  "nRuns": 10000
}
```

The handler patches the in-memory match list with the overrides before running the engine. Scenario runs are never cached; they're always computed fresh.

The UI shows each participant's scenario probability alongside a delta (`+X.Xpp` / `-X.Xpp`) versus the baseline.

---

## Scoring system

Points are separate from win probabilities. The simulation engine doesn't use the scoring system; that's `api/scoring.py` which powers the standings page. But they're related:

| Event | Points |
|---|---|
| Team qualifies for Round of 32 | +1 |
| Team wins Round of 32 match | +2 |
| Team wins Round of 16 match | +3 |
| Team wins Quarterfinal | +5 |
| Team wins Semifinal | +8 |
| Team wins Final (champion) | +13 |

A participant's total score is the sum across all 5 of their teams.

---

## Limitations

- **Draw rate is constant**: the 25% draw rate applies equally to all group-stage matches, regardless of the actual teams or stakes. High-stakes final matchday games often have lower draw rates in practice.
- **No extra time or penalties**: knockout matches resolve in 90 minutes (winner selected from the Elo probability). In reality, roughly 1 in 4 knockout matches goes to extra time.
- **Elo doesn't account for squad rotation, injuries, or form**: ratings reflect historical performance up to the last synced match result.
- **3rd-place seeding is simplified**: FIFA uses a complex seeding table for the 3rd-place bracket slots. The engine selects them randomly by rank, which is a valid approximation but not the official rule.
- **Unowned teams**: 23 of 48 teams are unowned. When one of them wins, the probabilities don't sum to 1.0. This is by design.
