# Swiss Rounds Configuration Feature - Implementation Plan

**Created:** 2025-11-09
**Status:** Ready for Implementation
**Priority:** High
**Complexity:** Low-Medium

---

## Overview

Add a configurable Swiss rounds selector to allow tournament organizers to choose between **4 rounds** or **5 rounds** of Swiss before starting the tournament.

### User Story

> As a tournament organizer, I want to be able to choose between 4 or 5 Swiss rounds before loading participants, so that I can adjust the tournament length based on time constraints and the number of teams participating.

---

## Feature Specification

### User Flow

```
1. User opens dashboard (http://localhost:5000)
   ↓
2. NEW: Swiss Rounds Configuration Panel (visible before "Load Participants")
   - Radio buttons: ⚪ 4 Rounds (Default) ⚪ 5 Rounds
   - Helper text explaining each option
   - Visual indication of current selection
   ↓
3. User selects preferred Swiss rounds (4 or 5)
   ↓
4. User clicks "Load Participants"
   - Selection is locked (cannot change after loading)
   - Configuration sent to backend
   ↓
5. User clicks "Setup Tournament"
   - Backend generates selected number of Swiss rounds
   - Finals structure adjusts accordingly
   ↓
6. Tournament proceeds with selected configuration
```

### UI/UX Requirements

**Location:** Top of control panel, above "Load Participants" button

**Visual Design:**
- Glass-morphic card matching existing UI aesthetic
- Clear visual distinction between 4 and 5 round options
- Disabled state after participants loaded (locked configuration)
- Smooth animations on selection change

**States:**
1. **Initial (Before Participants Loaded)**
   - Both options enabled
   - 4 rounds pre-selected (default)
   - Hover effects active

2. **Locked (After Participants Loaded)**
   - Selected option visible but disabled
   - Clear indication that configuration is locked
   - Explanatory text: "Configuration locked after loading participants"

3. **Active Tournament**
   - Shows current round (e.g., "Round 3 of 5")
   - Progress indicator

---

## Implementation Details

### Phase 1: Frontend Changes

#### File: `templates/dashboard_ultra_modern.html`

**1.1 Add Swiss Rounds Configuration UI**

**Location:** Insert after line ~200, before "Load Participants" button

```html
<!-- Swiss Rounds Configuration Panel -->
<div class="config-panel glass-card" id="swiss-config-panel">
    <div class="config-header">
        <i class="fas fa-cog config-icon"></i>
        <h3>Tournament Configuration</h3>
    </div>

    <div class="config-section">
        <label class="config-label">Swiss Rounds</label>
        <p class="config-description">Select the number of Swiss rounds before finals</p>

        <div class="radio-group" id="swiss-rounds-selector">
            <label class="radio-option" data-rounds="4">
                <input type="radio" name="swiss-rounds" value="4" checked>
                <div class="radio-content">
                    <div class="radio-check">
                        <i class="fas fa-check"></i>
                    </div>
                    <div class="radio-details">
                        <span class="radio-title">4 Rounds</span>
                        <span class="radio-subtitle">Standard (2-3 hours)</span>
                    </div>
                </div>
            </label>

            <label class="radio-option" data-rounds="5">
                <input type="radio" name="swiss-rounds" value="5">
                <div class="radio-content">
                    <div class="radio-check">
                        <i class="fas fa-check"></i>
                    </div>
                    <div class="radio-details">
                        <span class="radio-title">5 Rounds</span>
                        <span class="radio-subtitle">Extended (3-4 hours)</span>
                    </div>
                </div>
            </label>
        </div>

        <div class="config-info">
            <i class="fas fa-info-circle"></i>
            <span>Configuration will be locked after loading participants</span>
        </div>
    </div>
</div>
```

**1.2 Add CSS Styles**

**Location:** Insert in `<style>` section

