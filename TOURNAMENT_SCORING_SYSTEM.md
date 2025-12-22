# Tournament Scoring System Documentation

## Overview

This document describes the complete scoring and advancement logic for the MTG Tournament Dashboard system. The system tracks scores separately for each tournament stage to ensure fair competition where current performance matters most.

---

## Core Principles

1. **Stage-Specific Scoring**: Each tournament stage (Swiss, Top 8 Cut, Finals) maintains separate score tracking
2. **Performance-Based Advancement**: Teams advance based on their performance in the current stage
3. **Historical Tiebreakers**: Previous round scores are used ONLY to break ties
4. **No Score Carrying**: Teams cannot "coast" on early performance - must compete in each stage

---

## Score Tracking Variables

### Backend Data Structures

```python
# Global accumulated scores (all rounds combined)
self.scores = {
    'Team A': 120,  # Swiss + Top8Cut + Finals combined
    'Team B': 115,
    ...
}

# Swiss round scores (Rounds 1-4 for 16-team, saved before Top 8 Cut)
self.swiss_round_scores = {
    'Team A': 85,   # Rounds 1-4 only
    'Team B': 80,
    ...
}

# Top 8 Cut scores (Round 5 only, 16-team tournaments only)
self.top8_cut_scores = {
    'Team A': 20,   # Round 5 only
    'Team B': 25,
    ...
}

# Finals scores (Round 6 for 16-team, Round 5 for 8/12-team)
self.final_round_scores = {
    'Team A': 15,   # Finals round only
    'Team B': 10,
    ...
}
```

---

## Tournament Flows

### 16-Team Tournament (with Top 8 Cut)

```
Swiss Rounds (1-4) → Top 8 Cut (5) → Finals (6) → Champion
     16 teams           8 teams         4 teams     1 winner
```

#### **Round 1-4: Swiss Rounds**

**Score Tracking:**
- `self.scores` accumulates all team scores
- `self.player_scores` accumulates all player scores

**After Round 4:**
- `self.swiss_round_scores = dict(self.scores)` (snapshot saved)
- Top 8 teams identified by `self.swiss_round_scores`

**Code Location:** `tournament_dashboard.py:1328-1331`

```python
if not hasattr(self, 'swiss_round_scores') or not self.swiss_round_scores:
    print(f"[SAVE] Preserving Swiss round scores before Top 8 Cut")
    self.swiss_round_scores = dict(self.scores)
```

---

#### **Round 5: Top 8 Cut**

**Initialization:**
- 8 teams compete in 8 tables (2 pods of 4 teams each)
- Teams grouped by alternating ranking: (1,3,5,7) vs (2,4,6,8)

**Score Tracking:**
- `self.top8_cut_scores` initialized to 0 for all Top 8 teams
- As tables submit: `self.top8_cut_scores[team] += points` (Round 5 only)
- `self.scores` continues to accumulate (Swiss + Top 8 Cut)

**Code Location:** `tournament_dashboard.py:1124-1157`

```python
def update_top8_cut_scores(self, round_num, player_results):
    top8_cut_round = self.swiss_rounds_count + 1
    if round_num != top8_cut_round:
        return

    for result in player_results:
        # Find team and add points to top8_cut_scores
        self.top8_cut_scores[team_name] += points
```

**Advancement to Finals:**
- Sort teams by: `(top8_cut_scores, swiss_round_scores)` (tuple sorting)
- Top 4 teams advance

**Code Location:** `tournament_dashboard.py:1176-1194`

```python
def get_top8_ranking(team_score_tuple):
    team_name = team_score_tuple[0]
    top8_score = self.top8_cut_scores.get(team_name, 0)
    swiss_score = self.swiss_round_scores.get(team_name, 0)
    return (top8_score, swiss_score)

sorted_teams = sorted(self.scores.items(), key=get_top8_ranking, reverse=True)
top_4_teams = [team for team, score in sorted_teams[:4]]
```

**Console Output:**
```
[RANK] Finals advancement based on Top 8 Cut scores (Swiss as tiebreaker):
  1. Team A: Top8=25 pts (primary), Swiss=85 pts (tiebreaker) [→ FINALS]
  2. Team B: Top8=20 pts (primary), Swiss=80 pts (tiebreaker) [→ FINALS]
  3. Team C: Top8=20 pts (primary), Swiss=75 pts (tiebreaker) [→ FINALS]
  4. Team D: Top8=18 pts (primary), Swiss=90 pts (tiebreaker) [→ FINALS]
```

---

#### **Round 6: Finals**

**Initialization:**
- 4 teams compete in 4 tables (1 pod)

