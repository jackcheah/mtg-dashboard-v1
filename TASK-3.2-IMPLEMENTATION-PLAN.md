# Task 3.2: Score Correction Mechanism - Implementation Plan

**Date:** 2025-12-15
**Estimated Time:** 4-6 hours
**Priority:** Medium (nice-to-have, but improves usability)
**Status:** Ready for Implementation

---

## Overview

Implement a score correction mechanism that allows tournament organizers to edit scores for submitted tables before a round is finalized. This includes proper audit trails, validation, and UI for editing.

---

## Problem Statement

Currently, there is no way to correct scores after a table has been submitted. If an organizer makes a mistake, they must:
1. Restart the affected round from the beginning
2. Or manually restart the server and reload from backup

This creates significant friction during tournament management.

---

## User Stories

1. **As a tournament organizer**, I want to edit scores for a submitted table so I can fix data entry mistakes
2. **As a tournament organizer**, I want to see a confirmation before editing to prevent accidental changes
3. **As a tournament organizer**, I want an audit trail of all score changes for transparency
4. **As a tournament organizer**, I want to be prevented from editing finalized rounds to maintain data integrity

---

## Prerequisites (Already Implemented ✅)

Before implementing this task, verify these exist in the codebase:

| Prerequisite | Location | Purpose |
|--------------|----------|---------|
| `finalized_rounds` set | `tournament_dashboard.py:46` | Tracks which rounds are locked |
| `submitted_tables` set | Per round in `round_results` | Tracks which tables have scores |
| `round_results` dictionary | `TournamentManager` | Stores table submissions |
| `player_scores` dictionary | `TournamentManager` | Individual player point totals |
| `calculate_team_scores()` | `tournament_dashboard.py:948` | Recalculates team totals |
| `update_final_round_scores()` | `tournament_dashboard.py:1070` | Finals-specific scoring |
| `TournamentState` enum | `tournament_dashboard.py:14` | State machine for validation |
| `@require_state` decorator | `tournament_dashboard.py:1500` | Endpoint state protection |

---

## Implementation Steps

### Step 1: Add Score History Tracking Structure

**File:** `tournament_dashboard.py`
**Location:** In `TournamentManager.__init__()` (around line 30)

Add initialization for score history tracking:

```python
# In __init__():
self.score_edit_history = {}  # Format: {round_num: {table_name: [edit_entries]}}
```

---

### Step 2: Create `/edit_table_results` Endpoint

**File:** `tournament_dashboard.py`
**Location:** After `/submit_table_results` endpoint (around line 2200)

Create a new endpoint with these requirements:

**Request Format:**
```json
{
    "round": 1,
    "table": "Table 1",
    "results": [
        {"player_id": 1, "points": 5},
        {"player_id": 2, "points": 0},
        {"player_id": 3, "points": 1},
        {"player_id": 4, "points": 0}
    ],
    "reason": "Correcting typo - Player 1 won, not Player 2"
}
```

**Response Format (Success):**
```json
{
    "success": true,
    "message": "Results updated for Table 1",
    "table": "Table 1",
    "round": 1,
    "scores": {"Team A": 25, "Team B": 20, ...},
    "player_scores": {1: 10, 2: 5, ...},
    "edit_count": 1,
    "previous_results": [...]
}
```

**Response Format (Error):**
```json
{
    "success": false,
    "error": "Technical error details",
    "user_message": "User-friendly explanation",
    "suggestion": "What to do next"
}
```

**Implementation Logic:**