```css
/* Swiss Rounds Configuration Panel */
.config-panel {
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    background: var(--glass-bg);
    backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
}

.config-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
}

.config-icon {
    font-size: 1.5rem;
    color: var(--color-primary);
}

.config-header h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: white;
}

.config-section {
    margin-top: var(--spacing-md);
}

.config-label {
    display: block;
    font-size: 1rem;
    font-weight: 600;
    color: white;
    margin-bottom: var(--spacing-xs);
}

.config-description {
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.7);
    margin-bottom: var(--spacing-md);
}

/* Radio Group */
.radio-group {
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
}

.radio-option {
    flex: 1;
    cursor: pointer;
    position: relative;
}

.radio-option input[type="radio"] {
    position: absolute;
    opacity: 0;
    pointer-events: none;
}

.radio-content {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-md);
    transition: var(--transition-base);
}

.radio-option:hover .radio-content {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(139, 92, 246, 0.5);
    transform: translateY(-2px);
}

.radio-option input[type="radio"]:checked ~ .radio-content {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2));
    border-color: var(--color-primary);
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
}

.radio-check {
    width: 24px;
    height: 24px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: var(--transition-base);
}

.radio-option input[type="radio"]:checked ~ .radio-content .radio-check {
    background: var(--color-primary);
    border-color: var(--color-primary);
}

.radio-check i {
    font-size: 0.75rem;
    color: white;
    opacity: 0;
    transition: var(--transition-fast);
}

.radio-option input[type="radio"]:checked ~ .radio-content .radio-check i {
    opacity: 1;
}

.radio-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.radio-title {
    font-size: 1rem;
    font-weight: 600;
    color: white;
}

.radio-subtitle {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
}

.config-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(6, 182, 212, 0.1);
    border: 1px solid rgba(6, 182, 212, 0.3);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.8);
}

.config-info i {
    color: var(--color-secondary);
}

/* Locked State */
.config-panel.locked {
    opacity: 0.7;
    pointer-events: none;
}

.config-panel.locked .radio-option {
    cursor: not-allowed;
}

.config-panel.locked .config-info {
    background: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.3);
}

.config-panel.locked .config-info i {
    color: var(--color-warning);
}

/* Responsive Design */
@media (max-width: 768px) {
    .radio-group {
        flex-direction: column;
    }
}
```

**1.3 Add JavaScript Logic**

**Location:** Insert in `<script>` section

```javascript
// Swiss Rounds Configuration State
let swissRoundsConfig = {
    selected: 4,
    locked: false
};

// Initialize Swiss Rounds Selector
function initializeSwissRoundsSelector() {
    const radioOptions = document.querySelectorAll('.radio-option');
    const radioInputs = document.querySelectorAll('input[name="swiss-rounds"]');

    // Handle radio option clicks
    radioOptions.forEach(option => {
        option.addEventListener('click', function() {
            if (!swissRoundsConfig.locked) {
                const rounds = parseInt(this.dataset.rounds);
                swissRoundsConfig.selected = rounds;

                // Update radio inputs
                radioInputs.forEach(input => {
                    input.checked = parseInt(input.value) === rounds;
                });

                // Show toast
                showToast('Configuration Updated', `${rounds} Swiss rounds selected`, 'info');
            }
        });
    });
}

// Lock Swiss Rounds Configuration
function lockSwissRoundsConfig() {
    swissRoundsConfig.locked = true;
    const configPanel = document.getElementById('swiss-config-panel');
    configPanel.classList.add('locked');

    // Update info text
    const configInfo = configPanel.querySelector('.config-info span');
    configInfo.textContent = `Configuration locked: ${swissRoundsConfig.selected} Swiss rounds`;
}

// Get Selected Swiss Rounds
function getSelectedSwissRounds() {
    return swissRoundsConfig.selected;
}

// Modified loadParticipants function
async function loadParticipants() {
    try {
        showToast('Loading Participants...', 'Please wait while we load the tournament data', 'info');

        const response = await fetch('/load_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                swiss_rounds: getSelectedSwissRounds()
            })
        });

        const data = await response.json();

        if (data.success) {
            // Lock the Swiss rounds configuration
            lockSwissRoundsConfig();

            showToast('Success!', `Loaded ${data.team_count} teams (${data.player_count} players) - ${getSelectedSwissRounds()} Swiss rounds configured`, 'success');

            // Display teams
            await displayTeams();
        } else {
            showToast('Error', data.message || 'Failed to load participants', 'error');
        }
    } catch (error) {
        console.error('Error loading participants:', error);
        showToast('Error', 'Failed to load participants. Check console for details.', 'error');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeSwissRoundsSelector();
    // ... rest of existing initialization ...
});
```