**Score Tracking:**
- `self.final_round_scores` initialized to 0 for all 4 finalists
- As tables submit: `self.final_round_scores[team] += points` (Round 6 only)

**Code Location:** `tournament_dashboard.py:1083-1122`

**Champion Determination:**
- Sort teams by: `(final_round_scores, swiss_round_scores + top8_cut_scores)`
- Winner = Rank 1

**Code Location:** `tournament_dashboard.py:1010-1037`

```python
# Calculate tiebreaker
tiebreaker_points = swiss_round_points + top8_cut_points

# Sort by Finals (primary), then tiebreaker
final_standings.sort(
    key=lambda x: (x['final_points'], x['tiebreaker_points']),
    reverse=True
)
```

**Console Output:**
```
[TROPHY] CALCULATING CHAMPION
  Team A: Final=15 pts, Top8Cut=25 pts, Swiss=85 pts, Tiebreaker=110 pts
  Team B: Final=15 pts, Top8Cut=20 pts, Swiss=80 pts, Tiebreaker=100 pts
  Team C: Final=12 pts, Top8Cut=20 pts, Swiss=75 pts, Tiebreaker=95 pts
  Team D: Final=10 pts, Top8Cut=18 pts, Swiss=90 pts, Tiebreaker=108 pts

[OK] FINAL STANDINGS:
  [1st] Team A: Final=15 pts (PRIMARY), Tiebreaker=110 pts (Swiss=85+Top8=25)
  [2nd] Team B: Final=15 pts (PRIMARY), Tiebreaker=100 pts (Swiss=80+Top8=20)

[WARNING] TIE on final points! Using Swiss+Top8Cut as tiebreaker:
   Winner: Team A (Tiebreaker: 110 = Swiss 85 + Top8 25)
   Runner-up: Team B (Tiebreaker: 100 = Swiss 80 + Top8 20)
```

---

### 8-Team & 12-Team Tournaments (No Top 8 Cut)

```
Swiss Rounds (1-4) → Finals (5) → Champion
    8/12 teams         4 teams     1 winner
```

#### **Round 1-4: Swiss Rounds**

**Score Tracking:**
- Same as 16-team tournament
- `self.scores` accumulates all team scores

**After Round 4:**
- Top 4 teams advance directly to Finals
- No Top 8 Cut round

---

#### **Round 5: Finals**

**Initialization:**
- `self.swiss_round_scores = dict(self.scores)` (snapshot saved)
- 4 teams compete in 4 tables (1 pod)

**Score Tracking:**
- `self.final_round_scores` initialized to 0 for all 4 finalists
- As tables submit: `self.final_round_scores[team] += points` (Round 5 only)

**Champion Determination:**
- Sort teams by: `(final_round_scores, swiss_round_scores)`
- Winner = Rank 1

**Code Location:** `tournament_dashboard.py:1027-1037`

```python
# For 8/12-team: tiebreaker = Swiss only (no Top 8 Cut)
tiebreaker_points = swiss_round_points

final_standings.sort(
    key=lambda x: (x['final_points'], x['tiebreaker_points']),
    reverse=True
)
```

**Console Output:**
```
[TROPHY] CALCULATING CHAMPION
  Team A: Final=15 pts, Swiss=85 pts, Total=100 pts
  Team B: Final=15 pts, Swiss=80 pts, Total=95 pts

[OK] FINAL STANDINGS:
  [1st] Team A: Final=15 pts (PRIMARY), Swiss=85 pts (tiebreaker)
  [2nd] Team B: Final=15 pts (PRIMARY), Swiss=80 pts (tiebreaker)
```

---

## UI Display Logic

### Bracket Visualization

**Endpoint:** `/bracket_standings/<round_num>`

**Code Location:** `tournament_dashboard.py:3375-3448`

#### **Top 8 Cut Display:**

```python
# Show ONLY Top 8 Cut scores (not accumulated)
if round_num == swiss_rounds + 1:
    # Get top 8 teams from Swiss scores
    top8_teams = sorted(swiss_scores.items(), ...)[:8]

    # Show their Top 8 Cut scores (or 0 if not yet scored)
    current_round_scores = {}
    for team_name, _ in top8_teams:
        current_round_scores[team_name] = self.top8_cut_scores.get(team_name, 0)
```

**Result:** Bracket shows teams with scores like 0, 5, 10, 15, 20 pts (current round only)

#### **Finals Display:**