```python
from datetime import datetime

@app.route('/edit_table_results', methods=['POST'])
@require_state(
    TournamentState.SWISS_IN_PROGRESS,
    TournamentState.TOP8_IN_PROGRESS,
    TournamentState.FINALS_IN_PROGRESS
)
def edit_table_results():
    """Edit previously submitted table results (before round finalization)."""
    try:
        data = request.json
        
        # ========================================
        # VALIDATION BLOCK (match Phase 2.2 standards)
        # ========================================
        
        # 1. Validate request body exists
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'user_message': 'The request was empty.',
                'suggestion': 'Please provide round, table, and results data.'
            }), 400
        
        # 2. Validate round number
        round_num = data.get('round')
        if not isinstance(round_num, int):
            return jsonify({
                'success': False,
                'error': f'Round must be an integer, got {type(round_num).__name__}',
                'user_message': 'Invalid round number format.',
                'suggestion': 'Please select a valid round.'
            }), 400
        
        if round_num < 1 or round_num > tournament.max_rounds:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} is out of range (1-{tournament.max_rounds})',
                'user_message': f'Round {round_num} does not exist.',
                'suggestion': f'Valid rounds are 1 to {tournament.max_rounds}.'
            }), 400
        
        # 3. Validate round is not finalized
        if hasattr(tournament, 'finalized_rounds') and round_num in tournament.finalized_rounds:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} is finalized',
                'user_message': f'Round {round_num} has been finalized and cannot be edited.',
                'suggestion': 'Finalized rounds are locked to preserve tournament integrity.'
            }), 400
        
        # 4. Validate table name
        table_name = data.get('table')
        if not table_name or not isinstance(table_name, str):
            return jsonify({
                'success': False,
                'error': 'Invalid table name',
                'user_message': 'Table name is required.',
                'suggestion': 'Please specify which table to edit.'
            }), 400
        
        # 5. Validate table was previously submitted
        if round_num not in tournament.round_results:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} has no submissions',
                'user_message': f'Round {round_num} has no submitted tables yet.',
                'suggestion': 'Use Submit Table Results for new submissions.'
            }), 400
        
        submitted_tables = tournament.round_results[round_num].get('submitted_tables', set())
        if table_name not in submitted_tables:
            return jsonify({
                'success': False,
                'error': f'{table_name} not in submitted tables',
                'user_message': f'{table_name} has not been submitted yet.',
                'suggestion': 'Use Submit Table Results for new submissions, not Edit.'
            }), 400
        
        # 6. Validate results array
        new_results = data.get('results', [])
        if not isinstance(new_results, list):
            return jsonify({
                'success': False,
                'error': f'Results must be a list, got {type(new_results).__name__}',
                'user_message': 'Invalid results format.',
                'suggestion': 'Results must be an array of player scores.'
            }), 400
        
        if len(new_results) != 4:
            return jsonify({
                'success': False,
                'error': f'Expected 4 player results, got {len(new_results)}',
                'user_message': 'Each table must have exactly 4 player scores.',
                'suggestion': 'Please provide scores for all 4 players at the table.'
            }), 400
        
        # 7. Validate each player result
        for idx, result in enumerate(new_results):
            if not isinstance(result, dict):
                return jsonify({
                    'success': False,
                    'error': f'Result {idx} must be an object',
                    'user_message': f'Invalid format for player {idx + 1}.',
                    'suggestion': 'Each result must have player_id and points fields.'
                }), 400
            
            if 'player_id' not in result:
                return jsonify({
                    'success': False,
                    'error': f'Result {idx} missing player_id',
                    'user_message': f'Player {idx + 1} is missing player ID.',
                    'suggestion': 'Each result must include player_id.'
                }), 400
            
            if 'points' not in result:
                return jsonify({
                    'success': False,
                    'error': f'Result {idx} missing points',
                    'user_message': f'Player {idx + 1} is missing points.',
                    'suggestion': 'Each result must include points (0, 1, or 5).'
                }), 400
            
            player_id = result['player_id']
            if not isinstance(player_id, int):
                return jsonify({
                    'success': False,
                    'error': f'player_id must be int, got {type(player_id).__name__}',
                    'user_message': 'Invalid player ID format.',
                    'suggestion': 'Player ID must be a number.'
                }), 400
            
            if player_id not in tournament.player_scores:
                return jsonify({
                    'success': False,
                    'error': f'Player ID {player_id} not found',
                    'user_message': f'Player ID {player_id} does not exist.',
                    'suggestion': 'Please check the player ID is correct.'
                }), 400
            
            points = result['points']
            if points not in [0, 1, 5]:
                return jsonify({
                    'success': False,
                    'error': f'Invalid points value: {points}',
                    'user_message': f'Invalid points: {points}. Must be 0 (Loss), 1 (Draw), or 5 (Win).',
                    'suggestion': 'Use W=5, D=1, L=0 for scoring.'
                }), 400
        
        # ========================================
        # PROCESSING BLOCK
        # ========================================
        
        # Store original state for potential rollback
        original_player_scores = tournament.player_scores.copy()
        original_team_scores = tournament.scores.copy()
        
        try:
            # Get old results
            old_results = tournament.round_results[round_num]['table_submissions'].get(table_name, [])
            
            # Initialize score history if needed
            if 'score_history' not in tournament.round_results[round_num]:
                tournament.round_results[round_num]['score_history'] = {}
            
            if table_name not in tournament.round_results[round_num]['score_history']:
                tournament.round_results[round_num]['score_history'][table_name] = []
            
            # Store edit in history
            edit_entry = {
                'timestamp': datetime.now().isoformat(),
                'old_results': old_results,
                'new_results': new_results,
                'reason': data.get('reason', 'No reason provided'),
                'editor_ip': request.remote_addr
            }
            tournament.round_results[round_num]['score_history'][table_name].append(edit_entry)
            
            # Subtract old scores from player totals
            for result in old_results:
                player_id = result['player_id']
                points = result['points']
                if player_id in tournament.player_scores:
                    tournament.player_scores[player_id] -= points
                    print(f"  [EDIT] Subtracting old score: Player {player_id} -= {points}")
            
            # Add new scores to player totals
            for result in new_results:
                player_id = result['player_id']
                points = result['points']
                if player_id in tournament.player_scores:
                    tournament.player_scores[player_id] += points
                    print(f"  [EDIT] Adding new score: Player {player_id} += {points}")
            
            # Update stored results
            tournament.round_results[round_num]['table_submissions'][table_name] = new_results
            
            # Recalculate team scores
            tournament.calculate_team_scores()
            
            # Handle final round scoring if applicable
            if round_num == tournament.max_rounds:
                tournament.update_final_round_scores(round_num, new_results)
            
            print(f"[OK] Table {table_name} results edited for round {round_num}")
            
            edit_count = len(tournament.round_results[round_num]['score_history'][table_name])
            
            return jsonify({
                'success': True,
                'message': f'Results updated for {table_name}',
                'table': table_name,
                'round': round_num,
                'scores': tournament.scores,
                'player_scores': tournament.player_scores,
                'edit_count': edit_count,
                'previous_results': old_results
            })
            
        except Exception as inner_error:
            # Rollback on error
            tournament.player_scores = original_player_scores
            tournament.scores = original_team_scores
            print(f"[ROLLBACK] Restored original scores due to error: {inner_error}")
            raise
    
    except Exception as e:
        print(f"[ERROR] edit_table_results failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'user_message': 'An unexpected error occurred while editing scores.',
            'suggestion': 'Please try again. If the problem persists, contact support.'
        }), 500
```

