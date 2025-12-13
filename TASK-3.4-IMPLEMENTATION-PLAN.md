# Task 3.4: Tournament State Validation - Implementation Plan

**Date:** 2025-12-13
**Estimated Time:** 2-3 hours
**Priority:** High (prevents out-of-sequence operations)

---

## Overview

Implement a state machine to track tournament lifecycle and prevent invalid operations (e.g., submitting scores before setup, generating finals before completing Swiss rounds).

---

## State Machine Design

### States (Enum)

```python
from enum import Enum

class TournamentState(Enum):
    INITIAL = "initial"                    # Server started, no data loaded
    PARTICIPANTS_LOADED = "participants_loaded"  # Participants loaded, not set up
    TOURNAMENT_SETUP = "tournament_setup"  # Tournament initialized, Round 1 ready
    SWISS_IN_PROGRESS = "swiss_in_progress"  # Swiss rounds being played
    SWISS_COMPLETE = "swiss_complete"      # All Swiss rounds completed
    TOP8_IN_PROGRESS = "top8_in_progress"  # Top 8 Cut in progress (16-team only)
    TOP8_COMPLETE = "top8_complete"        # Top 8 Cut completed (16-team only)
    FINALS_IN_PROGRESS = "finals_in_progress"  # Finals round in progress
    FINALS_COMPLETE = "finals_complete"    # Finals completed, champion determined
```

### State Transitions

```
INITIAL
  → load_data → PARTICIPANTS_LOADED

PARTICIPANTS_LOADED
  → setup_tournament → TOURNAMENT_SETUP

TOURNAMENT_SETUP
  → submit_table_results (Round 1) → SWISS_IN_PROGRESS

SWISS_IN_PROGRESS
  → submit_table_results (last Swiss round) → SWISS_COMPLETE

SWISS_COMPLETE
  → generate_top8 (16-team only) → TOP8_IN_PROGRESS
  → generate_finals (8/12-team) → FINALS_IN_PROGRESS

TOP8_IN_PROGRESS
  → submit_table_results (Top 8) → TOP8_COMPLETE

TOP8_COMPLETE
  → generate_finals → FINALS_IN_PROGRESS

FINALS_IN_PROGRESS
  → submit_table_results (Finals) → FINALS_COMPLETE
```

---

## Implementation Steps

### 1. Add State Tracking to TournamentManager

**Location:** `tournament_dashboard.py` (TournamentManager class)

```python
class TournamentManager:
    def __init__(self):
        # ... existing initialization ...
        self.state = TournamentState.INITIAL
        self.state_history = []  # Track state transitions for debugging

    def transition_to(self, new_state: TournamentState, reason: str = ""):
        """Transition to a new state with logging."""
        old_state = self.state
        self.state = new_state
        self.state_history.append({
            'from': old_state.value,
            'to': new_state.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        print(f"[STATE] {old_state.value} → {new_state.value} ({reason})")
```

### 2. Create @require_state Decorator

**Location:** `tournament_dashboard.py` (before Flask routes)

```python
from functools import wraps
from flask import jsonify

def require_state(*allowed_states):
    """Decorator to ensure endpoint is called in valid state."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if tournament.state not in allowed_states:
                allowed_names = [s.value for s in allowed_states]
                return jsonify({
                    'success': False,
                    'error': f'Invalid operation in current state',
                    'user_message': f'Cannot perform this action right now.',
                    'suggestion': f'Current state: {tournament.state.value}. Allowed states: {", ".join(allowed_names)}',
                    'current_state': tournament.state.value,
                    'allowed_states': allowed_names
                }), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 3. Update Existing Methods to Transition States

**load_participants():**
```python
# At end of successful load
tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Participants loaded successfully")
```

**setup_tournament():**
```python
# After Round 1 generation
tournament.transition_to(TournamentState.TOURNAMENT_SETUP, "Tournament setup complete, Round 1 ready")
```

**submit_table_results() / submit_player_results():**
```python
# After first table submission in Round 1
if tournament.state == TournamentState.TOURNAMENT_SETUP:
    tournament.transition_to(TournamentState.SWISS_IN_PROGRESS, "First Swiss round table submitted")