```python
# Show ONLY Finals scores (not accumulated)
if round_num == max_rounds:
    # Get top 4 teams from previous round
    top4_teams = [determined by Top 8 Cut or Swiss]

    # Show their Finals scores (or 0 if not yet scored)
    current_round_scores = {}
    for team_name, _ in top4_teams:
        current_round_scores[team_name] = self.final_round_scores.get(team_name, 0)
```

**Result:** Bracket shows teams with scores like 0, 5, 10, 15, 20 pts (current round only)

### Pod Groupings

**Endpoint:** `/bracket_groups/<round_num>`

**Code Location:** `tournament_dashboard.py:3306-3373`

Determines actual pod assignments by reading table data:
- Tables 1-4 → Pod 1
- Tables 5-8 → Pod 2

**Result:** Bracket displays teams in their actual competitive groups, not theoretical matchups

---

## API Endpoints

### Core Endpoints

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/standings` | Current team standings | Accumulated total scores |
| `/bracket_standings/<round_num>` | Bracket display data | Current round scores only |
| `/bracket_groups/<round_num>` | Pod assignments | Actual table groupings |
| `/get_scores` | All score data | Swiss, Top8Cut, Finals, Total |

### Example API Responses

**`/bracket_standings/5` (Top 8 Cut):**
```json
{
  "success": true,
  "standings": [
    {
      "rank": 1,
      "team": "Team A",
      "current_round_points": 20,
      "total_points": 20,
      "swiss_points": 85,
      "score_type": "top8cut"
    }
  ],
  "score_type": "top8cut"
}
```

**`/bracket_groups/5` (Top 8 Cut):**
```json
{
  "success": true,
  "pod1": ["Team A", "Team C", "Team E", "Team G"],
  "pod2": ["Team B", "Team D", "Team F", "Team H"],
  "round_type": "top8cut"
}
```

---

## Score Update Flow

### Table Submission Process

```
User submits table → /submit_table_results → Backend processing
```

**Code Location:** `tournament_dashboard.py:2233-2242`

```python
# Update player and team scores
for result in player_results:
    self.player_scores[player_id] += points

# Handle Top 8 Cut scoring (16-team only)
if hasattr(self, 'has_semifinals') and self.has_semifinals:
    self.update_top8_cut_scores(round_num, player_results)

# Handle Finals scoring
if round_num == self.max_rounds:
    self.update_final_round_scores(round_num, player_results)

# Recalculate team totals
self.calculate_team_scores()
```

### Real-Time Bracket Updates

**Frontend Code Location:** `dashboard_ultra_modern.html:5189-5194`

```javascript
// After successful table submission
await updateBracketVisualization(roundNum);  // Refresh bracket with new scores
```

**Result:** Bracket updates immediately showing new scores without page refresh

---

## Testing Scenarios

### Scenario 1: Tied Finals, Different Previous Performance

**Setup (16-team):**
- Team A: Swiss=90, Top8Cut=15, Finals=20
- Team B: Swiss=70, Top8Cut=25, Finals=20

**Result:**
- Both tied at 20 Finals pts
- Tiebreaker: Team B wins (70+25=95 > 90+15=105) ❌ **WAIT - Team A should win!**

Let me recalculate:
- Team A tiebreaker: 90 + 15 = 105
- Team B tiebreaker: 70 + 25 = 95
- **Team A wins** (105 > 95) ✓

### Scenario 2: Lower Swiss, Better Top 8 Cut

**Setup (16-team Finals Advancement):**
- Team C: Swiss=95, Top8Cut=10
- Team D: Swiss=60, Top8Cut=25

**Result:**
- Team D advances to Finals (25 > 10 in Top 8 Cut)
- Swiss only used if tied on Top 8 Cut

### Scenario 3: 8-Team Tournament Tiebreaker

**Setup (8-team Finals):**
- Team E: Swiss=85, Finals=18
- Team F: Swiss=90, Finals=18

**Result:**
- Both tied at 18 Finals pts
- Tiebreaker: Team F wins (90 > 85 Swiss)

---

## Summary

| Tournament | Stage | Advancement Logic | Champion Logic |
|------------|-------|-------------------|----------------|
| **16-team** | Swiss → Top 8 | By Swiss total | N/A |
| **16-team** | Top 8 → Finals | By Top8Cut (+ Swiss tie) | N/A |
| **16-team** | Finals → Winner | N/A | By Finals (+ Swiss+Top8 tie) |
| **8/12-team** | Swiss → Finals | By Swiss total | N/A |
| **8/12-team** | Finals → Winner | N/A | By Finals (+ Swiss tie) |

**Key Insight:** Each playoff stage resets the competition - teams must perform in THAT stage to advance/win, with previous performance only breaking ties.