---

### Step 3: Create `/get_score_history` Endpoint

**File:** `tournament_dashboard.py`
**Location:** After `/edit_table_results` endpoint

```python
@app.route('/get_score_history/<int:round_num>/<table_name>')
def get_score_history(round_num, table_name):
    """Get edit history for a specific table."""
    try:
        # Decode table name (handles URL encoding)
        from urllib.parse import unquote
        table_name = unquote(table_name)
        
        if round_num not in tournament.round_results:
            return jsonify({
                'success': False,
                'error': 'Round not found',
                'user_message': f'Round {round_num} does not exist.',
                'suggestion': 'Please check the round number.'
            }), 404
        
        history = tournament.round_results[round_num].get('score_history', {}).get(table_name, [])
        
        return jsonify({
            'success': True,
            'table': table_name,
            'round': round_num,
            'edit_count': len(history),
            'history': history,
            'has_edits': len(history) > 0
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Failed to retrieve score history.',
            'suggestion': 'Please try again.'
        }), 500
```

---

### Step 4: Add Frontend Edit UI

**File:** `templates/dashboard_ultra_modern.html`

#### 4.1 Add CSS Styles (around line 2160, after existing submission progress CSS)

```css
/* Score Editing Styles */
.edit-scores-btn {
    background: linear-gradient(135deg, #f6ad55 0%, #ed8936 100%);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    margin-left: 10px;
    transition: all 0.3s ease;
}

.edit-scores-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(237, 137, 54, 0.4);
}

.cancel-edit-btn {
    background: linear-gradient(135deg, #718096 0%, #4a5568 100%);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    margin-left: 10px;
    transition: all 0.3s ease;
}

.cancel-edit-btn:hover {
    background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
}

.table-card.editing {
    border: 2px solid #f6ad55;
    box-shadow: 0 0 20px rgba(246, 173, 85, 0.3);
}

.edit-history-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    background: rgba(246, 173, 85, 0.2);
    color: #f6ad55;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 8px;
}

/* Score History Modal */
.history-modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
}

.history-modal.show {
    opacity: 1;
    visibility: visible;
}

.history-modal-content {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px;
    padding: 24px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.history-entry {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 3px solid #f6ad55;
}

.history-entry-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: 13px;
    color: #a0aec0;
}

.history-entry-reason {
    font-style: italic;
    color: #cbd5e0;
    margin-bottom: 12px;
}

.history-scores {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.history-scores-before,
.history-scores-after {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    padding: 10px;
}

.history-scores-before h5 {
    color: #fc8181;
    margin-bottom: 8px;
}

.history-scores-after h5 {
    color: #68d391;
    margin-bottom: 8px;
}
```

