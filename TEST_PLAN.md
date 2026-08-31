# Test Plan

## Quick Smoke Test (5 minutes before a tournament)

```bash
source venv/bin/activate
pytest tests/unit/ -v                    # 178 tests
python tournament_dashboard.py &         # Start server
python tests/e2e/test_concurrent.py      # 3 concurrent tests
```

Then in browser:
1. Open `http://127.0.0.1:5001` — no console errors
2. Click "Load Participants" → Event Mode modal appears → select Team → Scoring Mode modal → select Western
3. Participants load → Click "Setup Tournament" → Round 1 generates
4. Submit all tables for Round 1 → Finalize → Round 2 generates
5. Open `/projector` — tables display correctly

---

## Full Test Suite

### Phase 1: Automated Tests

```bash
# Unit tests (178 tests)
pytest tests/unit/ -v

# E2E tests (server must be running)
python tests/e2e/simulate_full_tournament.py --teams 8
python tests/e2e/simulate_full_tournament.py --teams 16

# Concurrent access tests (server must be running)
python tests/e2e/test_concurrent.py
```

### Phase 2: Manual Verification — Team Mode

| Test | How | Expected |
|------|-----|----------|
| Event mode selection | Click "Load Participants" | Event Mode modal appears with Team/Individual options |
| Scoring mode selection | After event mode confirmed | Scoring Mode modal appears with Western/Japanese |
| Score validation | Submit 4 wins at one table | Rejected: "Only 1 winner allowed" |
| Score validation | Submit 1 win + 1 draw + 2 losses | Rejected: "win means all others must be losses" |
| Partial players | Submit with 2 of 4 player scores | Rejected: "Expected 4 player results" |
| Incomplete finalization | Finalize with 1/8 tables submitted | Rejected: "only 1/8 tables submitted" |
| Confirmation modal | Click "Submit Round Results" | Confirmation dialog appears before proceeding |
| Score revert | POST `/revert_table_submission` | Scores subtracted, table unlocked |
| CSV export | GET `/export/standings` | Downloads CSV with team rankings |
| PIN auth | Start with `TOURNAMENT_PIN=1234`, submit without PIN | 403 Forbidden |
| Backup restore | Save backup, restart server | Auto-restores with correct event/scoring mode |
| Session recovery | Restart server while dashboard open | "Server restarted" prompt appears within 5s |

### Phase 3: Manual Verification — Individual Mode

| Test | How | Expected |
|------|-----|----------|
| Event mode: Individual | Select "Individual Event" in setup wizard | Event mode set, header shows "Individual" badge |
| Load 20 players | Load Excel with 20+ entries | 20 players loaded, structure shows Top Cut |
| Bye system (18 players) | Load 18 players, setup tournament | Round 1: 4 tables + 2 bye players shown |
| 3-player pod (19 players) | Load 19 players, setup tournament | Round 1: 4 tables of 4 + 1 table of 3 |
| 3-player scoring | Submit (5,0,0) at 3-player table | Accepted |
| 3-player scoring | Submit (1,1,0) at 3-player table | Accepted |
| 3-player scoring | Submit (1,1,1) at 3-player table | Accepted |
| 3-player scoring | Submit (5,1,0) at 3-player table | Rejected: win + draw invalid |
| Player drop | After all tables submitted, click "Drop Player" | Modal shows active players |
| Drop validation | Drop player before all tables submitted | Rejected: "All tables must be submitted" |
| Drop validation | Drop in team mode | Rejected: "only available for individual events" |
| Drop effect | Drop player, finalize round | Next round generates without dropped player |
| Drop standings | Check standings after drop | Dropped player shown greyed out with frozen score |
| Individual finals (≤16) | Complete 4 Swiss rounds with 16 players | Finals with top 4 at 1 table |
| Individual top cut (>16) | Complete 4 Swiss rounds with 20 players | Top Cut: top 2 byes + 8 play, then Finals |
| No team names | Check table display in individual mode | No "Team Name" shown for players |
| Round selector | Check dropdown labels | Shows "Top Cut (Top 10)" not "Top 8 Cut" |

### Phase 4: Scoring Mode Tests

| Test | How | Expected |
|------|-----|----------|
| Japanese + Team | 8-team Japanese mode full tournament | Players start 1000pts, pool mechanics work |
| Japanese + Individual | 20-player Japanese individual tournament | Same pool mechanics, byes = no point change |
| Western + Individual | 20-player Western individual tournament | Standard 5/1/0, byes = +5pts |

### Phase 5: Regression Checklist

- [ ] 8-team Western: Load → Setup → 4 Swiss → Finals → Champion
- [ ] 16-team Western: Load → Setup → 4 Swiss → Top 8 Cut → Finals → Champion
- [ ] 8-team Japanese: Full tournament with correct point calculations
- [ ] 20-player Individual Western: Full tournament with drops, byes, top cut
- [ ] 16-player Individual: Direct to finals after Swiss (no top cut)
- [ ] Backup save/restore cycle mid-tournament (both modes)
- [ ] Score editing mid-round
- [ ] Projector displays correctly for both modes
- [ ] Timer start/stop/reset (no display jumps)
- [ ] Page refresh mid-tournament restores event/scoring mode correctly
