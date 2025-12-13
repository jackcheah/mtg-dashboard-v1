# Phase 2 Implementation Plan: Security & Validation Fixes

**Version:** 1.0  
**Date:** December 13, 2025  
**Status:** Ready for Implementation  
**Priority:** P1 - Should Fix  
**Estimated Effort:** 8-12 hours  

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Implementation Tasks](#implementation-tasks)
4. [Testing Strategy](#testing-strategy)
5. [Rollback Plan](#rollback-plan)
6. [Success Criteria](#success-criteria)

---

## Overview

Phase 2 addresses critical security vulnerabilities and input validation gaps that could lead to:
- **XSS attacks** via malicious table names
- **Data corruption** from invalid input
- **Score duplication** from double-submission
- **Server crashes** from unhandled exceptions

### Scope

| Task | Files Affected | Lines Changed | Risk Level |
|------|----------------|---------------|------------|
| 2.1 XSS Fix | `dashboard_ultra_modern.html` | ~50 | Medium |
| 2.2 Input Validation | `tournament_dashboard.py` | ~80 | Low |
| 2.3 Double-Submission | Both files | ~60 | Medium |

**Total Estimated Changes:** ~190 lines across 2 files

---

## Prerequisites

### Before Starting

- [ ] **Phase 1 must be completed** (all critical bugs fixed)
- [ ] Backup current working version
- [ ] Review current codebase state
- [ ] Set up test environment with sample data

### Required Knowledge

- Python Flask request validation patterns
- JavaScript event delegation
- HTML data attributes
- XSS attack vectors and prevention

### Tools Needed

- Code editor with search/replace
- Browser developer console
- Python debugger (optional)

---

## Implementation Tasks

### Task 2.1: Fix XSS Vulnerability in Score Buttons

**Priority:** HIGH  
**Estimated Time:** 2-3 hours  
**Risk:** Medium (affects all score entry)

#### Current Vulnerability

```javascript
// Line 3512-3522 in dashboard_ultra_modern.html
onclick="setPlayerScore('${tableName}', ${playerId}, 5, this)"
// If tableName contains quotes or script tags, code injection is possible
```

#### Implementation Steps

**Step 1: Replace inline onclick with data attributes**

**File:** `dashboard_ultra_modern.html`  
**Location:** Lines 3512-3522 (inside `displayRoundTables` function)

```javascript
// BEFORE (vulnerable):
<button class="score-btn win-btn" 
        onclick="setPlayerScore('${tableName}', ${playerId}, 5, this)">
    W (5)
</button>
<button class="score-btn draw-btn" 
        onclick="setPlayerScore('${tableName}', ${playerId}, 1, this)">
    D (1)
</button>
<button class="score-btn loss-btn" 
        onclick="setPlayerScore('${tableName}', ${playerId}, 0, this)">
    L (0)
</button>

// AFTER (safe):
<button class="score-btn win-btn" 
        data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
        data-player="${playerId}"
        data-points="5">
    W (5)
</button>
<button class="score-btn draw-btn" 
        data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
        data-player="${playerId}"
        data-points="1">
    D (1)
</button>
<button class="score-btn loss-btn" 
        data-table="${tableName.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}"
        data-player="${playerId}"
        data-points="0">
    L (0)
</button>
```

**Step 2: Add event delegation handler**

**File:** `dashboard_ultra_modern.html`
**Location:** Add to `<script>` section (after existing event listeners, around line 3800+)

```javascript
// Event delegation for score buttons (XSS-safe)
document.addEventListener('click', function(e) {
    if (e.target.matches('.score-btn') || e.target.closest('.score-btn')) {
        const btn = e.target.matches('.score-btn') ? e.target : e.target.closest('.score-btn');

        // Extract data attributes
        const tableName = btn.dataset.table;
        const playerId = parseInt(btn.dataset.player);
        const points = parseInt(btn.dataset.points);

        // Validate data exists
        if (!tableName || isNaN(playerId) || isNaN(points)) {
            console.error('Invalid score button data:', { tableName, playerId, points });
            return;
        }

        // Call existing function
        setPlayerScore(tableName, playerId, points, btn);
    }
});
```

**Step 3: Testing**
- [ ] Test with normal table names (e.g., "Table 1")
- [ ] Test with special characters (e.g., "Table's 1", `Table"2`)
- [ ] Verify no console errors
- [ ] Verify scores are recorded correctly

---

### Task 2.2: Add Input Validation to Backend

**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Risk:** Low (defensive programming)

#### Current Problem

The `/submit_table_results` endpoint has no validation:
- No type checking for `round_num`, `player_id`, `points`
- No range validation
- No error handling wrapper
- Server crashes on invalid input

#### Implementation Steps

**File:** `tournament_dashboard.py`
**Location:** Lines 1939-1995 (function `submit_table_results`)

**Replace the entire function with validated version:**

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

        # === EXISTING PROCESSING LOGIC BELOW (keep unchanged) ===
        # Update player scores
        for result in player_results:
            player_id = result['player_id']
            points = result['points']

            if player_id in tournament.player_scores:
                tournament.player_scores[player_id] += points
            else:
                print(f"  WARNING: Player ID {player_id} not found in player_scores!")

        # Handle final round scoring separately
        if round_num == tournament.max_rounds:
            tournament.update_final_round_scores(round_num, player_results)

        # Recalculate team scores from individual player scores
        tournament.calculate_team_scores()

        return jsonify({
            'success': True,
            'message': f'{table_name} results submitted successfully',
            'table': table_name,
            'round': round_num,
            'scores': tournament.scores,
            'player_scores': tournament.player_scores
        })

    except Exception as e:
        print(f"[ERROR] submit_table_results failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500
```

**Testing:**
- [ ] Valid submission succeeds
- [ ] Invalid round number rejected (e.g., round 99)
- [ ] Invalid player ID rejected
- [ ] Invalid points rejected (e.g., points=10)
- [ ] Missing fields handled gracefully
- [ ] Server doesn't crash on malformed JSON

---

### Task 2.3: Prevent Double-Submission

**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Risk:** Medium (affects both backend and frontend)

#### Current Problem

Users can submit the same table multiple times:
- Points are **added** (`+=`), not set
- No tracking of submitted tables
- No UI feedback on submission state

#### Implementation Steps

**Part A: Backend - Track Submitted Tables**

**File:** `tournament_dashboard.py`
**Location:** Inside `submit_table_results` function (after validation, before processing)

**Add this check after line ~1975 (after validation block):**

```python
# Check for double-submission
if round_num not in tournament.round_results:
    tournament.round_results[round_num] = {'table_submissions': {}, 'submitted_tables': set()}

if table_name in tournament.round_results[round_num].get('submitted_tables', set()):
    return jsonify({
        'success': False,
        'error': f'{table_name} already submitted for round {round_num}',
        'already_submitted': True
    }), 400

# ... existing processing logic ...

# After successful processing (before return statement), add:
tournament.round_results[round_num]['submitted_tables'].add(table_name)
```

**Part B: Frontend - Disable Button After Submission**

**File:** `dashboard_ultra_modern.html`
**Location:** Find `submitTableResults` function (around line 3700-3750)

**Replace the function with:**

```javascript
async function submitTableResults(tableName) {
    const submitBtn = document.querySelector(`button[onclick*="submitTableResults('${tableName}')"]`);

    // Prevent double-click
    if (submitBtn && submitBtn.disabled) {
        console.log('Submit already in progress for', tableName);
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
        submitBtn.style.opacity = '0.6';
    }

    try {
        const currentRound = document.getElementById('round-select').value;
        const tableScoresKey = `${tableName}_round${currentRound}`;
        const scores = tableScores[tableScoresKey];

        if (!scores || Object.keys(scores).length === 0) {
            showToast('Error', 'No scores entered for this table', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Table Results';
                submitBtn.style.opacity = '1';
            }
            return;
        }

        const results = Object.entries(scores).map(([playerId, points]) => ({
            player_id: parseInt(playerId),
            points: points
        }));

        const response = await fetch('/submit_table_results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                round: parseInt(currentRound),
                table: tableName,
                results: results
            })
        });

        const data = await response.json();

        if (data.success) {
            if (submitBtn) {
                submitBtn.textContent = 'Submitted ✓';
                submitBtn.classList.add('submitted');
                submitBtn.style.backgroundColor = '#10b981';
            }
            showToast('Success', data.message, 'success');
            await refreshTeamScores();
        } else if (data.already_submitted) {
            if (submitBtn) {
                submitBtn.textContent = 'Already Submitted';
                submitBtn.classList.add('submitted');
            }
            showToast('Info', data.error, 'warning');
        } else {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Submit Table Results';
                submitBtn.style.opacity = '1';
            }
            showToast('Error', data.error, 'error');
        }
    } catch (error) {
        console.error('Submit error:', error);
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Table Results';
            submitBtn.style.opacity = '1';
        }
        showToast('Error', 'Network error, please try again', 'error');
    }
}
```

**Part C: Add CSS for Submitted State**

**File:** `dashboard_ultra_modern.html`
**Location:** Add to `<style>` section (around line 1900+)

```css
/* Submitted table button styling */
button.submitted {
    background-color: #10b981 !important;
    cursor: not-allowed;
    opacity: 0.8;
}

