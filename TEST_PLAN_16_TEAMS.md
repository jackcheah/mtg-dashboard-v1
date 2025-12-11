# Comprehensive Test Plan for 16-Team MTG Tournament Dashboard

**Version:** 1.0
**Date:** December 11, 2025
**Project:** MTG Tournament Dashboard v1

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Test Scope & Objectives](#2-test-scope--objectives)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [Backend Unit Tests](#4-backend-unit-tests)
5. [Frontend Unit Tests](#5-frontend-unit-tests)
6. [API Integration Tests](#6-api-integration-tests)
7. [End-to-End Integration Tests](#7-end-to-end-integration-tests)
8. [16-Team Tournament Specific Tests](#8-16-team-tournament-specific-tests)
9. [Performance & Stress Tests](#9-performance--stress-tests)
10. [Edge Case & Error Handling Tests](#10-edge-case--error-handling-tests)
11. [Test Data Requirements](#11-test-data-requirements)
12. [Test Execution Checklist](#12-test-execution-checklist)

---

## 1. Executive Summary

This test plan ensures the MTG Tournament Dashboard can successfully host a **16-team (64-player) cEDH tournament** without errors. The plan covers:

- **Backend**: TournamentManager, UnifiedSwissPairing, API endpoints
- **Frontend**: Dashboard UI, JavaScript functions, user interactions
- **Integration**: Full tournament flow from setup to champion determination

### 16-Team Tournament Structure
| Round | Type | Teams | Pods | Players |
|-------|------|-------|------|---------|
| 1-4 | Swiss | 16 | 16 | 64 |
| 5 | Top 8 Cut | 8 | 8 | 32 |
| 6 | Finals | 4 | 4 | 16 |

---

## 2. Test Scope & Objectives

### 2.1 In Scope
- Tournament setup and initialization
- Swiss pairing algorithm (4 rounds)
- Top 8 Cut generation and execution
- Finals generation and champion determination
- Score submission and calculation
- State persistence (backup/restore)
- UI interactions and display
- API endpoint functionality

### 2.2 Out of Scope
- Load testing with multiple concurrent tournaments
- Browser compatibility testing (assume modern Chrome/Firefox)
- Mobile responsiveness testing

### 2.3 Success Criteria
- [ ] All 16 teams (64 players) load correctly
- [ ] 4 Swiss rounds generate with zero constraint violations
- [ ] No teammate pairings in any pod
- [ ] No repeat team matchups across Swiss rounds
- [ ] Top 8 Cut generates correctly (8 pods)
- [ ] Finals generates correctly (4 pods)
- [ ] Champion determination works
- [ ] Backup/restore preserves full state
- [ ] UI displays all data correctly

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS)                        │
│  dashboard_ultra_modern.html (3931 lines)                       │
│  - 25+ JavaScript functions                                      │
│  - Real-time score entry (W/D/L buttons)                        │
│  - Round navigation and display                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (JSON)
┌─────────────────────────┴───────────────────────────────────────┐
│                     Backend (Flask/Python)                       │
│  tournament_dashboard.py (2831 lines)                           │
│  - TournamentManager class                                       │
│  - 30+ API endpoints                                             │
│  - State management                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                   Swiss Pairing Engine                           │
│  unified_swiss_pairing.py (1853 lines)                          │
│  - HybridConstraintSolver                                        │
│  - Zero-repeat team matchup guarantee                            │
│  - Intelligent seating                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Backend Unit Tests

### 4.1 TournamentManager Class Tests

#### 4.1.1 Initialization Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-INIT-001 | Create TournamentManager instance | Empty state, current_round=1 |
| BE-INIT-002 | create_sample_data(16) generates 16 teams | 16 teams with 4 players each |
| BE-INIT-003 | Load 16 teams from Excel file | All 64 players loaded correctly |
| BE-INIT-004 | Validate team count equals 16 | has_semifinals=True, max_rounds=6 |

#### 4.1.2 Tournament Setup Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-SETUP-001 | setup_tournament(swiss_rounds=4) with 16 teams | swiss_rounds_count=4, Round 1 generated |
| BE-SETUP-002 | Verify tournament_teams list has 16 entries | All team names present |
| BE-SETUP-003 | Verify scores initialized to 0 | All 16 teams start at 0 points |
| BE-SETUP-004 | Verify player_scores initialized | All 64 players start at 0 points |
| BE-SETUP-005 | Verify Round 1 has 16 tables | Each table has 4 players |

#### 4.1.3 Swiss Round Generation Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-SWISS-001 | Generate Round 1 | 16 pods, 4 players each, no teammate pairs |
| BE-SWISS-002 | Generate Round 2 after submitting R1 results | 16 pods, no repeat matchups |
| BE-SWISS-003 | Generate Round 3 after submitting R2 results | 16 pods, no repeat matchups |
| BE-SWISS-004 | Generate Round 4 after submitting R3 results | 16 pods, no repeat matchups |
| BE-SWISS-005 | Verify zero teammate violations across all Swiss | Pass constraint check |
| BE-SWISS-006 | Verify zero repeat team matchups | All team combinations unique |

#### 4.1.4 Top 8 Cut Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-TOP8-001 | generate_semifinals_round() after Round 4 | 8 pods with top 8 teams |
| BE-TOP8-002 | Verify Top 8 seeding order | Teams ranked by Swiss points |
| BE-TOP8-003 | Verify group distribution | Group 1: 1,3,5,7 / Group 2: 2,4,6,8 |
| BE-TOP8-004 | No teammates in same pod | Pass constraint check |
| BE-TOP8-005 | Top 8 Cut round marked as round 5 | current_round advances to 5 |

#### 4.1.5 Finals Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-FINAL-001 | generate_unified_finals() after Top 8 | 4 pods with top 4 teams |
| BE-FINAL-002 | Verify seeding by player strength | Table 1: strongest players |
| BE-FINAL-003 | No teammates in same pod | Pass constraint check |
| BE-FINAL-004 | Finals round marked as round 6 | current_round advances to 6 |

#### 4.1.6 Score Calculation Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-SCORE-001 | Win (W) awards 5 points | player_scores updated +5 |
| BE-SCORE-002 | Draw (D) awards 1 point | player_scores updated +1 |
| BE-SCORE-003 | Loss (L) awards 0 points | player_scores unchanged |
| BE-SCORE-004 | Team score = sum of player scores | Correct aggregation |
| BE-SCORE-005 | get_tournament_winner() returns correct team | Highest final round points |

#### 4.1.7 State Management Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| BE-STATE-001 | save_state() creates JSON backup | File exists, valid JSON |
| BE-STATE-002 | load_state() restores full tournament | All state variables restored |
| BE-STATE-003 | Pairing engine rehydration after restore | Can generate next round |
| BE-STATE-004 | Backup mid-tournament and restore | Continue from exact point |

---

## 5. Frontend Unit Tests

### 5.1 UI Component Tests

#### 5.1.1 Setup Panel Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| FE-SETUP-001 | Click "Load Participants" button | Calls loadParticipants() |
| FE-SETUP-002 | Display 16 teams after load | Team grid shows all teams |
| FE-SETUP-003 | Swiss rounds selector shows 4 as default | For 16 teams |
| FE-SETUP-004 | Click "Setup Tournament" button | Calls setupTournament() |
| FE-SETUP-005 | Display Round 1 after setup | 16 tables visible |

#### 5.1.2 Round Display Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| FE-ROUND-001 | Display 16 tables for Swiss rounds | Each table shows 4 players |
| FE-ROUND-002 | Display 8 tables for Top 8 Cut | Correct pod assignments |
| FE-ROUND-003 | Display 4 tables for Finals | Correct player placement |
| FE-ROUND-004 | Round selector navigates correctly | Loads correct round data |
| FE-ROUND-005 | Progression tracker updates | Shows current phase |

#### 5.1.3 Score Entry Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| FE-SCORE-001 | Click W button for player | Score set to 5, button highlighted |
| FE-SCORE-002 | Click D button for player | Score set to 1, button highlighted |
| FE-SCORE-003 | Click L button for player | Score set to 0, button highlighted |
| FE-SCORE-004 | Change from W to L | Score updated correctly |
| FE-SCORE-005 | Submit table results | API called, table marked complete |

#### 5.1.4 Results Display Tests
| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| FE-RESULT-001 | Team standings update after round | Scores reflected |
| FE-RESULT-002 | Player scores display correctly | Individual totals shown |
| FE-RESULT-003 | Championship modal appears | Shows winner details |
| FE-RESULT-004 | Final standings display | All teams ranked |

### 5.2 JavaScript Function Tests

| Test ID | Function | Test Case | Expected Result |
|---------|----------|-----------|-----------------|
| FE-JS-001 | loadParticipants() | API success | Teams populated |
| FE-JS-002 | setupTournament() | API success | Round 1 displayed |
| FE-JS-003 | displayTables() | 16 tables data | Correct rendering |
| FE-JS-004 | setPlayerScore() | W/D/L click | Score stored |
| FE-JS-005 | submitTableResults() | All 4 scores set | API called |
| FE-JS-006 | submitRoundResults() | All 16 tables complete | Next round generated |
| FE-JS-007 | updateRoundSelector() | After each round | Options updated |
| FE-JS-008 | refreshTeamScores() | After submission | Standings updated |
| FE-JS-009 | showChampionshipModal() | Winner data | Modal displayed |
| FE-JS-010 | restoreBackup() | Valid backup file | State restored |

---

## 6. API Integration Tests

### 6.1 Data Loading Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-001 | /load_data | GET | Load 16-team Excel | 200, teams/participants data |
| API-002 | /load_data | POST | Set swiss_rounds=4 | 200, swiss_rounds_count=4 |
| API-003 | /get_teams | GET | After load | 200, 16 teams |
| API-004 | /get_player_scores | GET | After load | 200, 64 players |

### 6.2 Tournament Setup Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-005 | /setup_tournament | POST | With 16 teams | 200, Round 1 tables |
| API-006 | /get_tournament_state | GET | After setup | 200, current_round=1 |
| API-007 | /get_tables/1 | GET | Get Round 1 | 200, 16 tables |
| API-008 | /validate_integrity | GET | After setup | 200, valid=true |

### 6.3 Score Submission Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-009 | /submit_table_results | POST | Table 1 scores | 200, scores updated |
| API-010 | /submit_player_results | POST | Round 1 complete | 200, round finalized |
| API-011 | /get_scores | GET | After submission | 200, updated scores |
| API-012 | /standings | GET | After submission | 200, ranked teams |

### 6.4 Round Progression Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-013 | /get_tables/2 | GET | After R1 submit | 200, Round 2 tables |
| API-014 | /get_tables/3 | GET | After R2 submit | 200, Round 3 tables |
| API-015 | /get_tables/4 | GET | After R3 submit | 200, Round 4 tables |
| API-016 | /get_semifinals | GET | After R4 submit | 200, 8 Top 8 pods |
| API-017 | /get_finals | GET | After Top 8 | 200, 4 Finals pods |

### 6.5 Final Results Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-018 | /get_final_standings | GET | After Finals | 200, champion info |
| API-019 | /tournament_statistics | GET | End of tournament | 200, full stats |
| API-020 | /final_standings | GET | Complete tournament | 200, all rankings |

### 6.6 Backup/Restore Endpoints

| Test ID | Endpoint | Method | Test Case | Expected Response |
|---------|----------|--------|-----------|-------------------|
| API-021 | /save_backup | POST | Mid-tournament | 200, success=true |
| API-022 | /restore_backup | POST | Valid backup | 200, state restored |
| API-023 | /reset_tournament | POST | Any state | 200, reset complete |

---

## 7. End-to-End Integration Tests

### 7.1 Full Tournament Flow Test (Critical)

**Test ID:** E2E-001
**Description:** Complete 16-team tournament from start to champion

```
Step 1: Load Participants
├── Action: Click "Load Participants" OR call /load_data
├── Verify: 16 teams displayed (64 players total)
└── Verify: Swiss rounds = 4, has_semifinals = true

Step 2: Setup Tournament
├── Action: Click "Setup Tournament" OR call /setup_tournament
├── Verify: Round 1 displayed (16 tables, 64 players)
├── Verify: No teammates in same pod
└── Verify: Each pod has 4 different teams

Step 3: Swiss Round 1
├── Action: Enter W/D/L for all 64 players (16 tables × 4 players)
├── Action: Submit all table results
├── Action: Click "Submit Round Results"
├── Verify: Scores updated correctly
├── Verify: Round 2 generated
└── Verify: No repeat matchups from Round 1

Step 4: Swiss Round 2
├── [Same actions as Round 1]
├── Verify: Round 3 generated
└── Verify: No repeat matchups from Rounds 1-2

Step 5: Swiss Round 3
├── [Same actions as Round 1]
├── Verify: Round 4 generated
└── Verify: No repeat matchups from Rounds 1-3

Step 6: Swiss Round 4 (Last Swiss)
├── [Same actions as Round 1]
├── Verify: Top 8 Cut round generated (Round 5)
├── Verify: Only top 8 teams advance
├── Verify: 8 pods (8 tables)
└── Verify: Correct seeding (1,3,5,7 vs 2,4,6,8 grouping)

Step 7: Top 8 Cut (Round 5)
├── Action: Enter W/D/L for 32 players (8 tables × 4 players)
├── Action: Submit all table results
├── Action: Click "Submit Round Results"
├── Verify: Finals generated (Round 6)
├── Verify: Only top 4 teams advance
└── Verify: 4 pods (4 tables)

Step 8: Finals (Round 6)
├── Action: Enter W/D/L for 16 players (4 tables × 4 players)
├── Action: Submit all table results
├── Action: Click "Submit Round Results"
├── Verify: Championship modal appears
├── Verify: Winner correctly determined
├── Verify: MVP calculated
└── Verify: Final standings display all 16 teams

Step 9: Verify Final State
├── Verify: All rounds accessible via round selector
├── Verify: Tournament statistics correct
├── Verify: No errors in console
└── Verify: State can be backed up
```

### 7.2 Backup/Restore Flow Test

**Test ID:** E2E-002
**Description:** Test state persistence across server restart

```
Step 1: Run tournament through Round 2
Step 2: Click "Save Backup" (or auto-backup triggers)
Step 3: Simulate server restart (stop/start Flask)
Step 4: Click "Restore Backup"
Step 5: Verify: Current round = 3
Step 6: Verify: All Round 1 & 2 results intact
Step 7: Verify: Can continue to Round 3
Step 8: Complete tournament
```

### 7.3 Round Navigation Test

**Test ID:** E2E-003
**Description:** Test navigating between completed rounds

```
Step 1: Complete all 6 rounds
Step 2: Use round selector to view Round 1
Step 3: Verify: Round 1 tables display correctly
Step 4: Navigate to Round 4 (last Swiss)
Step 5: Verify: Round 4 tables and scores display
Step 6: Navigate to Round 5 (Top 8 Cut)
Step 7: Verify: 8 tables (reduced from 16)
Step 8: Navigate to Round 6 (Finals)
Step 9: Verify: 4 tables, champion highlighted
```

---

## 8. 16-Team Tournament Specific Tests

### 8.1 16-Team Configuration Validation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T16-001 | Exactly 16 teams loaded | 16 team names in tournament_teams |
| T16-002 | Exactly 64 players loaded | 64 entries in player_scores |
| T16-003 | has_semifinals = True | Top 8 Cut enabled |
| T16-004 | max_rounds = 6 | 4 Swiss + Top 8 + Finals |
| T16-005 | swiss_rounds_count = 4 | Default for 16 teams |
| T16-006 | Pods per Swiss round = 16 | 64 players / 4 = 16 pods |

### 8.2 16-Team Pairing Guarantee Tests

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T16-007 | Zero teammate violations (Round 1) | All 16 pods valid |
| T16-008 | Zero teammate violations (Round 2) | All 16 pods valid |
| T16-009 | Zero teammate violations (Round 3) | All 16 pods valid |
| T16-010 | Zero teammate violations (Round 4) | All 16 pods valid |
| T16-011 | Zero repeat team matchups (R1→R2) | All new opponents |
| T16-012 | Zero repeat team matchups (R2→R3) | All new opponents |
| T16-013 | Zero repeat team matchups (R3→R4) | All new opponents |
| T16-014 | Mathematical feasibility | 16 teams can face 12 unique opponents in 4 rounds |

### 8.3 16-Team Top 8 Cut Validation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T16-015 | Top 8 teams selected by Swiss points | Correct ranking |
| T16-016 | Bottom 8 teams eliminated | Not in Top 8 pods |
| T16-017 | Seeding preserved (1,3,5,7 group) | Higher seeds grouped |
| T16-018 | Seeding preserved (2,4,6,8 group) | Lower seeds grouped |
| T16-019 | 8 pods generated | 32 players total |
| T16-020 | No teammates in Top 8 pods | Constraint satisfied |

### 8.4 16-Team Finals Validation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T16-021 | Top 4 teams selected | Best 4 from Top 8 Cut |
| T16-022 | 4 pods generated | 16 players total |
| T16-023 | Strength-based seating | Table 1 = strongest players |
| T16-024 | No teammates in Finals pods | Constraint satisfied |
| T16-025 | Champion determination correct | Highest Finals points wins |

### 8.5 16-Team Score Calculation

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T16-026 | Swiss round team scoring | Sum of 4 player scores |
| T16-027 | Max possible Swiss score | 4 players × 4 rounds × 5 pts = 80 |
| T16-028 | Top 8 Cut scoring | Continues from Swiss |
| T16-029 | Finals scoring | Determines champion |
| T16-030 | Tiebreaker handling | Swiss points as tiebreaker |

---

## 9. Performance & Stress Tests

### 9.1 Pairing Algorithm Performance

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| PERF-001 | Generate Round 1 (16 teams) | < 1 second |
| PERF-002 | Generate Round 2-4 (16 teams) | < 2 seconds each |
| PERF-003 | Generate Top 8 Cut | < 1 second |
| PERF-004 | Generate Finals | < 0.5 seconds |
| PERF-005 | Full tournament generation | < 5 seconds total |

### 9.2 API Response Time

| Test ID | Endpoint | Expected Response Time |
|---------|----------|------------------------|
| PERF-006 | /load_data | < 500ms |
| PERF-007 | /setup_tournament | < 2 seconds |
| PERF-008 | /submit_player_results | < 1 second |
| PERF-009 | /get_tables/{n} | < 200ms |
| PERF-010 | /tournament_statistics | < 500ms |

### 9.3 Frontend Rendering Performance

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| PERF-011 | Render 16 teams grid | < 100ms |
| PERF-012 | Render 16 tables (Swiss) | < 200ms |
| PERF-013 | Update all scores (64 players) | < 150ms |
| PERF-014 | Round selector navigation | < 100ms |

---

## 10. Edge Case & Error Handling Tests

### 10.1 Data Validation Tests

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| EDGE-001 | Missing Excel file | Error message, graceful handling |
| EDGE-002 | Invalid team count (15 teams) | Warning, tournament may proceed with relaxed constraints |
| EDGE-003 | Duplicate player names | Accept (use Player ID as unique) |
| EDGE-004 | Empty team name | Reject with error |
| EDGE-005 | Team with < 4 players | Reject with error |
| EDGE-006 | Team with > 4 players | Reject with error |

### 10.2 State Validation Tests

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| EDGE-007 | Submit results without entering scores | Prevent submission |
| EDGE-008 | Submit same round twice | Reject, round already finalized |
| EDGE-009 | Access Round 3 before Round 2 submitted | Return empty/error |
| EDGE-010 | Submit invalid player ID | Reject with error |
| EDGE-011 | Submit negative score | Reject with error |

### 10.3 Network Error Handling

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| EDGE-012 | API timeout on submit | Show error toast, retry option |
| EDGE-013 | API 500 error | Show error message, state preserved |
| EDGE-014 | Network disconnect mid-submission | Auto-backup should preserve state |
| EDGE-015 | Restore from corrupted backup | Graceful failure, error message |

### 10.4 Concurrent Operation Tests

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| EDGE-016 | Double-click submit button | Prevent duplicate submissions |
| EDGE-017 | Rapid score changes | Final score saved correctly |
| EDGE-018 | Navigation during submission | Block until complete |

---

## 11. Test Data Requirements

### 11.1 16-Team Test Data (Standard)

**File:** `participants/participant_team.xlsx`

| Column | Format | Example |
|--------|--------|---------|
| Player ID | Integer | 1, 2, 3, ... 64 |
| Player Name | String | Player A1, Player A2, ... |
| Team Name | String | Team A, Team B, ... Team P |

**Team Distribution:**
- 16 teams: Team A through Team P
- 4 players per team
- Total: 64 players

### 11.2 Score Distribution Scenarios

**Scenario A: Clear Winner**
- One team wins all games (dominates)
- Used to test champion determination

**Scenario B: Close Competition**
- Multiple teams tied after Swiss
- Tests tiebreaker logic

**Scenario C: Mixed Results**
- Realistic distribution of W/D/L
- Tests ranking accuracy

### 11.3 Test Data Generation

Use `generate_16_teams.py` to create standard test data:

```bash
python generate_16_teams.py
```

---

## 12. Test Execution Checklist

### 12.1 Pre-Test Setup
- [ ] Python 3.8+ installed
- [ ] Flask dependencies installed (`pip install flask openpyxl`)
- [ ] Test data file exists (`participants/participant_team.xlsx`)
- [ ] No existing backup files (clean state)

### 12.2 Backend Test Execution

```bash
# Run unit tests
python -m pytest test_backup_restore.py -v

# Run full tournament flow test
python test_tournament_comprehensive.py
```

### 12.3 API Test Execution

```bash
# Start server
python tournament_dashboard.py

# Run API tests (separate terminal)
# Use curl, Postman, or pytest with requests
```

### 12.4 Frontend Test Execution

1. Start Flask server: `python tournament_dashboard.py`
2. Open browser: `http://localhost:5000`
3. Execute manual test cases from sections 5, 7
4. Check browser console for JavaScript errors

### 12.5 Complete 16-Team Tournament Test

**Manual Test Procedure:**

1. **Load Data**
   - [ ] Click "Load Participants"
   - [ ] Verify 16 teams displayed
   - [ ] Verify 64 players total

2. **Setup Tournament**
   - [ ] Click "Setup Tournament"
   - [ ] Verify Round 1 has 16 tables
   - [ ] Verify no teammate violations

3. **Swiss Rounds 1-4**
   - [ ] For each round:
     - [ ] Enter scores for all 64 players
     - [ ] Submit all 16 tables
     - [ ] Click "Submit Round Results"
     - [ ] Verify next round generated
     - [ ] Verify no repeat matchups

4. **Top 8 Cut (Round 5)**
   - [ ] Verify 8 teams selected
   - [ ] Verify 8 tables generated
   - [ ] Enter scores for 32 players
   - [ ] Submit all 8 tables
   - [ ] Click "Submit Round Results"

5. **Finals (Round 6)**
   - [ ] Verify 4 teams selected
   - [ ] Verify 4 tables generated
   - [ ] Enter scores for 16 players
   - [ ] Submit all 4 tables
   - [ ] Click "Submit Round Results"

6. **Verify Results**
   - [ ] Championship modal appears
   - [ ] Winner displayed correctly
   - [ ] Final standings show all 16 teams
   - [ ] No JavaScript errors in console

### 12.6 Sign-Off Criteria

| Category | Pass Criteria |
|----------|---------------|
| Backend Unit Tests | 100% pass rate |
| API Integration Tests | 100% pass rate |
| Frontend Tests | All manual tests pass |
| E2E Tournament Flow | Complete without errors |
| Performance Tests | All within thresholds |
| Edge Cases | Graceful handling |

---

## Appendix A: API Endpoint Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve dashboard HTML |
| `/load_data` | GET/POST | Load participants, set Swiss rounds |
| `/setup_tournament` | POST | Initialize tournament, generate R1 |
| `/submit_player_results` | POST | Finalize round, generate next |
| `/submit_table_results` | POST | Submit single table scores |
| `/get_tables/<n>` | GET | Get round N pairings |
| `/get_tournament_state` | GET | Get current state |
| `/get_semifinals` | GET | Get Top 8 Cut pods |
| `/get_finals` | GET | Get Finals pods |
| `/get_final_standings` | GET | Get final rankings |
| `/tournament_statistics` | GET | Get detailed stats |
| `/restore_backup` | POST | Restore from backup file |
| `/save_backup` | POST | Create backup |
| `/reset_tournament` | POST | Reset all state |

---

## Appendix B: Known Constraints

1. **Teammate Separation:** Teammates NEVER in same pod (hard constraint)
2. **Team Separation:** 4-player pods must have 4 different teams
3. **Zero Repeat Guarantee:** For 16 teams over 4 Swiss rounds, mathematically guaranteed (15 available opponents, 12 needed)
4. **Scoring:** W=5, D=1, L=0 points
5. **Top 8 Cut:** Top 8 teams by Swiss points advance
6. **Finals:** Top 4 teams from Top 8 Cut advance

---

## Appendix C: Validation Queries

### Check for Teammate Violations
```python
def check_no_teammates_in_pod(pod):
    teams = [player['Team Name'] for player in pod]
    return len(teams) == len(set(teams))  # All unique teams
```

### Check for Repeat Matchups
```python
def check_no_repeat_matchups(round1_pods, round2_pods):
    def get_team_set(pod):
        return frozenset(p['Team Name'] for p in pod)

    r1_matchups = {get_team_set(pod) for pod in round1_pods}
    r2_matchups = {get_team_set(pod) for pod in round2_pods}

    return len(r1_matchups & r2_matchups) == 0  # No overlap
```

---

**End of Test Plan**