#### 4.2 Add JavaScript Functions (around line 3900, after existing submission functions)

```javascript
// ============================================
// SCORE EDITING FUNCTIONS (Task 3.2)
// ============================================

// Add edit button to submitted tables
function addEditButtonToSubmittedTables(roundNum) {
    const tableCards = document.querySelectorAll('.table-card');
    tableCards.forEach(card => {
        const submitBtn = card.querySelector('.submit-table-btn');
        if (submitBtn && submitBtn.classList.contains('submitted')) {
            const tableName = card.id.replace('table-', '').replace(/-/g, ' ');
            addEditButton(card, tableName, roundNum);
        }
    });
}

function addEditButton(tableCard, tableName, roundNum) {
    // Check if edit button already exists
    if (tableCard.querySelector('.edit-scores-btn')) {
        return;
    }
    
    const submitBtn = tableCard.querySelector('.submit-table-btn');
    if (!submitBtn) return;
    
    const editBtn = document.createElement('button');
    editBtn.className = 'edit-scores-btn';
    editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit Scores';
    editBtn.onclick = (e) => {
        e.stopPropagation();
        enableScoreEditing(tableName, roundNum);
    };
    
    submitBtn.parentElement.appendChild(editBtn);
    
    // Check for edit history and add badge
    checkAndShowEditHistory(tableName, roundNum, tableCard);
}

async function checkAndShowEditHistory(tableName, roundNum, tableCard) {
    try {
        const response = await fetch(`/get_score_history/${roundNum}/${encodeURIComponent(tableName)}`);
        const data = await response.json();
        
        if (data.success && data.edit_count > 0) {
            const header = tableCard.querySelector('.table-header');
            if (header && !header.querySelector('.edit-history-badge')) {
                const badge = document.createElement('span');
                badge.className = 'edit-history-badge';
                badge.innerHTML = `<i class="fas fa-history"></i> ${data.edit_count} edit(s)`;
                badge.onclick = (e) => {
                    e.stopPropagation();
                    viewScoreHistory(tableName, roundNum);
                };
                badge.style.cursor = 'pointer';
                header.appendChild(badge);
            }
        }
    } catch (error) {
        console.error('Failed to check edit history:', error);
    }
}

function enableScoreEditing(tableName, roundNum) {
    const confirmMsg = `You are about to edit scores for ${tableName}.\n\n` +
                      `• The previous scores will be saved in the audit trail\n` +
                      `• Team standings will be recalculated\n` +
                      `• This action can be repeated if needed\n\n` +
                      `Do you want to continue?`;
    
    if (!confirm(confirmMsg)) {
        return;
    }
    
    const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
    if (!tableCard) {
        showToast('Error', 'Table not found', 'error');
        return;
    }
    
    // Add editing visual indicator
    tableCard.classList.add('editing');
    
    // Re-enable score buttons
    const scoreButtons = tableCard.querySelectorAll('.score-btn');
    scoreButtons.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('disabled');
    });
    
    // Remove lock icons
    const lockIcons = tableCard.querySelectorAll('.lock-icon');
    lockIcons.forEach(icon => icon.remove());
    
    // Change submit button to "Update Scores"
    const submitBtn = tableCard.querySelector('.submit-table-btn');
    submitBtn.disabled = false;
    submitBtn.classList.remove('submitted');
    submitBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
    submitBtn.onclick = () => updateTableScores(tableName, roundNum);
    
    // Hide edit button during editing
    const editBtn = tableCard.querySelector('.edit-scores-btn');
    if (editBtn) editBtn.style.display = 'none';
    
    // Add cancel button
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'cancel-edit-btn';
    cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
    cancelBtn.onclick = () => cancelScoreEditing(tableName, roundNum);
    submitBtn.parentElement.appendChild(cancelBtn);
    
    // Clear any previous score selections for this table
    if (tableScores[tableName]) {
        delete tableScores[tableName];
    }
    
    showToast('Edit Mode', `You can now edit scores for ${tableName}. Select new scores and click Update.`, 'info');
}

async function updateTableScores(tableName, roundNum) {
    // Validate all players have scores
    const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
    const playerElements = tableCard.querySelectorAll('.table-player');
    
    if (!tableScores[tableName] || Object.keys(tableScores[tableName]).length !== playerElements.length) {
        showToast('Incomplete', 'Please select scores for all players before updating.', 'warning');
        return;
    }
    
    // Build results array
    const results = [];
    for (const playerId in tableScores[tableName]) {
        results.push({
            player_id: parseInt(playerId),
            points: tableScores[tableName][playerId]
        });
    }
    
    // Ask for edit reason
    const reason = prompt('(Optional) Please provide a reason for this edit:', '');
    
    const updateBtn = tableCard.querySelector('.submit-table-btn');
    updateBtn.disabled = true;
    updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    
    try {
        const response = await fetch('/edit_table_results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                round: roundNum,
                table: tableName,
                results: results,
                reason: reason || 'Score correction'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Scores Updated!', `${tableName} scores have been updated successfully.`, 'success');
            
            // Remove editing state
            tableCard.classList.remove('editing');
            
            // Restore submitted state
            markTableAsSubmitted(tableName, roundNum);
            
            // Remove cancel button
            const cancelBtn = tableCard.querySelector('.cancel-edit-btn');
            if (cancelBtn) cancelBtn.remove();
            
            // Show edit button again
            const editBtn = tableCard.querySelector('.edit-scores-btn');
            if (editBtn) editBtn.style.display = '';
            
            // Add/update edit history badge
            checkAndShowEditHistory(tableName, roundNum, tableCard);
            
            // Refresh team scores display
            refreshTeamScores();
            
            if (data.edit_count > 0) {
                showToast('Edit History', `This table has been edited ${data.edit_count} time(s). Click the badge to view history.`, 'info');
            }
        } else {
            showToast('Error', data.user_message || data.error || 'Failed to update scores', 'error');
            updateBtn.disabled = false;
            updateBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
        }
    } catch (error) {
        showToast('Network Error', 'Failed to connect to server. Please try again.', 'error');
        console.error('Update scores error:', error);
        updateBtn.disabled = false;
        updateBtn.innerHTML = '<i class="fas fa-save"></i> Update Scores';
    }
}

function cancelScoreEditing(tableName, roundNum) {
    const tableCard = document.getElementById(`table-${tableName.replace(/\s+/g, '-')}`);
    
    // Remove editing state
    tableCard.classList.remove('editing');
    
    // Clear score selections
    if (tableScores[tableName]) {
        delete tableScores[tableName];
    }
    
    // Remove cancel button
    const cancelBtn = tableCard.querySelector('.cancel-edit-btn');
    if (cancelBtn) cancelBtn.remove();
    
    // Show edit button again
    const editBtn = tableCard.querySelector('.edit-scores-btn');
    if (editBtn) editBtn.style.display = '';
    
    // Restore submitted state (re-fetch to get correct data)
    const currentRound = document.getElementById('round-select').value;
    loadRound();
    
    showToast('Cancelled', 'Score editing cancelled. Original scores restored.', 'info');
}

async function viewScoreHistory(tableName, roundNum) {
    try {
        const response = await fetch(`/get_score_history/${roundNum}/${encodeURIComponent(tableName)}`);
        const data = await response.json();
        
        if (data.success && data.edit_count > 0) {
            showHistoryModal(tableName, roundNum, data.history);
        } else {
            showToast('No History', 'This table has not been edited.', 'info');
        }
    } catch (error) {
        showToast('Error', 'Failed to load score history.', 'error');
        console.error('Score history error:', error);
    }
}

function showHistoryModal(tableName, roundNum, history) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('history-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'history-modal';
        modal.className = 'history-modal';
        modal.innerHTML = `
            <div class="history-modal-content">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 id="history-modal-title" style="margin: 0; color: #fff;"></h3>
                    <button onclick="closeHistoryModal()" style="background: none; border: none; color: #fff; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div id="history-modal-body"></div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeHistoryModal();
        });
    }
    
    // Populate modal content
    document.getElementById('history-modal-title').textContent = `Score History: ${tableName} (Round ${roundNum})`;
    
    let bodyHTML = `<p style="color: #a0aec0; margin-bottom: 16px;">Total edits: ${history.length}</p>`;
    
    history.forEach((entry, index) => {
        const timestamp = new Date(entry.timestamp).toLocaleString();
        bodyHTML += `
            <div class="history-entry">
                <div class="history-entry-header">
                    <span><strong>Edit #${index + 1}</strong></span>
                    <span>${timestamp}</span>
                </div>
                ${entry.reason ? `<div class="history-entry-reason">"${entry.reason}"</div>` : ''}
                <div class="history-scores">
                    <div class="history-scores-before">
                        <h5>Before</h5>
                        ${formatScoresForHistory(entry.old_results)}
                    </div>
                    <div class="history-scores-after">
                        <h5>After</h5>
                        ${formatScoresForHistory(entry.new_results)}
                    </div>
                </div>
            </div>
        `;
    });
    
    document.getElementById('history-modal-body').innerHTML = bodyHTML;
    
    // Show modal
    modal.classList.add('show');
}