button.submitted:hover {
    background-color: #059669 !important;
}
```

**Testing:**
- [ ] Single submission works normally
- [ ] Double-click prevented (button disabled immediately)
- [ ] Already-submitted tables show "Submitted ✓"
- [ ] Page refresh preserves submitted state
- [ ] Backend rejects duplicate submissions

---

## Testing Strategy

### Manual Testing Checklist

**Test Environment Setup:**
```bash
# 1. Backup current version
cp tournament_dashboard.py tournament_dashboard.py.backup
cp templates/dashboard_ultra_modern.html templates/dashboard_ultra_modern.html.backup

# 2. Start server
python tournament_dashboard.py

# 3. Open browser to http://127.0.0.1:5000
```

**Test Cases:**

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| XSS-1 | Normal table name | Scores recorded correctly |
| XSS-2 | Table name with apostrophe | No XSS, scores work |
| XSS-3 | Table name with quotes | No XSS, scores work |
| VAL-1 | Valid submission | 200 OK, scores updated |
| VAL-2 | Invalid round (99) | 400 error, clear message |
| VAL-3 | Invalid player ID | 400 error, clear message |
| VAL-4 | Invalid points (10) | 400 error, clear message |
| VAL-5 | Missing fields | 400 error, clear message |
| DUP-1 | Submit table once | Success |
| DUP-2 | Submit same table twice | Second rejected |
| DUP-3 | Refresh page | Submitted state preserved |

---

## Rollback Plan

If issues occur during implementation:

```bash
# Restore backup files
cp tournament_dashboard.py.backup tournament_dashboard.py
cp templates/dashboard_ultra_modern.html.backup templates/dashboard_ultra_modern.html

