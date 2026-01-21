# Japanese Swiss Point Mode - Implementation Guide

> **Status**: Implementation Complete ✅  
> **Created**: January 17, 2026  
> **Last Updated**: January 17, 2026

This document provides a complete implementation guide for adding the Japanese Swiss Point Mode to the MTG Tournament Dashboard. This scoring system is an alternative to the traditional Western 5/1/0 point system.

---

## Table of Contents

1. [Overview](#overview)
2. [Scoring System Comparison](#scoring-system-comparison)
3. [Implementation Details](#implementation-details)
   - [Backend Changes](#backend-changes)
   - [Frontend Changes](#frontend-changes)
   - [API Endpoints](#api-endpoints)
4. [Code Examples](#code-examples)
5. [Testing Checklist](#testing-checklist)
6. [File Modification Summary](#file-modification-summary)

---

## Overview

### What is Japanese Swiss Point Mode?

In this scoring mode:
- Every player starts with **1000 points**
- Each round, every player contributes **7% of their current points** to a table pool
- The **winner takes the entire pool**
- **Losers and draws** lose their contributed 7% (no compensation)
- Points accumulate throughout the tournament (never reset)
- Team score = Sum of all team members' points

### Why This Mode?

- Creates larger point differentials between consistent winners and losers
- Winner-takes-all creates higher stakes per round
- Mathematically, points can never reach 0 (7% of any positive number stays positive)
- More dramatic scoring for spectators

---

## Scoring System Comparison

| Aspect | Western Mode (Current) | Japanese Mode (New) |
|--------|------------------------|---------------------|
| Starting Points | 0 per player | 1000 per player |
| Win | +5 points | Takes pool (~28% of table total) |
| Draw | +1 point each | All lose their 7% contribution |
| Loss | 0 points | Loses 7% contribution |
| Team Score Calculation | Sum of player points | Sum of player points |
| Point Range (4 rounds) | 0-20 points | ~650-1800+ points |

### Mathematical Example

**Round 1 Setup:**
- 4 players, each with 1000 points
- Each contributes: `round(1000 × 0.07) = 70 points`
- Pool total: `70 × 4 = 280 points`

**After Round 1:**
- Winner: `1000 - 70 + 280 = 1210 points` (+210 net)
- Losers: `1000 - 70 = 930 points` (-70 net)

**Round 2 Example (varied starting points):**
- Player A: 1210 points → contributes `round(1210 × 0.07) = 85 points`
- Player B: 930 points → contributes `round(930 × 0.07) = 65 points`
- Player C: 1050 points → contributes `round(1050 × 0.07) = 74 points`
- Player D: 980 points → contributes `round(980 × 0.07) = 69 points`
- Pool total: `85 + 65 + 74 + 69 = 293 points`

---

## Implementation Status

### Backend (COMPLETED ✅)

All backend components have been implemented in `tournament_dashboard.py`:

| Component | Status | Line Numbers |
|-----------|--------|--------------|
| `ScoringMode` enum | ✅ Implemented | ~36-39 |
| `TournamentManager.__init__` scoring vars | ✅ Implemented | ~83-86 |
| `set_scoring_mode()` method | ✅ Implemented | ~367-395 |
| `setup_tournament()` Japanese init | ✅ Implemented | ~724-740 |
| `calculate_japanese_table_scores()` | ✅ Implemented | ~1129-1192 |
| `get_table_winner_id()` | ✅ Implemented | ~1194-1214 |
| `save_state()` scoring mode | ✅ Implemented | ~152 |
| `load_state()` scoring mode | ✅ Implemented | ~228-236 |
| `submit_table_results` Japanese logic | ✅ Implemented | ~2765-2800 |
| `/set_scoring_mode` endpoint | ✅ Implemented | ~2299-2329 |
| `/get_tournament_state` response | ✅ Implemented | ~3219-3220 |
| `/load_data` response | ✅ Implemented | ~2191 |

### Frontend (COMPLETED ✅)

All frontend components have been implemented:

| Component | Status | File |
|-----------|--------|------|
| Mode selection modal | ✅ Implemented | `dashboard_ultra_modern.html` |
| Score display formatting | ✅ Implemented | `dashboard_ultra_modern.html` |
| Japanese mode badge | ✅ Implemented | `dashboard_ultra_modern.html`, `projector_view.html` |
| Projector view updates | ✅ Implemented | `projector_view.html` |

---

## Implementation Details

### Backend Changes (COMPLETED)

#### 1. Add Scoring Mode Enum

**File:** `tournament_dashboard.py`  
**Location:** Near line 24 (after `TournamentState` enum)

```python
class ScoringMode(Enum):
    """Enum representing the scoring calculation mode."""
    WESTERN = "western"      # Traditional 5/1/0 point system
    JAPANESE = "japanese"    # 7% pool contribution system
```

---

#### 2. Update TournamentManager.__init__

**File:** `tournament_dashboard.py`  
**Location:** Lines 42-77

Add these new instance variables:

```python
def __init__(self):
    # ... existing code ...
    
    # Scoring mode configuration (NEW)
    self.scoring_mode = ScoringMode.WESTERN  # Default to Western mode
    self.japanese_starting_points = 1000     # Starting points for Japanese mode
    self.japanese_pool_percentage = 0.07     # 7% pool contribution
```

---

#### 3. Add set_scoring_mode Method

**File:** `tournament_dashboard.py`  
**Location:** After `configure_swiss_rounds` method (~line 356)

```python
def set_scoring_mode(self, mode: str) -> tuple:
    """
    Set the scoring mode before tournament setup.
    Must be called after participants are loaded but before setup_tournament().
    
    Args:
        mode: "western" or "japanese"
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate state - can only set mode before tournament starts
    if self.state not in [TournamentState.INITIAL, TournamentState.PARTICIPANTS_LOADED]:
        return False, "Cannot change scoring mode after tournament has started"
    
    # Validate mode value
    mode_lower = mode.lower()
    if mode_lower == "western":
        self.scoring_mode = ScoringMode.WESTERN
        print(f"[CONFIG] Scoring mode set to: WESTERN (5/1/0 points)")
        return True, "Scoring mode set to Western (5/1/0 point system)"
    elif mode_lower == "japanese":
        self.scoring_mode = ScoringMode.JAPANESE
        print(f"[CONFIG] Scoring mode set to: JAPANESE (7% pool system)")
        return True, "Scoring mode set to Japanese (7% pool system, 1000 starting points)"
    else:
        return False, f"Invalid scoring mode: {mode}. Use 'western' or 'japanese'"
```

---

#### 4. Modify setup_tournament Method

**File:** `tournament_dashboard.py`  
**Location:** In `setup_tournament` method (~line 686-689)

Replace this:
```python
self.player_scores = {}
for participant in self.participants:
    player_id = participant.get('Player ID')
    self.player_scores[player_id] = 0
```

With this:
```python
self.player_scores = {}
for participant in self.participants:
    player_id = participant.get('Player ID')
    if self.scoring_mode == ScoringMode.JAPANESE:
        self.player_scores[player_id] = self.japanese_starting_points  # 1000
    else:
        self.player_scores[player_id] = 0  # Western mode

if self.scoring_mode == ScoringMode.JAPANESE:
    print(f"[JAPANESE MODE] All {len(self.player_scores)} players initialized with {self.japanese_starting_points} points")
```

---

#### 5. Add Japanese Scoring Calculation Method

**File:** `tournament_dashboard.py`  
**Location:** After `calculate_team_scores` method (~line 1077)

```python
def calculate_japanese_table_scores(self, table_players: list, winner_id: int = None) -> dict:
    """
    Calculate scores for a table using Japanese Swiss Point rules.
    
    Args:
        table_players: List of player dicts at the table
        winner_id: Player ID of the winner (None = draw)
    
    Returns:
        dict: {player_id: points_change} for each player
    
    Rules:
    1. Each player contributes 7% (rounded) of their current points to the pool
    2. Winner takes entire pool (net gain = pool - their contribution)
    3. Losers/Draw participants lose their contribution (net loss = -contribution)
    """
    result = {}
    pool = 0
    contributions = {}
    
    # Step 1: Calculate each player's contribution
    for player in table_players:
        player_id = player['Player ID']
        current_points = self.player_scores.get(player_id, self.japanese_starting_points)
        contribution = round(current_points * self.japanese_pool_percentage)
        contributions[player_id] = contribution
        pool += contribution
    
    # Step 2: Distribute points
    for player in table_players:
        player_id = player['Player ID']
        contribution = contributions[player_id]
        
        if winner_id is not None and player_id == winner_id:
            # Winner: loses contribution but gains entire pool
            net_change = pool - contribution
            result[player_id] = net_change
        else:
            # Loser or Draw: just loses contribution
            result[player_id] = -contribution
    
    # Log for debugging
    player_names = {p['Player ID']: p['Player Name'] for p in table_players}
    print(f"[JAPANESE] Pool: {pool} pts | Contributions: " + 
          ", ".join([f"{player_names[pid]}: {c}" for pid, c in contributions.items()]))
    if winner_id:
        print(f"[JAPANESE] Winner: {player_names.get(winner_id, 'Unknown')} takes pool")
    else:
        print(f"[JAPANESE] DRAW: All players lose their contribution")
    
    return result


def is_table_result_a_draw(self, table_results: list) -> bool:
    """
    Determine if a table result is a draw.
    
    A draw occurs when:
    - 0 winners (all draws/losses)
    - 2+ winners (treated as draw per rules)
    
    Args:
        table_results: List of {player_id, points} dicts
    
    Returns:
        bool: True if this is a draw scenario
    """
    # In Western mode, 5 points = win, 1 point = draw, 0 = loss
    # In Japanese mode, we need to determine winner from results
    winners = [r for r in table_results if r.get('points') == 5 or r.get('is_winner', False)]
    return len(winners) != 1
```

---

#### 6. Modify Score Submission Handling

**File:** `tournament_dashboard.py`  
**Location:** In the endpoint that handles table result submission

When processing table results, check the scoring mode:

```python
# In the score submission logic:

if tournament.scoring_mode == ScoringMode.JAPANESE:
    # Get table players
    table_players = tournament.tables[round_num][table_name]
    
    # Determine winner (player with "Win" result)
    winner_id = None
    win_count = 0
    for result in table_results:
        if result.get('points') == 5:  # Win indicator
            win_count += 1
            winner_id = result['player_id']
    
    # If multiple winners, it's a draw
    if win_count != 1:
        winner_id = None
    
    # Calculate Japanese scoring
    score_changes = tournament.calculate_japanese_table_scores(table_players, winner_id)
    
    # Apply score changes
    for player_id, change in score_changes.items():
        tournament.player_scores[player_id] += change
else:
    # Western mode: Use existing 5/1/0 logic
    for result in table_results:
        player_id = result['player_id']
        points = result['points']
        tournament.player_scores[player_id] += points
```

---

#### 7. Update State Persistence

**File:** `tournament_dashboard.py`

**In `save_state` method (~line 160):**
```python
# Add to the state dict being saved:
"scoring_mode": self.scoring_mode.value,  # Save as string "western" or "japanese"
```

**In `load_state` method (~line 268):**
```python
# Restore scoring mode (with backward compatibility)
scoring_mode_str = data.get('scoring_mode', 'western')
if scoring_mode_str == 'japanese':
    self.scoring_mode = ScoringMode.JAPANESE
else:
    self.scoring_mode = ScoringMode.WESTERN
```

---

### Frontend Changes (COMPLETED)

#### 1. Mode Selection Modal

**File:** `templates/dashboard_ultra_modern.html`

Add a modal that appears after participants are loaded:

```html
<!-- Scoring Mode Selection Modal -->
<div id="scoring-mode-modal" class="modal" style="display: none;">
    <div class="modal-content">
        <h2>Select Scoring Mode</h2>
        <p>Choose how points will be calculated in this tournament:</p>
        
        <div class="mode-selection-grid">
            <div class="mode-card" data-mode="western" onclick="selectScoringMode('western')">
                <h3>🏆 Western Mode</h3>
                <p><strong>Traditional Scoring</strong></p>
                <ul>
                    <li>Win: +5 points</li>
                    <li>Draw: +1 point</li>
                    <li>Loss: 0 points</li>
                </ul>
                <p class="mode-description">Standard cEDH tournament scoring</p>
            </div>
            
            <div class="mode-card" data-mode="japanese" onclick="selectScoringMode('japanese')">
                <h3>🎌 Japanese Mode</h3>
                <p><strong>Pool-Based Scoring</strong></p>
                <ul>
                    <li>Start: 1000 points</li>
                    <li>Each round: Contribute 7% to pool</li>
                    <li>Winner takes entire pool</li>
                </ul>
                <p class="mode-description">High-stakes winner-takes-all format</p>
            </div>
        </div>
        
        <button id="confirm-mode-btn" onclick="confirmScoringMode()" disabled>
            Confirm Selection
        </button>
    </div>
</div>
```

**JavaScript for mode selection:**
```javascript
let selectedScoringMode = null;

function selectScoringMode(mode) {
    selectedScoringMode = mode;
    
    // Update UI to show selection
    document.querySelectorAll('.mode-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('selected');
    
    // Enable confirm button
    document.getElementById('confirm-mode-btn').disabled = false;
}

async function confirmScoringMode() {
    if (!selectedScoringMode) return;
    
    try {
        const response = await fetch('/set_scoring_mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: selectedScoringMode })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Hide modal
            document.getElementById('scoring-mode-modal').style.display = 'none';
            
            // Show success toast
            showToast(data.message, 'success');
            
            // Enable "Setup Tournament" button
            document.getElementById('setup-tournament-btn').disabled = false;
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('Error setting scoring mode', 'error');
    }
}
```

---

#### 2. Update Player Score Display

For Japanese mode, display scores with proper formatting:

```javascript
function formatPlayerScore(score, mode) {
    if (mode === 'japanese') {
        return score.toLocaleString() + ' pts';  // "1,210 pts"
    } else {
        return score + ' pts';  // "15 pts"
    }
}
```

---

#### 3. Table Submission Preview (Japanese Mode)

Before submitting a table, show the point calculation:

```javascript
function showJapaneseSubmissionPreview(tablePlayers, winnerId) {
    let pool = 0;
    const contributions = {};
    
    tablePlayers.forEach(player => {
        const contribution = Math.round(player.currentPoints * 0.07);
        contributions[player.id] = contribution;
        pool += contribution;
    });
    
    let preview = `Pool Total: ${pool} points\n\n`;
    
    tablePlayers.forEach(player => {
        const contrib = contributions[player.id];
        if (player.id === winnerId) {
            const netGain = pool - contrib;
            preview += `${player.name}: +${netGain} pts (wins pool)\n`;
        } else {
            preview += `${player.name}: -${contrib} pts\n`;
        }
    });
    
    return preview;
}
```

---

### API Endpoints

#### New Endpoint: POST /set_scoring_mode

```python
@app.route('/set_scoring_mode', methods=['POST'])
def set_scoring_mode():
    """Set scoring mode before tournament setup."""
    try:
        data = request.json
        mode = data.get('mode', 'western')
        
        with state_lock:
            success, message = tournament.set_scoring_mode(mode)
        
        return jsonify({
            'success': success,
            'message': message,
            'scoring_mode': tournament.scoring_mode.value
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

#### Update: GET /get_tournament_state

Add scoring mode to the response:

```python
# In get_tournament_state endpoint, add:
'scoring_mode': tournament.scoring_mode.value,
'japanese_mode_active': tournament.scoring_mode == ScoringMode.JAPANESE,
```

---

## Testing Checklist

### Unit Tests
- [ ] `calculate_japanese_table_scores` returns correct values for win scenario
- [ ] `calculate_japanese_table_scores` returns correct values for draw scenario
- [ ] 7% rounding works correctly for edge cases (e.g., 973 points)
- [ ] `set_scoring_mode` rejects changes after tournament starts

### Integration Tests
- [ ] Mode selection persists after backup/restore
- [ ] Japanese mode initializes players with 1000 points
- [ ] Team scores correctly sum player Japanese points
- [ ] Western mode unaffected by new code

### E2E Tests
- [ ] Complete tournament in Japanese mode
- [ ] Verify final point totals are mathematically correct
- [ ] Verify projector view displays Japanese points

### Manual Tests
- [ ] Mode selection modal appears after "Load Participants"
- [ ] Cannot see "Setup Tournament" until mode is selected
- [ ] Table submission shows correct point changes
- [ ] Standings update immediately after each table submission

---

## File Modification Summary

| File | Changes |
|------|---------|
| `tournament_dashboard.py` | Add `ScoringMode` enum, update `__init__`, add `set_scoring_mode()`, add `calculate_japanese_table_scores()`, modify `setup_tournament()`, update save/load state, add `/set_scoring_mode` endpoint |
| `templates/dashboard_ultra_modern.html` | Add mode selection modal, update score display formatting, add submission preview for Japanese mode |
| `templates/projector_view.html` | Update score display to handle larger Japanese point values |

---

## Future Enhancements (Optional)

1. **Configurable pool percentage**: Allow admin to set percentage (5%, 7%, 10%)
2. **Starting points configuration**: Allow custom starting points
3. **Mode indicator badge**: Show "Japanese Mode" badge throughout UI
4. **Point history graph**: Visual representation of point changes over rounds
5. **Protection floor**: Optional minimum point threshold (e.g., 100 points)

---

## Contact & Questions

If you have questions about this implementation, refer to:
- `CLAUDE.md` - Main project documentation
- `README.md` - User documentation
- `tests/e2e/README.md` - Testing documentation

---

*This document was created as part of the planning phase for Japanese Swiss Point Mode implementation.*