# After completing last Swiss round
if round_num == tournament.swiss_rounds_count and all_tables_submitted:
    tournament.transition_to(TournamentState.SWISS_COMPLETE, f"All {tournament.swiss_rounds_count} Swiss rounds completed")
```

**generate_top8():**
```python
# At start
tournament.transition_to(TournamentState.TOP8_IN_PROGRESS, "Top 8 Cut started")
```

**generate_finals():**
```python
# At start
tournament.transition_to(TournamentState.FINALS_IN_PROGRESS, "Finals round started")

# After finals completion
if finals_submitted:
    tournament.transition_to(TournamentState.FINALS_COMPLETE, "Tournament complete, champion determined")
```

### 4. Apply Decorators to Endpoints

```python
@app.route('/setup_tournament', methods=['POST'])
@require_state(TournamentState.PARTICIPANTS_LOADED, TournamentState.TOURNAMENT_SETUP)
def setup_tournament():
    # ... existing code ...

@app.route('/submit_table_results', methods=['POST'])
@require_state(
    TournamentState.TOURNAMENT_SETUP,
    TournamentState.SWISS_IN_PROGRESS,
    TournamentState.TOP8_IN_PROGRESS,
    TournamentState.FINALS_IN_PROGRESS
)
def submit_table_results():
    # ... existing code ...

@app.route('/generate_finals', methods=['POST'])
@require_state(TournamentState.SWISS_COMPLETE, TournamentState.TOP8_COMPLETE)
def generate_finals():
    # ... existing code ...
```

### 5. Add State Info Endpoint

```python
@app.route('/get_state_info')
def get_state_info():
    """Get current tournament state and valid next actions."""
    valid_actions = []

    if tournament.state == TournamentState.INITIAL:
        valid_actions = ['load_data']
    elif tournament.state == TournamentState.PARTICIPANTS_LOADED:
        valid_actions = ['setup_tournament']
    elif tournament.state == TournamentState.TOURNAMENT_SETUP:
        valid_actions = ['submit_table_results']
    elif tournament.state == TournamentState.SWISS_IN_PROGRESS:
        valid_actions = ['submit_table_results']
    elif tournament.state == TournamentState.SWISS_COMPLETE:
        if tournament.has_semifinals:
            valid_actions = ['generate_top8']
        else:
            valid_actions = ['generate_finals']
    elif tournament.state == TournamentState.TOP8_IN_PROGRESS:
        valid_actions = ['submit_table_results']
    elif tournament.state == TournamentState.TOP8_COMPLETE:
        valid_actions = ['generate_finals']
    elif tournament.state == TournamentState.FINALS_IN_PROGRESS:
        valid_actions = ['submit_table_results']

    return jsonify({
        'success': True,
        'current_state': tournament.state.value,
        'valid_actions': valid_actions,
        'state_history': tournament.state_history[-5:]  # Last 5 transitions
    })
```

### 6. Update reset_tournament()

```python
def reset_tournament(self):
    """Reset tournament state while preserving participants."""
    # ... existing reset logic ...
    self.state = TournamentState.PARTICIPANTS_LOADED
    self.state_history.append({
        'from': 'various',
        'to': TournamentState.PARTICIPANTS_LOADED.value,
        'reason': 'Tournament reset',
        'timestamp': datetime.now().isoformat()
    })