function formatScoresForHistory(results) {
    if (!results || results.length === 0) return '<p>No data</p>';
    
    return results.map(r => {
        const pointsLabel = r.points === 5 ? 'Win' : (r.points === 1 ? 'Draw' : 'Loss');
        return `<div style="font-size: 12px; margin: 4px 0;">Player ${r.player_id}: ${r.points} pts (${pointsLabel})</div>`;
    }).join('');
}

function closeHistoryModal() {
    const modal = document.getElementById('history-modal');
    if (modal) modal.classList.remove('show');
}
```

#### 4.3 Integration Point

**In `markTableAsSubmitted()` function** (around line 3610), add call to show edit button:

```javascript
// At the end of markTableAsSubmitted():
const currentRound = parseInt(document.getElementById('round-select').value);
addEditButton(tableCard, tableName, currentRound);
```

**In `loadRound()` function** (after displayTables call), add:

```javascript
// After displayTables(data.tables, round):
setTimeout(() => {
    addEditButtonToSubmittedTables(parseInt(round));
}, 500);
```

---

## Verification Plan

### Automated Tests

**File:** `test_tournament_comprehensive.py`

Add the following test cases:

```python
def test_edit_table_results_success(self):
    """Test editing table results successfully."""
    # Setup: Submit initial results
    initial_results = [
        {'player_id': 1, 'points': 5},
        {'player_id': 2, 'points': 0},
        {'player_id': 3, 'points': 1},
        {'player_id': 4, 'points': 0}
    ]
    # Submit initial
    response = self.client.post('/submit_table_results', json={
        'round': 1,
        'table': 'Table 1',
        'results': initial_results
    })
    assert response.json['success'] == True
    
    # Edit: Change player 1 from win to loss, player 2 from loss to win
    new_results = [
        {'player_id': 1, 'points': 0},
        {'player_id': 2, 'points': 5},
        {'player_id': 3, 'points': 1},
        {'player_id': 4, 'points': 0}
    ]
    response = self.client.post('/edit_table_results', json={
        'round': 1,
        'table': 'Table 1',
        'results': new_results,
        'reason': 'Test correction'
    })
    assert response.json['success'] == True
    assert response.json['edit_count'] == 1
    
