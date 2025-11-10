# MTG Tournament Dashboard - Codebase Index & Analysis

**Generated:** 2025-11-10
**Status:** Complete Analysis ✅
**Purpose:** Comprehensive codebase understanding for AI-assisted development

---

## 📋 QUICK REFERENCE

### Project Overview
- **Type:** Web-based MTG CEDH Tournament Management System
- **Tech Stack:** Flask (Python) + Vanilla JavaScript + Modern CSS
- **Current Version:** 1.0 (Production Ready)
- **Team Support:** 8 or 16 teams (32 or 64 players)
- **Tournament Structure:** Configurable Swiss Rounds (4 or 5) + Finals (Top 4)

### Key Files
```
tournament_dashboard.py          # Backend (1,754 lines) - Flask app + TournamentManager
unified_swiss_pairing.py        # Pairing Algorithm (1,375 lines) - Advanced CSP solver
templates/dashboard_ultra_modern.html  # Frontend (2,224 lines) - Modern UI
DOCUMENTATION.md                # Complete user documentation
CLAUDE.md                       # Implementation plan for v2.0
SWISS_ROUNDS_CONFIG_PLAN.md     # Next feature to implement
```

---

## 🏗️ ARCHITECTURE OVERVIEW

### System Flow
```
1. Select Swiss Rounds (4 or 5) → TournamentManager.configure_swiss_rounds()
2. Load Participants (Excel/Sample) → TournamentManager.teams
3. Setup Tournament → UnifiedSwissPairing.generate_all_rounds()
4. All Swiss rounds generated & locked (4 or 5 based on configuration)
5. User scores each round → Auto-advance to next round
6. After final Swiss round → Generate Finals (Top 4 teams)
7. Finals complete → Championship Modal
```

### Data Flow
```
Excel File → load_participants() → self.teams{} → setup_tournament()
         → UnifiedSwissPairing → generate_all_rounds() → self.tables{}
         → Frontend displays → User scores → submit_table_results()
         → Update scores → Auto-advance → Next round
```

---

## 📁 FILE STRUCTURE

### Backend Files

#### `tournament_dashboard.py` (1,754 lines)
**Purpose:** Main Flask application with tournament management logic

**Key Classes:**
- `TournamentManager` (Lines 11-931)
  - Properties: teams, scores, player_scores, tables, current_round
  - Methods: load_participants(), setup_tournament(), generate_all_swiss_rounds()

**API Endpoints (21 total):**
```python
GET  /                          # Dashboard home
POST /load_data                 # Load participants from Excel (with swiss_rounds config)
POST /set_swiss_rounds          # Configure 4 or 5 rounds
POST /setup_tournament          # Generate all Swiss rounds
POST /submit_table_results      # Submit individual table scores
POST /submit_player_results     # Finalize round (auto-advance)
GET  /setup_round/<round_num>   # Load specific round tables
GET  /get_tables/<round_num>    # Get pre-generated tables
GET  /get_tournament_state      # Current tournament state
GET  /validate_round/<round_num> # Validate pairing rules
GET  /validate_full_swiss       # Validate all 4 rounds
GET  /get_semifinals            # Finals data
GET  /get_final_standings       # Championship standings
GET  /tournament_statistics     # Detailed stats & validation
```

**Key Methods:**
```python
load_participants(excel_file)           # Lines 28-139
create_sample_data()                    # Lines 141-249 (16 teams)
setup_tournament(swiss_rounds=None)     # Lines 251-320
generate_all_swiss_rounds()             # Lines 322-365
organize_rounds_into_tables()           # Lines 404-422
submit_player_results(round_num, results) # Lines 472-500
calculate_team_scores()                 # Lines 502-512
generate_unified_finals()               # Lines 514-630
calculate_final_round_standings()       # Lines 632-700
```

#### `unified_swiss_pairing.py` (1,375 lines)
**Purpose:** Advanced constraint satisfaction pairing algorithm

**Key Classes:**
```python
HybridConstraintSolver          # Lines 46-400
  - build_constraint_graph()
  - solve_with_backtracking()
  - intelligent_fallback()

UnifiedSwissPairing             # Lines 402-1375
  - generate_all_rounds()       # Main entry point
  - validate_solution()
  - get_detailed_statistics()
```

**Algorithm Features:**
- Zero repeat matchups for 8 teams (96.8% efficiency)
- 18.3% unique matchups for 16 teams (mathematically optimal)
- Triple fallback strategy (Enhanced CSP → Dynamic → Relaxed)
- Performance: <1s for 8 teams, <10s for 16 teams

### Frontend Files

#### `templates/dashboard_ultra_modern.html` (2,224 lines)
**Purpose:** Modern glassmorphic UI with vanilla JavaScript

**Structure:**
```html
Lines 1-100:    HTML head, fonts, CSS variables
Lines 100-800:  CSS styles (glassmorphism, animations)
Lines 800-1200: HTML structure (controls, tables, standings)
Lines 1200-2224: JavaScript (API calls, UI updates, scoring)
```

**Key JavaScript Functions:**
```javascript
loadParticipants()              # Load teams from backend
setupTournament()               # Generate all rounds
loadRound(roundNum)             # Display round tables
submitTableResults(table)       # Submit table scores
submitRoundResults()            # Finalize round (auto-advance)
showChampionshipModal()         # Winner celebration
```

**UI Components:**
- Control Panel (Load, Setup, Timer)
- Round Selector (Rounds 1-4, Finals)
- Tables Grid (4 players per table, score buttons)
- Team Standings (live scores)
- Championship Modal (winner, MVP, standings)

---

