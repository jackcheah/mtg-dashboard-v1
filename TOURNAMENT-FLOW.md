# Tournament Flow Guide

A complete reference for how tournaments run in the MTG Tournament Dashboard — pairing logic, scoring mechanics, tiebreakers, and round progression. Covers all 4 combinations: Team/Individual mode with Western/Japanese scoring.

For setup, configuration, and operator instructions, see [README.md](README.md).

---

## Table of Contents

1. [Tournament Structure](#1-tournament-structure)
2. [Scoring Systems](#2-scoring-systems)
3. [Tournament Flow — Team Mode](#3-tournament-flow--team-mode)
4. [Tournament Flow — Individual Mode](#4-tournament-flow--individual-mode)
5. [Quick Reference — All 4 Flows](#5-quick-reference--all-4-flows)

---

## 1. Tournament Structure

The system automatically determines the round structure based on participant count:

**Team Mode:**

| Teams | Default Swiss Rounds | Playoffs | Total Rounds |
|-------|---------------------|----------|--------------|
| 8 | 4 | Finals (top 4 teams) | 5 |
| 12 | 4 | Finals (top 4 teams) | 5 |
| 16 | 4 | Top 8 Cut + Finals | 6 |
| 20-40 | 5 | Top 8 Cut + Finals | 7 |

**Individual Mode:**

| Players | Default Swiss Rounds | Playoffs | Total Rounds |
|---------|---------------------|----------|--------------|
| 16 or fewer | 4 | Finals (top 4 players) | 5 |
| 17+ | 4 | Top Cut (top 10) + Finals | 6 |

Swiss rounds are configurable to 3, 4, or 5 before the tournament starts.

---

## 2. Scoring Systems

### Western Mode (Default)

Players start at **0 points**. Points are awarded per round:

| Outcome | Points |
|---------|--------|
| Win | 5 |
| Draw | 1 |
| Loss | 0 |

**Team score** = sum of all 4 players' individual scores.

**Valid outcomes for a 4-player pod:**

| Outcome | Scores |
|---------|--------|
| 1 winner, 3 losers | (5, 0, 0, 0) |
| 2 draws, 2 losers | (1, 1, 0, 0) |
| 3 draws, 1 loser | (1, 1, 1, 0) |
| 4 draws | (1, 1, 1, 1) |

A pod can have at most 1 winner. If there is a winner, no draws are allowed (the other 3 must all be losses).

**Valid outcomes for a 3-player pod** (individual mode only):

| Outcome | Scores |
|---------|--------|
| 1 winner, 2 losers | (5, 0, 0) |
| 3 draws | (1, 1, 1) |
| 2 draws, 1 loser | (1, 1, 0) |

### Japanese Swiss Point Mode

Players start at **1000 points**. Each round, a pool-based calculation determines point changes:

1. Every player at the table contributes **7% of their current points** (rounded) to a shared pool
2. If there is a **winner**: the winner receives the entire pool. All others lose their contribution.
3. If there is a **draw** (no winner): every player loses their contribution. The pool disappears — points are destroyed.

**Key properties:**
- Points can never reach 0 (7% of any positive number stays positive)
- Draws are a net loss for everyone at the table
- Winners gain significantly more than losers lose, creating large score differentials
- Team score = sum of all 4 players' Japanese point totals

#### Worked Example

**Round 1** — 4 players, each starting with 1000 points:

| Player | Current | Contribution (7%) | Result | New Score |
|--------|---------|-------------------|--------|-----------|
| Alice | 1000 | 70 | **Win** | 1000 - 70 + 280 = **1210** |
| Bob | 1000 | 70 | Loss | 1000 - 70 = **930** |
| Carol | 1000 | 70 | Loss | 1000 - 70 = **930** |
| Dave | 1000 | 70 | Loss | 1000 - 70 = **930** |

Pool = 70 + 70 + 70 + 70 = **280 points**. Alice wins the pool.

**Round 2** — Same players with varied scores (different table assignments):

| Player | Current | Contribution (7%) |
|--------|---------|-------------------|
| Alice | 1210 | round(1210 x 0.07) = **85** |
| Eve | 930 | round(930 x 0.07) = **65** |
| Frank | 1050 | round(1050 x 0.07) = **74** |
| Grace | 980 | round(980 x 0.07) = **69** |

Pool = 85 + 65 + 74 + 69 = **293 points**

If Eve wins: Eve goes from 930 to 930 - 65 + 293 = **1158**. Others each lose their contribution.

**Draw example** — If no one wins at the table, ALL players lose their 7% contribution and no one receives the pool. The 293 points in the pool are simply removed from the game.

---

## 3. Tournament Flow — Team Mode

### Swiss Rounds

Each Swiss round creates pods of 4 players from 4 different teams. Teammates are **never** placed in the same pod (hard constraint).

#### Round 1: Random Grouping

1. All teams are shuffled randomly into groups of 4
2. Within each group, players are assigned to 4 pods using the **pod-consistency algorithm**: each pod gets exactly 1 player from each team
3. Multiple valid assignments are generated and one is chosen randomly for variety

#### Rounds 2-3: Traditional Swiss

1. **Sort** all teams by current score (highest first)
2. **Group** into brackets of 4: top 4 teams form Group 1, next 4 form Group 2, etc.
3. **Swap** (Layer 2): If any group contains teams that have already faced each other, the lowest-scored repeat team is swapped with a team from an adjacent bracket. The swap must not create new repeats. Up to 10 attempts per conflict.
4. **Optimize** (Layer 3): Within each group, exhaustive permutation search assigns players to pods to minimize player-level repeat matchups (up to 13,824 combinations per group).

#### Round 4+: Anti-Collusion Snake Pairing

To prevent top teams from colluding via intentional draws, rounds 4+ use **snake/interleave grouping** that spreads top teams across different pods.

Teams are sorted by score, then assigned in a snake pattern:

**Example with 16 teams (4 groups):**

| Group | Seeds |
|-------|-------|
| Group 1 | 1, 8, 9, 16 |
| Group 2 | 2, 7, 10, 15 |
| Group 3 | 3, 6, 11, 14 |
| Group 4 | 4, 5, 12, 13 |

Each group contains one team from each quartile of the standings, so top teams cannot face each other. Layer 2 (team swap) and Layer 3 (player permutation) still apply on top of this grouping.

#### The 3-Layer Optimization System

Every round after Round 1 uses three layers of optimization:

| Layer | What it does | Scope |
|-------|-------------|-------|
| **Layer 1: Grouping** | Decides which 4 teams play together | Determines the grouping algorithm (Swiss or snake) |
| **Layer 2: Team Swap** | Fixes team-level repeat matchups | Swaps teams between adjacent brackets |
| **Layer 3: Player Permutation** | Minimizes player-level repeats within each group | Exhaustive search of player-to-pod assignments |

**Strict matchup guarantee:** For tournaments with 16+ teams and up to 5 Swiss rounds, the system guarantees zero repeat team matchups across all Swiss rounds. The feasibility formula is: `swiss_rounds x 3 <= team_count - 1`. For 8 and 12 team tournaments, some repeats are unavoidable.

### Scoring During Swiss Rounds

After each round:

1. **Submit table scores** — The operator enters Win/Draw/Loss for each player at each table
2. **(Western)** Points are added directly: +5 for win, +1 for draw, +0 for loss
3. **(Japanese)** The 7% pool calculation is applied per table: contributions computed, pool distributed to winner or destroyed on draw
4. **Team scores recalculated** — Sum of all 4 players' current scores
5. **Finalize round** — Locks scores, triggers next round generation

### Top 8 Cut (16-40 teams only)

After all Swiss rounds are complete, the top 8 teams advance to a Top 8 Cut round.

**Team selection:** All teams are ranked using the full tiebreaker hierarchy (see [Tiebreakers](#tiebreakers--team-mode)). The top 8 advance.

**Seeding into 2 groups (interleaved):**

| Group | Team Seeds |
|-------|-----------|
| Group 1 | 1st, 3rd, 5th, 7th |
| Group 2 | 2nd, 4th, 6th, 8th |

**Table assignment (skill-matched):**

Within each group, players are ranked by individual score within their team (strongest = Rank 1). Tables are formed by matching players of the same rank:

| Table | Players |
|-------|---------|
| Table 1 | Rank 1 player from each of the 4 teams in the group |
| Table 2 | Rank 2 player from each team |
| Table 3 | Rank 3 player from each team |
| Table 4 | Rank 4 player from each team |

This produces 8 total tables (4 per group). Scoring follows the same Western/Japanese rules.

### Finals (Top 4 Teams)

After the Top 8 Cut (or directly after Swiss for 8/12 teams), the top 4 teams advance to Finals.

**For 16-40 teams:** Top 4 are selected from the 8 teams that played the Top 8 Cut, ranked by a 5-level tiebreaker:
1. Top 8 Cut round score
2. Swiss round score
3. Best individual player score
4. Average player score
5. Early wins score

**For 8/12 teams:** Top 4 selected directly from Swiss standings using the standard tiebreaker.

**Table construction:** Same strength-based seating as Top 8 Cut — 4 tables, each with the corresponding rank player from each finalist team. First seat at each table goes to the highest-ranked team.

### Tiebreakers — Team Mode

**Swiss standings** use this hierarchy (all compared descending):

| Priority | Tiebreaker | Description |
|----------|-----------|-------------|
| 1 | Total team score | Sum of all 4 players' scores |
| 2 | Best player score | Highest individual score on the team |
| 3 | Average player score | Mean of all 4 players' scores (multiplied by 1000 for integer comparison) |
| 4 | Early wins score | Exponentially weighted round performance |

**Early wins formula:**

Each Swiss round has a weight of `10^(swiss_rounds - round_number)`. The team's points earned in each round are multiplied by that round's weight and summed.

*Example (4 Swiss rounds):*
- Round 1 weight: 1000
- Round 2 weight: 100
- Round 3 weight: 10
- Round 4 weight: 1

A team scoring 15, 10, 20, 5 across 4 rounds gets: `15x1000 + 10x100 + 20x10 + 5x1 = 16,205`

This heavily favors teams that performed well in early rounds. Only Swiss rounds are counted (not Top 8 Cut or Finals).

**Finals champion** uses a 5-level hierarchy:

| Priority | Tiebreaker | Description |
|----------|-----------|-------------|
| 1 | Finals round points | Points scored in the Finals round only |
| 2 | Tiebreaker points | Swiss points + Top 8 Cut points (or just Swiss for 8/12 teams) |
| 3 | Best player score | Highest individual player score on the team |
| 4 | Average player score | Mean player score on the team |
| 5 | Early wins score | Same exponential formula as Swiss tiebreaker |

### MVP

The MVP is the individual player with the highest cumulative score across the entire tournament (all rounds: Swiss + Top 8 Cut + Finals), selected from players on the **Top 4 finalist teams** only.

In Japanese mode, this reflects the full accumulated Japanese score starting from 1000.

---

## 4. Tournament Flow — Individual Mode

### Swiss Rounds

Each Swiss round creates pods of 4 (or 3) individual players. The system attempts to avoid repeat opponents but this is a **soft constraint** (optimization, not a guarantee).

#### Pairing Algorithm

1. **Sort** all active players by score (highest first, random tiebreaking for equal scores)
2. **Handle remainders** (when player count is not divisible by 4):
   - Remainder 3: The bottom 3 players form a 3-player pod
   - Remainder 1 or 2: The bottom 1 or 2 players receive byes
3. **Form pods** of 4 sequentially from the sorted list
4. **Optimize** via up to 150 iterations of greedy adjacent-pod swaps to reduce repeat opponents

#### Bye System

When the player count is not divisible by 4, some players receive byes (automatic wins) each round.

**Bye selection:**
- Candidates are drawn from the bottom of the standings
- Players who have **not** had a previous bye are preferred
- Among those, the lowest-scoring player is chosen

**Bye scoring:**

| Scoring Mode | Bye Award |
|-------------|-----------|
| Western | +5 points (automatic win) |
| Japanese | No point change (player keeps current score) |

### Player Drop

Individual mode allows the Tournament Operator (TO) to remove players mid-tournament.

**When:** After all tables have submitted scores for a round, but before the round is finalized.

**What happens:**
- The player's score is **frozen** at its current value
- The player is removed from all future pairings
- The pairing engine rebuilds for the next round with the reduced player count
- Dropped players still appear in final standings (marked as dropped)

**Undrop:** A previously dropped player can be re-added (PIN-protected). Their frozen score is restored and they rejoin future pairings.

### Top Cut (17+ players)

After Swiss rounds, if there are more than 16 players, the top 10 advance to a Top Cut round.

| Seed | What happens |
|------|-------------|
| 1st-2nd | Receive byes (Western: +5pts, Japanese: no change) |
| 3rd-6th | Play at Table 1 |
| 7th-10th | Play at Table 2 |

After the Top Cut round, the top 4 players advance to Finals.

### Finals (Top 4 Players)

The top 4 players play at a single Finals table. One round determines the champion.

- **Direct from Swiss** (16 or fewer players): Top 4 from Swiss standings
- **After Top Cut** (17+ players): Top 4 from Top Cut results

### Tiebreakers — Individual Mode

**Standings hierarchy:**

| Priority | Tiebreaker | Description |
|----------|-----------|-------------|
| 1 | Total player score | Cumulative score across all rounds |
| 2 | Early wins score | Same exponential round weighting as team mode, applied per player |

This hierarchy is used for Swiss standings, Top Cut advancement, Finals advancement, and champion determination.

---

## 5. Quick Reference — All 4 Flows

### Team + Western

```
Setup: Select Team mode, Western scoring
  |
  v
Swiss Rounds (3-5 rounds)
  Each round: 4-player pods, 1 player per team per pod
  Scoring: Win=5, Draw=1, Loss=0
  Team score = sum of 4 players
  |
  v
[8/12 teams]                    [16-40 teams]
  |                                |
  v                                v
Finals                          Top 8 Cut
  Top 4 teams                     Top 8 teams, 2 groups
  4 tables (strength-matched)     8 tables (strength-matched)
  |                                |
  v                                v
Champion                        Finals
                                  Top 4 teams, 4 tables
                                  |
                                  v
                                Champion
```

### Team + Japanese

Same flow as Team + Western, with these scoring differences:
- Players start at 1000 points instead of 0
- Each round: 7% pool contribution, winner takes pool, losers lose contribution
- Draws destroy the pool (net loss for all)
- Team score = sum of players' Japanese point totals
- Scores are typically in the 600-2000+ range after Swiss rounds

### Individual + Western

```
Setup: Select Individual mode, Western scoring
  |
  v
Swiss Rounds (3-5 rounds)
  Each round: pods of 4 (or 3), score-sorted
  Byes for remainder 1-2 players (+5 pts each)
  Scoring: Win=5, Draw=1, Loss=0
  Optional: Drop players between rounds
  |
  v
[16 or fewer players]           [17+ players]
  |                                |
  v                                v
Finals                          Top Cut (Top 10)
  Top 4 players                   Seeds 1-2: byes (+5 pts)
  1 table                         Seeds 3-10: 2 tables of 4
  |                                |
  v                                v
Champion                        Finals
                                  Top 4 players, 1 table
                                  |
                                  v
                                Champion
```

### Individual + Japanese

Same flow as Individual + Western, with these scoring differences:
- Players start at 1000 points instead of 0
- Swiss round byes: no point change (instead of +5)
- Top Cut byes: no point change (instead of +5)
- Pool-based scoring at each table
- Scores are typically in the 600-1800+ range after Swiss rounds
