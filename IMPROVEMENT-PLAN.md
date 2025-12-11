# MTG Tournament Dashboard - Improvement Plan

**Version:** 1.0
**Date:** December 11, 2025
**Status:** Draft - Pending Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 1: Critical Bug Fixes](#phase-1-critical-bug-fixes)
3. [Phase 2: Security & Validation Fixes](#phase-2-security--validation-fixes)
4. [Phase 3: UX & Error Handling Improvements](#phase-3-ux--error-handling-improvements)
5. [Phase 4: Code Quality Improvements](#phase-4-code-quality-improvements)
6. [Phase 5: Performance Optimizations](#phase-5-performance-optimizations)
7. [Phase 6: Future Feature Suggestions](#phase-6-future-feature-suggestions)
8. [Implementation Priority Matrix](#implementation-priority-matrix)
9. [Testing Requirements](#testing-requirements)

---

## Executive Summary

After a thorough analysis of the tournament flow logic, frontend structure, and integration points, this plan identifies:

- **8 Critical Bugs** - Must fix for 16-team tournaments to work correctly
- **12 High-Priority Issues** - Security and validation gaps
- **15+ Enhancement Opportunities** - UX, code quality, and performance

### Key Findings

| Category | Count | Severity |
|----------|-------|----------|
| Hardcoded Round Numbers | 2 | Critical |
| Missing/Wrong API Endpoints | 2 | Critical |
| Input Validation Gaps | 5 | High |
| XSS Vulnerabilities | 1 | High |
| Double-Submission Risk | 1 | High |
| UX Friction Points | 4 | Medium |
| Code Duplication | 3 | Low |
| Performance Issues | 2 | Low |

---

## Phase 1: Critical Bug Fixes

> **Priority: P0 - Must Fix Before Any 16-Team Tournament**

This phase addresses the fundamental structural bugs preventing 16-team tournaments from completing.

### 1.1 Hardcoded Round Number Logic (Backend & Frontend)

**Severity:** CRITICAL
**Impact:** Champion determination fails, finals detection fails for 16-team (6 round) tournaments.

#### Backend Fix
**File:** `tournament_dashboard.py`
**Line:** 1979 in `submit_table_results`

Change the hardcoded round 5 check to dynamic `max_rounds`:
```python
# Handle final round scoring separately
if round_num == tournament.max_rounds:  # Was: if round_num == 5:
    tournament.update_final_round_scores(round_num, player_results)
```

#### Frontend Fix 1: State Initialization
**File:** `dashboard_ultra_modern.html`
**Lines:** ~2889 (`loadParticipants`) and ~3093 (`setupTournament`)

**IMPORTANT:** The frontend currently does NOT capture `max_rounds` from any API response. This variable must be added to the global state before the dynamic finals detection will work.

We need to ensure `window.tournamentMaxRounds` is initialized from the API response so other functions can use it.

**In `loadParticipants` (Line ~2889):**
```javascript
if (data.success && data.teams) {
    // NEW: Store max rounds
    if (data.max_rounds) {
        window.tournamentMaxRounds = data.max_rounds;
    }
    // ... rest of function
```

**In `setupTournament` (Line ~3093):**
```javascript
// Store tournament configuration globally
window.tournamentSwissRounds = swissRounds;
window.totalTeams = teamCount;
// NEW: Store max rounds
if (data.max_rounds) {
     window.tournamentMaxRounds = data.max_rounds;
}
```

#### Frontend Fix 2: Dynamic Finals Mode
**File:** `dashboard_ultra_modern.html`
**Line:** 3581 in `refreshTeamScores`

Update finals detection to use the dynamic variable:
```javascript
if (finalsMode === null) {
    const currentRound = document.getElementById('round-select').value;
    // was: finalsMode = (currentRound === '5' || currentRound === 5);
    const maxRounds = window.tournamentMaxRounds || 5;
    finalsMode = (parseInt(currentRound) === maxRounds);
}
```

---

### 1.2 Missing API Endpoint

**Severity:** CRITICAL
**Impact:** Bracket visualization fails silently.

**File:** `dashboard_ultra_modern.html`
**Line:** 3329 in `updateBracketVisualization`

Change the call to the non-existent `/get_standings` to the existing `/standings` endpoint:
```javascript
try {
    // Fetch current standings to get team scores
    const standingsResponse = await fetch('/standings'); // Was: fetch('/get_standings');
    const standingsData = await standingsResponse.json();
```

---

### 1.3 Incorrect Round Type Detection

**Severity:** CRITICAL
**Impact:** Bracket visualization fails for "Top 8 Cut" round.

**File:** `dashboard_ultra_modern.html`
**Function:** `updateBracketVisualization`

**Issue:** The code checks for `'semifinals'` but `getRoundType()` returns `'top8cut'`. Two locations need fixing (both use the wrong string 'semifinals').

Matches internal logic to `getRoundType` return value ('top8cut').

**Line 3322:**
```javascript
// Only show bracket for top8cut and finals
if (roundType !== 'top8cut' && roundType !== 'finals') { // Was: !== 'semifinals'
    bracketContainer.style.display = 'none';
    return;
}
```

**Line 3339:**
```javascript
if (roundType === 'top8cut') { // Was: === 'semifinals'
    // Show top 8 teams in semifinals bracket
    bracketTitleText.textContent = 'Semifinals Bracket - Top 8 Teams';
```

**Note:** Both line 3322 and 3339 must be updated. The `getRoundType()` function (line 2803) correctly returns `'top8cut'`, but the bracket visualization logic checks for the old string `'semifinals'`.

---

### 1.4 Verification Plan for Phase 1

1.  **Automated Tests:**
    ```bash
    python test_tournament_comprehensive.py --teams 16
    ```
    Ensure `test_finals` passes on 16 teams.

2.  **Manual Browser Verification:**
    -   Start server: `python tournament_dashboard.py`
    -   Load a 16-team participant list.
    -   **Console Check:** Type `window.tournamentMaxRounds` -> Must be `6`.
    -   Simulate rounds up to Round 5.
    -   **Round 5 (Top 8 Cut):** Verify "Tournament Bracket" title appears and shows 8 teams (checking `roundType === 'top8cut'`).
    -   **Round 6 (Finals):** Verify "Finals Mode" activates (checking `max_rounds`).

---

## Phase 2: Security & Validation Fixes

> **Priority: P1 - Should Fix**

### 2.1 XSS Vulnerability in Score Buttons

**Severity:** HIGH
**Impact:** Potential code injection via malicious table names

#### Affected Location

| File | Lines | Code |
|------|-------|------|
| `dashboard_ultra_modern.html` | 3512-3522 | `onclick="setPlayerScore('${tableName}', ...)"` |

#### Vulnerability

```javascript
// If tableName = "Table'; alert('XSS'); //", this becomes:
onclick="setPlayerScore('Table'; alert('XSS'); //', 1, 5, this)"
```

#### Required Changes

**Replace inline onclick with data attributes and event delegation:**

```html
<!-- BEFORE (vulnerable): -->
<button class="score-btn" onclick="setPlayerScore('${tableName}', ${playerId}, 5, this)">W</button>

<!-- AFTER (safe): -->
<button class="score-btn"
        data-table="${tableName.replace(/'/g, '&#39;')}"
        data-player="${playerId}"
        data-points="5">W</button>
```

```javascript
// Add event delegation
document.addEventListener('click', function(e) {
    if (e.target.matches('.score-btn')) {
        const tableName = e.target.dataset.table;
        const playerId = parseInt(e.target.dataset.player);
        const points = parseInt(e.target.dataset.points);
        setPlayerScore(tableName, playerId, points, e.target);
    }
});
```

#### Testing Required
- [ ] Score buttons work with normal table names
- [ ] Score buttons work with special characters in table names
- [ ] No XSS possible via table name injection

---

### 2.2 Missing Input Validation

**Severity:** HIGH
**Impact:** Server errors, potential data corruption

#### Affected Location

| File | Lines | Endpoint |
|------|-------|----------|
| `tournament_dashboard.py` | 1939-1995 | `/submit_table_results` |

#### Current Issues

1. No try-except wrapper around entire function
2. No validation of `round_num` type or range
3. No validation of `player_id` type
4. No validation of `points` value (should be 0, 1, or 5)
5. No check for KeyError on missing fields
6. No check for null/undefined values

#### Required Changes

```python
@app.route('/submit_table_results', methods=['POST'])
def submit_table_results():
    """Submit results for a specific table with full validation."""
    try:
        data = request.json

        # Validate request body exists
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Validate round number
        round_num = data.get('round')
        if not isinstance(round_num, int) or round_num < 1 or round_num > tournament.max_rounds:
            return jsonify({'success': False, 'error': f'Invalid round number: {round_num}'}), 400

        # Validate table name
        table_name = data.get('table')
        if not table_name or not isinstance(table_name, str):
            return jsonify({'success': False, 'error': 'Invalid table name'}), 400

        # Validate table exists in round
        if round_num in tournament.tables and table_name not in tournament.tables[round_num]:
            return jsonify({'success': False, 'error': f'Table {table_name} not found in round {round_num}'}), 400

        # Validate player results
        player_results = data.get('results', [])
        if not isinstance(player_results, list) or len(player_results) == 0:
            return jsonify({'success': False, 'error': 'No player results provided'}), 400

        for result in player_results:
            # Check required fields exist
            if 'player_id' not in result or 'points' not in result:
                return jsonify({'success': False, 'error': 'Missing player_id or points in result'}), 400

            # Validate player_id
            player_id = result['player_id']
            if not isinstance(player_id, int) or player_id not in tournament.player_scores:
                return jsonify({'success': False, 'error': f'Invalid player_id: {player_id}'}), 400

            # Validate points (must be 0, 1, or 5)
            points = result['points']
            if points not in [0, 1, 5]:
                return jsonify({'success': False, 'error': f'Invalid points value: {points}. Must be 0, 1, or 5'}), 400

        # ... existing processing logic ...

    except Exception as e:
        print(f"[ERROR] submit_table_results failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500
```

#### Testing Required
- [ ] Valid submissions succeed
- [ ] Invalid round numbers rejected
- [ ] Invalid player IDs rejected
- [ ] Invalid points values rejected
- [ ] Missing fields handled gracefully

---

### 2.3 Double-Submission Prevention

**Severity:** HIGH
**Impact:** Scores counted twice, incorrect standings

#### Current Problem

If a user clicks "Submit" twice quickly (or network delays cause retry), points are added twice:

```python
# Line 1972: Points are ADDED, not SET
tournament.player_scores[player_id] += points
```

#### Required Changes

**Backend: Track submitted tables**
```python
# In submit_table_results(), add check:
if round_num not in tournament.round_results:
    tournament.round_results[round_num] = {'table_submissions': {}, 'submitted_tables': set()}

# Check if already submitted
if table_name in tournament.round_results[round_num].get('submitted_tables', set()):
    return jsonify({
        'success': False,
        'error': f'{table_name} already submitted for round {round_num}',
        'already_submitted': True
    }), 400

# After successful processing, mark as submitted
tournament.round_results[round_num]['submitted_tables'].add(table_name)
```

**Frontend: Disable button after submission**
```javascript
async function submitTableResults(tableName) {
    const submitBtn = document.querySelector(`[data-submit-table="${tableName}"]`);

    // Prevent double-click
    if (submitBtn.disabled) return;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
        const response = await fetch('/submit_table_results', { ... });
        const data = await response.json();

        if (data.success) {
            submitBtn.textContent = 'Submitted ✓';
            submitBtn.classList.add('submitted');
        } else if (data.already_submitted) {
            submitBtn.textContent = 'Already Submitted';
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit';
            showToast('Error', data.error, 'error');
        }
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit';
        showToast('Error', 'Network error, please try again', 'error');
    }
}
```

#### Testing Required
- [ ] Single submission works normally
- [ ] Double-click prevented
- [ ] Already-submitted tables show correct state after page refresh

---

## Phase 3: UX & Error Handling Improvements

> **Priority: P2 - Nice to Have**

### 3.1 Table Submission Status Tracking

**Current Problem:** Users can't easily see which tables have been submitted.

**Proposed Solution:**

1. Add visual indicator (checkmark icon) on submitted tables
2. Show progress bar: "12/16 tables submitted"
3. Disable score buttons on submitted tables
4. Show confirmation before round finalization

**UI Mockup:**
```
Round 1 Progress: [████████████░░░░] 12/16 tables submitted

┌─────────────────────────────────────┐
│ Table 1 ✓ SUBMITTED                 │
│ Players: Alice, Bob, Charlie, Diana │
│ Scores: 5, 0, 1, 0 (locked)         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Table 2 ⚠ PENDING                   │
│ Players: Eve, Frank, Grace, Henry   │
│ [W] [D] [L] buttons active          │
│ [Submit Table Results]              │
└─────────────────────────────────────┘
```

---

### 3.2 Score Correction Mechanism

**Current Problem:** No way to fix incorrectly entered scores.

**Proposed Solution:**

1. Add "Edit Scores" button for unfinalized rounds
2. Require confirmation before overwriting scores
3. Store score history for audit trail

**Implementation:**
```python
# New endpoint: /edit_table_results
@app.route('/edit_table_results', methods=['POST'])
def edit_table_results():
    """Edit previously submitted table results (before round finalization)."""
    # Validate round not yet finalized
    if round_num in tournament.finalized_rounds:
        return jsonify({'success': False, 'error': 'Cannot edit finalized round'}), 400

    # Store old scores in history
    old_scores = tournament.round_results[round_num]['table_submissions'][table_name]
    if 'score_history' not in tournament.round_results[round_num]:
        tournament.round_results[round_num]['score_history'] = {}
    tournament.round_results[round_num]['score_history'][table_name] = old_scores

    # Subtract old scores, add new scores
    # ... implementation ...
```

---

### 3.3 Improved Error Messages

**Current Problem:** Generic errors don't help users understand what went wrong.

**Proposed Solution:**

| Scenario | Current Message | Improved Message |
|----------|-----------------|------------------|
| Missing scores | "Error" | "Please enter scores for all 4 players before submitting" |
| Network error | (silent fail) | "Network error. Your scores were not saved. Please try again." |
| Invalid round | 500 error | "Round 3 is not available yet. Please complete Round 2 first." |
| Double submit | (accepts both) | "Table 1 was already submitted. Scores are locked." |

---

### 3.4 Tournament State Validation

**Current Problem:** Operations can be performed out of sequence.

**Proposed State Machine:**

```
[Not Initialized]
       │
       ▼ load_data()
[Participants Loaded]
       │
       ▼ setup_tournament()
[Round 1 Active]
       │
       ▼ submit_player_results(1)
[Round 2 Active]
       │
       ▼ ... (repeat for rounds 3-4)
[Round 5 Active] (Top 8 Cut for 16 teams)
       │
       ▼ submit_player_results(5)
[Finals Active]
       │
       ▼ submit_player_results(6)
[Tournament Complete]
```

**Validation Rules:**
- Cannot setup if not loaded
- Cannot submit round N if round N-1 not finalized
- Cannot submit round if already finalized
- Cannot load new participants if tournament in progress

---

## Phase 4: Code Quality Improvements

> **Priority: P3 - Technical Debt**

### 4.1 Remove Code Duplication

**Location 1:** `tournament_dashboard.py:705-709` - Duplicate print statement
```python
# Line 708
print(f"      Seating: {seating_str}")
# Line 709 (duplicate - remove this)
print(f"      Seating: {seating_str}")
```

**Location 2:** Team name lookup pattern repeated 5+ times
```python
# Create helper function:
def get_team_name(participant: dict) -> str:
    """Extract team name from participant dict with fallback."""
    return (participant.get('Team Name') or
            participant.get('Team') or
            participant.get('team_name') or
            participant.get('team') or
            'Unknown Team')
```

---

### 4.2 Standardize Naming Conventions

**Current Inconsistencies:**

| Context | Variant 1 | Variant 2 | Recommendation |
|---------|-----------|-----------|----------------|
| Round type | `top8cut` | `semifinals` | Use `top8cut` |
| Player ID field | `Player ID` | `player_id` | Use `player_id` |
| Team name field | `Team Name` | `team_name` | Use `team_name` |

**Action:** Create constants file and update all references.

---

### 4.3 Add API Documentation

**Proposed Format:**

```python
@app.route('/submit_table_results', methods=['POST'])
def submit_table_results():
    """
    Submit results for a specific table.

    Request Body:
        {
            "round": int,           # Round number (1-6)
            "table": str,           # Table name (e.g., "Table 1")
            "results": [            # Array of player results
                {
                    "player_id": int,   # Player ID
                    "points": int       # Points (0=Loss, 1=Draw, 5=Win)
                },
                ...
            ]
        }

    Response (Success):
        {
            "success": true,
            "message": str,
            "table": str,
            "round": int,
            "scores": dict,         # Updated team scores
            "player_scores": dict   # Updated player scores
        }

    Response (Error):
        {
            "success": false,
            "error": str            # Error message
        }

    Status Codes:
        200 - Success
        400 - Invalid input
        500 - Server error
    """
```

---

### 4.4 Improve Logging

**Current:** Mix of `print()` statements with inconsistent formatting.

**Proposed:** Use Python `logging` module with levels.

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Usage:
logger.info(f"Tournament setup complete: {len(teams)} teams")
logger.warning(f"Player ID {player_id} not found")
logger.error(f"Failed to save backup: {e}")
logger.debug(f"Processing table {table_name} with results: {results}")
```

---

## Phase 5: Performance Optimizations

> **Priority: P3 - Technical Debt**

### 5.1 Incremental Score Updates

**Current:** `calculate_team_scores()` recalculates ALL teams after each table submission.

**Proposed:** Only update affected team's score.

```python
def update_team_score(self, team_name: str):
    """Incrementally update a single team's score."""
    players = self.teams.get(team_name, [])
    total = sum(self.player_scores.get(p['Player ID'], 0) for p in players)
    self.scores[team_name] = total

# In submit_table_results:
affected_teams = set(result['team_name'] for result in player_results)
for team in affected_teams:
    tournament.update_team_score(team)
```

---

### 5.2 Dedicated Score Endpoint

**Current:** Frontend calls `/load_data` (heavy) just to refresh scores.

**Proposed:** Create lightweight endpoint.

```python
@app.route('/get_current_scores')
def get_current_scores():
    """Lightweight endpoint for score refresh."""
    return jsonify({
        'success': True,
        'scores': tournament.scores,
        'player_scores': tournament.player_scores,
        'current_round': tournament.current_round
    })
```

---

## Phase 6: Future Feature Suggestions

> **Priority: P4 - Future Enhancements**

### 6.1 Real-time Updates (WebSocket)

**Benefit:** Multiple organizers can see live score updates.

**Implementation:** Add Flask-SocketIO for real-time broadcasts.

---

### 6.2 Tournament Templates

**Benefit:** Quick setup for common tournament formats.

**Features:**
- Preset configurations for 8/12/16 team tournaments
- Save/load tournament settings
- Import team lists from previous tournaments

---

### 6.3 Export Results

**Benefit:** Generate reports for participants.

**Features:**
- Export final standings to PDF/Excel
- Generate certificates for winners
- Create shareable tournament summary page

---

### 6.4 Undo/Redo System

**Benefit:** Recover from mistakes without manual intervention.

**Features:**
- Undo last score submission
- Redo undone actions
- Full action history log

---

## Implementation Priority Matrix

| Phase | Description | Effort | Impact | Priority |
|-------|-------------|--------|--------|----------|
| **1** | Critical Bug Fixes | Low | Critical | **P0 - Must Fix** |
| **2** | Security & Validation | Medium | High | **P1 - Should Fix** |
| **3** | UX Improvements | Medium | Medium | P2 - Nice to Have |
| **4** | Code Quality | Low | Low | P3 - Technical Debt |
| **5** | Performance | Low | Low | P3 - Technical Debt |
| **6** | New Features | High | Medium | P4 - Future |

---

## Recommended Implementation Order

### Immediate (Before Next 16-Team Tournament)
1. [ ] Fix hardcoded round 5 → `max_rounds` (1.1 - Backend: 1 location)
2. [ ] Capture `max_rounds` in frontend state (1.1 - Frontend: 2 locations)
3. [ ] Update finals detection to use dynamic max_rounds (1.1 - Frontend: 1 location)
4. [ ] Fix missing `/get_standings` endpoint (1.2 - Frontend: 1 location)
5. [ ] Fix round type detection mismatch (1.3 - Frontend: 2 locations)

### Short Term (Next Sprint)
4. [ ] Add input validation to submit_table_results (2.2)
5. [ ] Add double-submission prevention (2.3)
6. [ ] Fix XSS vulnerability (2.1)

### Medium Term (Next Month)
7. [ ] Add table submission status tracking (3.1)
8. [ ] Add score correction mechanism (3.2)
9. [ ] Improve error messages (3.3)
10. [ ] Add tournament state validation (3.4)

### Long Term (Backlog)
11. [ ] Code quality improvements (Phase 4)
12. [ ] Performance optimizations (Phase 5)
13. [ ] New features (Phase 6)

---

## Testing Requirements

### For Each Fix

- [ ] Unit test for the specific fix
- [ ] Integration test for affected flow
- [ ] Manual verification with 16-team tournament

### Test Coverage Gaps to Address

| Gap | Test Needed |
|-----|-------------|
| Finals scoring for 16 teams | Verify round 6 triggers final scoring |
| Bracket visualization | Verify displays for Top 8 Cut and Finals |
| Double-submission | Verify second submission rejected |
| Invalid input | Verify all validation rules enforced |
| XSS prevention | Verify special characters handled safely |

---

## Appendix: File Locations Reference

| Issue | File | Line(s) |
|-------|------|---------|
| Hardcoded round 5 (backend) | `tournament_dashboard.py` | 1979 |
| Hardcoded round 5 (frontend) | `dashboard_ultra_modern.html` | 3581 |
| Missing endpoint | `dashboard_ultra_modern.html` | 3329 |
| Round type mismatch | `dashboard_ultra_modern.html` | 3322 |
| XSS vulnerability | `dashboard_ultra_modern.html` | 3512-3522 |
| Missing validation | `tournament_dashboard.py` | 1939-1995 |
| Duplicate print | `tournament_dashboard.py` | 705-709 |

---

**Document Status:** Ready for Review
**Next Action:** Prioritize and assign implementation tasks