def test_edit_finalized_round_fails(self):
    """Test that editing finalized rounds is rejected."""
    # Finalize round
    tournament.finalized_rounds.add(1)
    
    response = self.client.post('/edit_table_results', json={
        'round': 1,
        'table': 'Table 1',
        'results': [...]
    })
    assert response.json['success'] == False
    assert 'finalized' in response.json['error'].lower()

def test_edit_unsubmitted_table_fails(self):
    """Test that editing unsubmitted tables is rejected."""
    response = self.client.post('/edit_table_results', json={
        'round': 1,
        'table': 'Table 99',
        'results': [...]
    })
    assert response.json['success'] == False

def test_score_history_tracking(self):
    """Test that edit history is properly tracked."""
    # Submit, edit, check history
    # ...
    response = self.client.get('/get_score_history/1/Table%201')
    assert response.json['success'] == True
    assert response.json['edit_count'] == 1
    assert len(response.json['history']) == 1
```

**Run tests with:**
```bash
python -X utf8 test_tournament_comprehensive.py --teams 8 --verbose
python -X utf8 test_tournament_comprehensive.py --teams 16 --verbose
```

### Manual Testing Checklist

1. **Submit Initial Scores:**
   - [ ] Load participants
   - [ ] Setup tournament
   - [ ] Submit scores for Table 1 (Player 1: Win, others: Loss)
   - [ ] Verify "Edit Scores" button appears

2. **Edit Scores:**
   - [ ] Click "Edit Scores" button
   - [ ] Verify confirmation dialog appears
   - [ ] Click OK to enter edit mode
   - [ ] Verify score buttons are re-enabled
   - [ ] Verify table has orange border (editing indicator)
   - [ ] Select new scores (Player 2: Win, Player 1: Loss)
   - [ ] Click "Update Scores"
   - [ ] Verify prompt for edit reason
   - [ ] Enter reason and confirm
   - [ ] Verify success toast message
   - [ ] Verify team scores updated in standings

3. **Cancel Editing:**
   - [ ] Click "Edit Scores" on another table
   - [ ] Click "Cancel" button
   - [ ] Verify scores not changed
   - [ ] Verify table restored to submitted state

4. **View History:**
   - [ ] Verify edit badge appears on edited table
   - [ ] Click edit badge
   - [ ] Verify history modal shows with correct data
   - [ ] Verify before/after scores displayed
   - [ ] Verify timestamp and reason shown
   - [ ] Close modal

5. **Finalized Round Protection:**
   - [ ] Finalize a round (submit all tables + finalize)
   - [ ] Attempt to edit a table in finalized round
   - [ ] Verify error message appears

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Score corruption | Medium | High | Rollback on error, validation |
| Audit trail gaps | Low | Medium | Comprehensive logging |
| UI confusion | Medium | Low | Clear visual indicators |
| State machine conflicts | Low | High | @require_state decorator |

---

## Files to Modify

| File | Changes |
|------|---------|
| `tournament_dashboard.py` | Add 2 endpoints (~150 LOC) |
| `templates/dashboard_ultra_modern.html` | Add CSS (~80 LOC) + JS (~250 LOC) |
| `test_tournament_comprehensive.py` | Add test cases (~50 LOC) |

---

## Implementation Checklist

- [ ] Add score history tracking structure to TournamentManager
- [ ] Create `/edit_table_results` endpoint with full validation
- [ ] Create `/get_score_history` endpoint
- [ ] Add @require_state decorator to edit endpoint
- [ ] Add CSS styles for edit UI
- [ ] Add JavaScript functions for edit flow
- [ ] Add history modal
- [ ] Integrate edit buttons into existing table display
- [ ] Add automated tests
- [ ] Manual testing complete
- [ ] Update PHASE-2-3-SUMMARY.md to mark complete
- [ ] Update CLAUDE.md with new endpoint documentation

---

## Success Criteria

- [ ] Submitted tables show "Edit Scores" button
- [ ] Clicking edit shows confirmation dialog
- [ ] Score buttons re-enable during edit mode
- [ ] Cancel restores original state
- [ ] Update saves new scores and updates standings
- [ ] Edit history is tracked with timestamps
- [ ] History can be viewed in modal
- [ ] Finalized rounds cannot be edited
- [ ] All existing tests still pass
- [ ] No score corruption occurs

---

**End of Implementation Plan**