---

### Phase 2: Backend Changes

#### File: `tournament_dashboard.py`

**2.1 Modify TournamentManager.__init__()**

**Location:** Line ~19

```python
def __init__(self):
    # ... existing code ...
    self.swiss_rounds_count = 4  # Default: 4 Swiss rounds (can be 4 or 5)
    self.swiss_rounds_configured = False  # Track if configuration is set
    self.max_rounds = 6  # Will be recalculated based on swiss_rounds_count
    # ... rest of existing code ...
```

**2.2 Add Configuration Method**

**Location:** After `__init__()`, around line ~27

```python
def configure_swiss_rounds(self, rounds):
    """
    Configure the number of Swiss rounds before tournament setup.
    Must be called before setup_tournament().

    Args:
        rounds (int): Number of Swiss rounds (4 or 5)

    Returns:
        tuple: (success: bool, message: str)
    """
    if self.swiss_rounds_configured:
        return False, "Swiss rounds already configured. Cannot change after loading participants."

    if rounds not in [4, 5]:
        return False, "Swiss rounds must be either 4 or 5."

    self.swiss_rounds_count = rounds
    self.swiss_rounds_configured = True

    # Recalculate max rounds: Swiss + Finals
    # Current structure: Swiss rounds + 1 Finals
    self.max_rounds = self.swiss_rounds_count + 1

    print(f"✓ Swiss rounds configured: {self.swiss_rounds_count} rounds")
    print(f"✓ Total rounds: {self.max_rounds} (Swiss: {self.swiss_rounds_count}, Finals: 1)")

    return True, f"Configured for {self.swiss_rounds_count} Swiss rounds"
```

**2.3 Modify setup_tournament() Method**

**Location:** Around line ~150

```python
def setup_tournament(self, swiss_rounds=None):
    """
    Setup tournament with configured Swiss rounds.

    Args:
        swiss_rounds (int, optional): Override configured Swiss rounds (for backward compatibility)

    Returns:
        tuple: (success: bool, message: str)
    """
    # Use configured rounds if not overridden
    if swiss_rounds is not None:
        # Allow override if not yet configured
        if not self.swiss_rounds_configured:
            self.swiss_rounds_count = swiss_rounds
        else:
            print(f"⚠ Warning: Swiss rounds override ignored (already configured)")

    # Validate configuration
    if not self.swiss_rounds_configured:
        print("⚠ Swiss rounds not configured, using default: 4 rounds")
        self.swiss_rounds_count = 4
        self.swiss_rounds_configured = True

    print(f"✓ Setting up tournament with {self.swiss_rounds_count} Swiss rounds")

    # ... rest of existing setup_tournament() code ...
```

**2.4 Modify /load_data Endpoint**

**Location:** Around line ~400

```python
@app.route('/load_data', methods=['POST'])
def load_data():
    """Load participant data and configure Swiss rounds"""
    try:
        # Get Swiss rounds configuration from request
        data = request.json or {}
        swiss_rounds = data.get('swiss_rounds', 4)

        # Configure Swiss rounds
        success, message = tournament.configure_swiss_rounds(swiss_rounds)
        if not success:
            return jsonify({
                'success': False,
                'message': message
            })

        # Load participant data
        excel_file = 'July_CEDH_Event/13th July CEDH Participant List.xlsx'

        # Try to load from Excel, fallback to sample data
        if os.path.exists(excel_file):
            try:
                success, message = tournament.load_participants(excel_file)
            except Exception as e:
                print(f"Error loading Excel file: {e}")
                print("Falling back to sample data...")
                tournament.create_sample_data()
                success = True
        else:
            print(f"Excel file not found: {excel_file}")
            print("Creating sample data with 16 teams...")
            tournament.create_sample_data()
            success = True

        if success:
            return jsonify({
                'success': True,
                'message': 'Participants loaded successfully',
                'team_count': len(tournament.teams),
                'player_count': len(tournament.participants),
                'swiss_rounds': tournament.swiss_rounds_count
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })

    except Exception as e:
        print(f"Error in load_data: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })
```

