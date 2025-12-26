# E2E Testing for MTG Tournament Dashboard

This directory contains end-to-end (E2E) tests for the MTG Tournament Dashboard.

## Prerequisites

1. **Python 3.8+** with the following packages:
   - `playwright`
   - `openpyxl`

2. **Install Playwright browsers**:
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **Dashboard server** must be running at `http://localhost:5001`

## Test Scripts

### 1. `generate_16_teams.py`
Generates test participant data (16 teams × 4 players = 64 players).

```bash
# Generate with descriptive team names
python generate_16_teams.py

# Generate with simple names (Team A, Team B, etc.)
python generate_16_teams.py --simple
```

This creates `participants/participant_team.xlsx` which the dashboard reads on startup.

---

### 2. `simulate_tournament_flow.py`
Basic tournament simulation script that:
- Loads participants
- Sets up tournament
- Plays through all rounds (Swiss → Top 8 Cut → Finals)
- Validates Swiss pairing rules
- Detects champion declaration

```bash
python simulate_tournament_flow.py
```

---

### 3. `simulate_full_tournament.py` ⭐ (Recommended)
Comprehensive tournament simulation with detailed tracking:
- **Player Tracking**: Every player's journey through rounds
- **Team Tracking**: Team scores at each phase
- **Pairing Validation**: Swiss pairing rules enforcement
- **Phase Detection**: Automatic detection of Swiss/Top8/Finals
- **Detailed Reporting**: JSON report with all results

```bash
python simulate_full_tournament.py
```

**Output**: Creates `tournament_test_report.json` with:
- Round-by-round results
- Player journeys (all scores, tables, opponents)
- Swiss/Top8/Finals standings
- Champion and MVP information
- Validation warnings

---

## Tournament Structure (16 Teams)

```
Round 1-4: Swiss Rounds
    └── 16 teams compete in 4 rounds
    └── 4 pods per round (4 players each)
    └── Swiss pairing rules enforced:
        • No repeat matchups
        • Teammates avoid same pod

Round 5: Top 8 Cut
    └── Top 8 teams advance
    └── 2 pods (4 teams each)
    └── Repeat matchup rules relaxed

Round 6: Finals
    └── Top 4 teams compete
    └── 1 pod (4 teams)
    └── Champion determined by:
        1. Finals points (primary)
        2. Top 8 + Swiss points (tiebreaker)
```

---

## Running Tests

### Quick Test
```bash
# 1. Start the dashboard server
cd mtg-dashboard-v1
python tournament_dashboard.py

# 2. In another terminal, run the test
cd tests/e2e
python generate_16_teams.py --simple
python simulate_tournament_flow.py
```

### Full Test with Tracking
```bash
# 1. Start the dashboard server
cd mtg-dashboard-v1
python tournament_dashboard.py

# 2. In another terminal
cd tests/e2e
python generate_16_teams.py
python simulate_full_tournament.py
```

---

## Test Files

| File | Description |
|------|-------------|
| `generate_16_teams.py` | Creates test participant data |
| `simulate_tournament_flow.py` | Basic E2E simulation |
| `simulate_full_tournament.py` | Comprehensive simulation with tracking |
| `teams_16.csv` | Sample CSV data (legacy) |
| `tournament_test_report.json` | Generated test report (from full simulation) |

---

## Validation Rules

The tests validate:

1. **No Repeat Matchups** (Swiss): Players shouldn't be in the same pod twice
2. **Teammate Avoidance** (Swiss): Players from same team shouldn't be in same pod
3. **Phase Transitions**: Proper progression Swiss → Top 8 → Finals
4. **Champion Declaration**: Tournament completes with winner announcement

---

## Troubleshooting

### "Tables not found"
- Ensure the dashboard server is running
- Check that participants were loaded successfully
- Verify tournament was set up

### "Submit button not visible"
- Check if all tables have been scored
- Verify the round hasn't already been submitted

### "Validation warnings"
- Some warnings may be acceptable:
  - Repeat matchups in Top 8/Finals
  - Teammate pairings in later rounds (unavoidable with fewer teams)

---

## Contributing

When adding new tests:
1. Follow the existing patterns for page interaction
2. Add validation for new features
3. Update this README with usage instructions
