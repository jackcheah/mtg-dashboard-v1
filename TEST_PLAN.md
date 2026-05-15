# Test Plan

## Quick Smoke Test (5 minutes before a tournament)

```bash
source venv/bin/activate
pytest tests/unit/ -v                    # 21 tests, <2s
python tournament_dashboard.py &         # Start server
python tests/e2e/test_concurrent.py      # 3 concurrent tests
```

Then in browser:
1. Open `http://127.0.0.1:5001` — no console errors
2. Load sample data (8 teams) -> Setup tournament
3. Submit all tables for Round 1 -> Finalize (confirmation modal appears) -> Round 2 generates
4. Open `/projector` — tables display correctly

---

## Full Test Suite

### Phase 1: Automated Tests

```bash
# Unit tests (21 tests)
pytest tests/unit/ -v

# E2E tests (server must be running)
python tests/e2e/simulate_full_tournament.py --teams 8
python tests/e2e/simulate_full_tournament.py --teams 16

# Concurrent access tests (server must be running)
python tests/e2e/test_concurrent.py
```

### Phase 2: Manual Verification

| Test | How | Expected |
|------|-----|----------|
| Score validation | Submit 4 wins at one table | Rejected: "Only 1 winner allowed" |
| Score validation | Submit 1 win + 1 draw + 2 losses | Rejected: "win means all others must be losses" |
| Partial players | Submit with 2 of 4 player scores | Rejected: "Expected 4 player results" |
| Incomplete finalization | Finalize with 1/8 tables submitted | Rejected: "only 1/8 tables submitted" |
| Confirmation modal | Click "Submit Round Results" | Confirmation dialog appears before proceeding |
| Score revert | POST `/revert_table_submission` | Scores subtracted, table unlocked for re-submission |
| CSV export | GET `/export/standings` | Downloads CSV with team rankings |
| PIN auth | Start with `TOURNAMENT_PIN=1234`, submit without PIN | 403 Forbidden |
| Backup restore | Save backup, corrupt `.bak`, restart | Loads from `.bak.1` with fallback message |
| Session recovery | Restart server while dashboard open | "Server restarted" prompt appears within 5s |

### Phase 3: Regression Checklist

- [ ] 8-team: Load -> Setup -> 4 Swiss -> Finals -> Champion
- [ ] 16-team: Load -> Setup -> 4 Swiss -> Top 8 Cut -> Finals -> Champion
- [ ] Backup save/restore cycle mid-tournament
- [ ] Score editing mid-round
- [ ] Projector displays tables, standings, and winners
- [ ] Timer start/stop/reset (no display jumps)
- [ ] Reset tournament and start new one