```

---

## Endpoints That Need State Validation

| Endpoint | Allowed States |
|----------|----------------|
| `POST /load_data` | INITIAL, PARTICIPANTS_LOADED (reload) |
| `POST /setup_tournament` | PARTICIPANTS_LOADED, TOURNAMENT_SETUP (re-setup) |
| `POST /setup_round/<N>` | SWISS_IN_PROGRESS, TOP8_IN_PROGRESS, FINALS_IN_PROGRESS |
| `POST /submit_table_results` | TOURNAMENT_SETUP, SWISS_IN_PROGRESS, TOP8_IN_PROGRESS, FINALS_IN_PROGRESS |
| `POST /submit_player_results` | Same as submit_table_results |
| `POST /generate_finals` | SWISS_COMPLETE, TOP8_COMPLETE |
| `GET /get_tournament_state` | Any state (read-only) |
| `GET /get_submission_status/<N>` | Any state (read-only) |

---

## Testing Strategy

### 1. State Transition Tests

```python
def test_state_transitions():
    # Test: Cannot setup before loading
    response = setup_tournament()
    assert response.status_code == 400
    assert "Invalid operation" in response.json['error']

    # Test: Load → Setup → Swiss
    load_data()
    assert tournament.state == TournamentState.PARTICIPANTS_LOADED

    setup_tournament()
    assert tournament.state == TournamentState.TOURNAMENT_SETUP

    submit_table_results(round=1, table="Table 1", results=[...])
    assert tournament.state == TournamentState.SWISS_IN_PROGRESS
```

### 2. Invalid Operation Tests

```python
def test_invalid_operations():
    # Test: Cannot generate finals during Swiss
    tournament.state = TournamentState.SWISS_IN_PROGRESS
    response = generate_finals()
    assert response.status_code == 400
    assert "Invalid operation" in response.json['error']
```

### 3. Integration Tests

Run existing comprehensive test suite to ensure state machine doesn't break workflows.

---

## Error Messages

### User-Friendly Messages

```python
STATE_ERROR_MESSAGES = {
    TournamentState.INITIAL: "Please load participants first.",
    TournamentState.PARTICIPANTS_LOADED: "Please set up the tournament before submitting results.",
    TournamentState.SWISS_IN_PROGRESS: "Complete all Swiss rounds before generating finals.",
    # ... etc
}
```

---

## Backward Compatibility

- New state tracking is additive (no breaking changes)
- Existing endpoints continue to work
- New `/get_state_info` endpoint is optional
- Frontend can ignore state info if not upgraded

---

## Files to Modify

1. **tournament_dashboard.py**
   - Add TournamentState enum (after imports)
   - Update TournamentManager.__init__() (add state tracking)
   - Add transition_to() method
   - Add require_state() decorator
   - Update all state-changing methods
   - Add @require_state decorators to endpoints
   - Add /get_state_info endpoint

2. **test_tournament_comprehensive.py**
   - Add state transition validation tests
   - Verify invalid operations are rejected

3. **PHASE-2-3-SUMMARY.md**
   - Update to show Task 3.4 as complete
   - Document new endpoint and state machine

4. **CLAUDE.md**
   - Add state machine to architecture section
   - Document new endpoint

---

## Implementation Order

1. ✅ Add TournamentState enum
2. ✅ Add state tracking to TournamentManager
3. ✅ Create require_state decorator
4. ✅ Add state transitions to existing methods
5. ✅ Apply decorators to endpoints
6. ✅ Add /get_state_info endpoint
7. ✅ Test with existing test suite
8. ✅ Add state-specific tests
9. ✅ Update documentation

---

## Risk Assessment

**Low Risk:**
- State tracking is read-only for most operations
- Decorator pattern is non-invasive
- Easy to disable if issues arise

**Potential Issues:**
- State may get out of sync if transitions are missed
- Need careful testing of all code paths

**Mitigation:**
- Comprehensive logging of state transitions
- Fallback: Remove decorators if blocking valid operations
- State history for debugging

---

## Success Criteria

- ✅ Cannot submit scores before tournament setup
- ✅ Cannot generate finals before Swiss completion
- ✅ Cannot perform operations out of sequence
- ✅ All existing tests still pass
- ✅ Clear error messages when operations rejected
- ✅ State history available for debugging

---

**End of Implementation Plan**