**2.5 Add New Endpoint for Configuration Info**

**Location:** After `/load_data` endpoint

```python
@app.route('/get_tournament_config', methods=['GET'])
def get_tournament_config():
    """Get current tournament configuration"""
    return jsonify({
        'swiss_rounds': tournament.swiss_rounds_count,
        'swiss_rounds_configured': tournament.swiss_rounds_configured,
        'max_rounds': tournament.max_rounds,
        'current_round': tournament.current_round
    })
```

---

### Phase 3: Pairing Algorithm Updates

#### File: `unified_swiss_pairing.py`

**3.1 Update Constructor**

**Location:** Line ~50

```python
class UnifiedSwissPairing:
    def __init__(self, teams, tournament_teams, num_rounds=4):
        """
        Initialize unified Swiss pairing algorithm.

        Args:
            teams (dict): Dictionary of team objects
            tournament_teams (list): List of all team names
            num_rounds (int): Number of Swiss rounds (4 or 5)
        """
        self.teams = teams
        self.tournament_teams = tournament_teams
        self.num_rounds = num_rounds  # Support 4 or 5 rounds
        # ... rest of existing code ...
```

**3.2 Update Validation Loops**

**Location:** Throughout the file, update any hardcoded `range(1, 5)` to use `self.num_rounds`

```python
# Example locations:
# Line ~100: Round generation loop
for round_num in range(1, self.num_rounds + 1):
    # Generate round...

# Line ~200: Validation loop
for round_num in range(1, self.num_rounds + 1):
    # Validate round...
```

---

## Testing Plan

### Test Cases

#### TC1: Default Configuration (4 Rounds)
```
1. Open dashboard
2. Verify 4 rounds is pre-selected
3. Load participants
4. Setup tournament
5. Verify 4 Swiss rounds generated
6. Complete tournament
7. Verify finals work correctly
```

#### TC2: Select 5 Rounds
```
1. Open dashboard
2. Select "5 Rounds" radio button
3. Verify toast notification
4. Load participants
5. Verify configuration locked
6. Setup tournament
7. Verify 5 Swiss rounds generated
8. Complete all 5 rounds
9. Verify finals work correctly
```

#### TC3: Configuration Locking
```
1. Open dashboard
2. Select 5 rounds
3. Load participants
4. Attempt to change selection
5. Verify selection is locked
6. Verify info text updated
```

#### TC4: 8 Teams with 5 Rounds
```
1. Select 5 rounds
2. Load 8 teams
3. Setup tournament
4. Verify 5 rounds generate successfully
5. Verify pairing quality maintained
6. Complete tournament
```

#### TC5: 16 Teams with 5 Rounds
```
1. Select 5 rounds
2. Load 16 teams
3. Setup tournament
4. Verify 5 rounds generate successfully
5. Verify pairing quality maintained (expect better distribution)
6. Complete tournament
```

---

## Expected Performance

### Pairing Quality Improvements (5 Rounds vs 4 Rounds)

**8 Teams:**
```
4 Rounds:
- Total matchups: 96
- Repeat rate: 3.2%
- Generation time: <1 second

5 Rounds:
- Total matchups: 120
- Repeat rate: ~8-10% (expected increase)
- Generation time: <2 seconds
```

**16 Teams:**
```
4 Rounds:
- Total matchups: 384
- Unique matchups: 70
- Repeat rate: 81.7%
- Generation time: <10 seconds

5 Rounds:
- Total matchups: 480
- Unique matchups: ~85-90
- Repeat rate: ~75-78% (improved distribution!)
- Generation time: <15 seconds
```