## 🔑 KEY CONCEPTS

### Tournament Structure (Current v1.0)
```
Setup Phase:
  1. Select Swiss Rounds (4 or 5) ✅
  2. Load Participants (8 or 16 teams)
  3. Setup Tournament (generates all Swiss rounds)
  4. Round 1 auto-loads

Swiss Rounds (4 or 5 rounds):
  Round 1 → Score → Submit → AUTO-ADVANCE to Round 2
  Round 2 → Score → Submit → AUTO-ADVANCE to Round 3
  Round 3 → Score → Submit → AUTO-ADVANCE to Round 4
  Round 4 → Score → Submit → AUTO-ADVANCE to Round 5 or Finals
  [If 5 rounds selected]
  Round 5 → Score → Submit → AUTO-ADVANCE to Finals

Finals:
  - Top 4 teams (by Swiss points)
  - 4 tables (strength-based matchups)
  - Score → Submit → Championship Modal

Championship:
  - Winner announcement
  - Final standings (Swiss + Finals breakdown)
  - MVP recognition
  - Tiebreaker: Higher Swiss points
```

### Scoring System
```
Win:  5 points
Draw: 1 point
Loss: 0 points

Team Score = Sum of 4 players' points
Tournament Winner = Highest total (Swiss + Finals)
Tiebreaker = Higher Swiss points
MVP = Highest individual total
```

### Pairing Rules (Current v1.0)
```
1. Team Separation: No teammates in same pod (100%)
2. Pre-Generated: All rounds created at setup (NOT performance-based)
3. Repeat Avoidance: Minimize repeat matchups globally
4. Intelligent Seating: Round 1 random, Rounds 2+ score-based ✨ NEW
5. Locked Pairings: Cannot regenerate after tournament start

Intelligent Seating:
- Round 1: Random seating (no prior scores)
- Rounds 2+: Higher team score → Seat 1, lower → Seat 4
- Dynamic: Updates each round based on current standings
```

---

## 📊 DATA MODELS

### TournamentManager State
```python
self.participants = []           # All players (list of dicts)
self.teams = {}                  # {team_name: [player1, player2, ...]}
self.tournament_teams = []       # List of team names in tournament
self.scores = {}                 # {team_name: total_points}
self.player_scores = {}          # {player_id: total_points}
self.tables = {}                 # {round_num: {table_name: [players]}}
self.round_results = {}          # {round_num: {players: {id: points}}}
self.swiss_rounds_count = 4      # Configurable (3 or 4)
self.current_round = 1           # Current round number
```

### Player Object
```python
{
    'Player ID': 1,
    'Player Name': 'Alice',
    'Team Name': 'Team Alpha'
}
```

### Table Structure
```python
self.tables = {
    1: {  # Round 1
        'Table 1': [player1, player2, player3, player4],
        'Table 2': [player5, player6, player7, player8],
        # ... 8 or 16 tables total
    },
    2: { ... },  # Round 2
    3: { ... },  # Round 3
    4: { ... }   # Round 4
}
```

---

## ✅ RECENTLY IMPLEMENTED: SWISS ROUNDS CONFIG

**Status:** Fully implemented and tested

**Goal:** Add UI option to select 4 or 5 Swiss rounds before loading participants

**Files Modified:**
1. `templates/dashboard_ultra_modern.html` - Added configuration UI with radio buttons
2. `tournament_dashboard.py` - Added configure_swiss_rounds() method and updated endpoints
3. Round selector dropdown now dynamically updates based on configuration

**Features:**
- Configuration panel with 4 or 5 round selection
- Configuration locks after participants are loaded
- Backend validation ensures only 4 or 5 rounds allowed
- Round selector dropdown dynamically shows correct number of rounds
- Toast notifications for configuration changes

**Estimated Time:** 4-6 hours

**Implementation Order:**
1. Frontend (HTML + CSS + JavaScript) - 2-3 hours
2. Backend (Flask endpoints + configuration) - 1-2 hours
3. Pairing Algorithm (support 5 rounds) - 30 minutes
4. Testing (all test cases) - 1 hour

---

## 🔮 FUTURE ROADMAP (v2.0)

**See CLAUDE.md for complete plan**

**Major Changes:**
- 7-round structure (4 or5 Swiss → Semifinals → Finals)
- Intelligent seating (score-based positioning)
- Semifinals phase (Top 8 teams)
- Enhanced tiebreakers (Finals > Semis > Swiss)
- UI enhancements (progression tracker, bracket visualization)

**Timeline:** 13 days (~3 weeks)

---

## 📚 DOCUMENTATION FILES

### User Documentation
- **DOCUMENTATION.md** - Complete system documentation (single source of truth)
  - Installation (Docker + Local)
  - Tournament structure & flow
  - Usage guide & troubleshooting
  - API reference
  - Testing & validation

### Development Documentation
- **CLAUDE.md** - v2.0 implementation plan & codebase analysis
- **SWISS_ROUNDS_CONFIG_PLAN.md** - Next feature implementation plan
- **CODEBASE_INDEX.md** - This file (quick reference for AI)

---

## 🛠️ DEVELOPMENT WORKFLOW

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python tournament_dashboard.py

# Access dashboard
http://localhost:5000
```

### Running with Docker
```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Making Changes
1. Read relevant documentation (DOCUMENTATION.md, CLAUDE.md)
2. Use codebase-retrieval to find specific code
3. Make changes using str-replace-editor
4. Test locally
5. Update documentation if needed

---

**END OF CODEBASE INDEX**

For detailed implementation plans, see CLAUDE.md and SWISS_ROUNDS_CONFIG_PLAN.md