# Restart server
# Test that original functionality works
```

---

## Success Criteria

Phase 2 is complete when:

- [x] All XSS vulnerabilities fixed (no code injection possible)
- [x] All input validation added (invalid data rejected gracefully)
- [x] Double-submission prevented (backend + frontend)
- [x] All 11 test cases pass
- [x] No regression in existing functionality
- [x] Error messages are clear and helpful

---

## Implementation Order

Execute tasks in this sequence:

1. **Task 2.2** (Input Validation) - Safest, no UI changes
2. **Task 2.1** (XSS Fix) - Medium risk, test thoroughly
3. **Task 2.3** (Double-Submission) - Highest risk, affects both layers

---

## Notes for Implementation

### Critical Points

1. **Don't remove existing logic** - Only add validation wrapper around it
2. **Test after each task** - Don't batch all changes
3. **Keep backups** - Easy rollback if needed
4. **Check console** - Watch for JavaScript errors during testing

### Common Pitfalls to Avoid

- ❌ Don't change the scoring logic (`player_scores[id] += points`)
- ❌ Don't modify the `calculate_team_scores()` function
- ❌ Don't change API response structure (other code depends on it)
- ✅ Only add validation and safety checks

### File Line References

| Task | File | Approximate Lines |
|------|------|-------------------|
| 2.1 Step 1 | `dashboard_ultra_modern.html` | 3512-3522 |
| 2.1 Step 2 | `dashboard_ultra_modern.html` | 3800+ (add new) |
| 2.2 | `tournament_dashboard.py` | 1939-1995 (replace) |
| 2.3 Part A | `tournament_dashboard.py` | 1975+ (insert) |
| 2.3 Part B | `dashboard_ultra_modern.html` | 3700-3750 (replace) |
| 2.3 Part C | `dashboard_ultra_modern.html` | 1900+ (add new) |

---

**Document Status:** Ready for Execution
**Estimated Total Time:** 8-12 hours
**Risk Level:** Medium
**Dependencies:** Phase 1 must be complete ✅

---

## Quick Reference Summary

### Files to Modify

1. **`tournament_dashboard.py`**
   - Line 1939-1995: Add input validation to `submit_table_results()`
   - Line 1975+: Add double-submission check

2. **`templates/dashboard_ultra_modern.html`**
   - Line 3512-3522: Replace onclick with data attributes
   - Line 3800+: Add event delegation handler
   - Line 3700-3750: Update `submitTableResults()` function
   - Line 1900+: Add CSS for submitted state

### Key Changes Summary

| What | Why | How |
|------|-----|-----|
| XSS Fix | Prevent code injection | Use data attributes instead of inline onclick |
| Input Validation | Prevent server crashes | Validate all inputs before processing |
| Double-Submission | Prevent score duplication | Track submitted tables + disable buttons |

### Validation Rules to Implement

```python
# Round number: 1 <= round_num <= max_rounds
# Player ID: must exist in tournament.player_scores
# Points: must be 0, 1, or 5
# Table name: must be non-empty string
# Results: must be non-empty array
```

### Expected Outcomes

✅ **Security:** No XSS attacks possible
✅ **Reliability:** Invalid input rejected gracefully
✅ **Data Integrity:** No duplicate score submissions
✅ **User Experience:** Clear error messages

---

**END OF DOCUMENT**