**Key Benefit:** 5 rounds provide better matchup distribution for 16-team tournaments.

---

## Migration & Backward Compatibility

### Backward Compatibility

**Existing Code:** Fully compatible
- Default: 4 rounds (no change from current behavior)
- Existing tournaments continue to work
- No breaking changes to API contracts

**Configuration Override:**
```python
# Old method still works:
tournament.setup_tournament(swiss_rounds=4)

# New method preferred:
tournament.configure_swiss_rounds(5)
tournament.setup_tournament()
```

### Migration Steps

1. **Deploy backend changes first**
   - Add new methods and endpoints
   - Maintain backward compatibility
   - Test with existing tournaments

2. **Deploy frontend changes**
   - Add configuration UI
   - Update JavaScript logic
   - Test user flows

3. **Update documentation**
   - Add configuration instructions
   - Update screenshots
   - Update API documentation

---

## Documentation Updates

### Files to Update

1. **DOCUMENTATION.md**
   - Add Swiss rounds configuration section
   - Update tournament structure section
   - Add screenshots of new UI
   - Update usage guide

2. **CLAUDE.md**
   - Update implementation plan
   - Mark Phase 1 as "Enhanced with configurable rounds"
   - Update timeline

---

## Timeline

**Estimated Time:** 4-6 hours

- **Phase 1 (Frontend):** 2-3 hours
  - UI design and CSS: 1 hour
  - JavaScript logic: 1 hour
  - Testing: 1 hour

- **Phase 2 (Backend):** 1-2 hours
  - Configuration method: 30 minutes
  - Endpoint updates: 30 minutes
  - Testing: 1 hour

- **Phase 3 (Pairing):** 30 minutes
  - Constructor update: 15 minutes
  - Loop updates: 15 minutes

- **Documentation:** 1 hour
  - Update DOCUMENTATION.md
  - Update CLAUDE.md
  - Add screenshots

---

## Success Criteria

✅ User can select 4 or 5 Swiss rounds before loading participants
✅ Configuration UI matches existing design aesthetic
✅ Configuration locks after participants loaded
✅ Backend correctly generates selected number of rounds
✅ Pairing algorithm works with both 4 and 5 rounds
✅ Finals structure works correctly with both configurations
✅ Tournament completes successfully with both configurations
✅ Backward compatibility maintained
✅ Documentation updated

---

## Next Steps

**Tomorrow's Implementation Checklist:**

1. **Phase 1: Frontend Implementation**
   - [ ] Add Swiss rounds configuration HTML to `dashboard_ultra_modern.html`
   - [ ] Add CSS styles for configuration panel
   - [ ] Add JavaScript logic for selection and locking
   - [ ] Test UI responsiveness

2. **Phase 2: Backend Implementation**
   - [ ] Add `configure_swiss_rounds()` method to `TournamentManager`
   - [ ] Update `/load_data` endpoint to accept configuration
   - [ ] Add `/get_tournament_config` endpoint
   - [ ] Update `setup_tournament()` method
   - [ ] Test with both 4 and 5 rounds

3. **Phase 3: Pairing Algorithm**
   - [ ] Update `UnifiedSwissPairing.__init__()` constructor
   - [ ] Update all hardcoded round loops
   - [ ] Test pairing generation with 5 rounds
   - [ ] Verify pairing quality

4. **Testing**
   - [ ] Test all 5 test cases (TC1-TC5)
   - [ ] Test with 8 teams (4 and 5 rounds)
   - [ ] Test with 16 teams (4 and 5 rounds)
   - [ ] Verify backward compatibility

5. **Documentation**
   - [ ] Update DOCUMENTATION.md
   - [ ] Update CLAUDE.md
   - [ ] Add usage instructions

---

**End of Implementation Plan**

This feature is ready for implementation. All design decisions have been made, and the implementation path is clear. Begin with Phase 1 (Frontend) tomorrow.
