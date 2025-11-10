# MTG Tournament Dashboard - API Quick Reference

**Generated:** 2025-11-10
**Purpose:** Fast API endpoint reference for development

---

## 🚀 CORE ENDPOINTS

### 1. Load Participants
```http
GET /load_data
```
**Purpose:** Load participant data from Excel file or create sample data

**Response:**
```json
{
  "success": true,
  "team_count": 16,
  "player_count": 64,
  "teams": ["Team Alpha", "Team Beta", ...],
  "message": "Participants loaded successfully"
}
```

**Frontend Usage:**
```javascript
fetch('/load_data')
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      console.log(`Loaded ${data.team_count} teams`);
    }
  });
```

---

### 2. Configure Swiss Rounds
```http
POST /set_swiss_rounds
Content-Type: application/json

{
  "rounds_count": 4  // 3 or 4
}
```

**Response:**
```json
{
  "success": true,
  "swiss_rounds": 4,
  "message": "Swiss rounds set to 4"
}
```

---

### 3. Setup Tournament
```http
POST /setup_tournament
```

**Purpose:** Generate all Swiss rounds (locked pairings)

**Response:**
```json
{
  "success": true,
  "message": "Tournament setup complete with 16 teams and 4 Swiss rounds!",
  "tournament_teams": ["Team Alpha", ...],
  "swiss_rounds": 4
}
```

**What Happens:**
1. Validates team count (must be 8 or 16)
2. Calls `UnifiedSwissPairing.generate_all_rounds()`
3. Generates all 4 Swiss rounds at once
4. Stores in `self.tables{}`
5. Pairings are now LOCKED for entire tournament

---

### 4. Load Round Tables
```http
GET /setup_round/<round_num>
```

**Example:** `GET /setup_round/1`

**Response:**
```json
{
  "success": true,
  "round": 1,
  "tables": {
    "Table 1": [
      {"Player ID": 1, "Player Name": "Alice", "Team Name": "Team Alpha"},
      {"Player ID": 5, "Player Name": "Eve", "Team Name": "Team Beta"},
      {"Player ID": 9, "Player Name": "Iris", "Team Name": "Team Gamma"},
      {"Player ID": 13, "Player Name": "Mia", "Team Name": "Team Delta"}
    ],
    "Table 2": [...],
    ...
  },
  "validation_issues": []
}
```

---

### 5. Submit Table Results
```http
POST /submit_table_results
Content-Type: application/json

{
  "round": 1,
  "table": "Table 1",
  "results": [
    {"player_id": 1, "points": 5},  // Win
    {"player_id": 5, "points": 1},  // Draw
    {"player_id": 9, "points": 1},  // Draw
    {"player_id": 13, "points": 0}  // Loss
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Table 1 results submitted",
  "updated_scores": {
    "Team Alpha": 5,
    "Team Beta": 1,
    "Team Gamma": 1,
    "Team Delta": 0
  }
}
```

**Important:** Submit each table individually before finalizing round

---

### 6. Submit Round Results (Finalize)
```http
POST /submit_player_results
Content-Type: application/json

{
  "round": 1,
  "player_results": [
    {"player_id": 1, "points": 5},
    {"player_id": 2, "points": 1},
    ...
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Round 1 complete!",
  "next_round": 2,
  "auto_advance": true
}
```

**Special Cases:**
- Round 4 complete → Generates Finals (Top 4 teams)
- Finals complete → Returns championship data

---

## 📊 DATA RETRIEVAL ENDPOINTS

### Get Tournament State
```http
GET /get_tournament_state
```

**Response:**
```json
{
  "teams": {...},
  "scores": {"Team Alpha": 25, ...},
  "player_scores": {1: 10, 2: 5, ...},
  "current_round": 2,
  "round_results": {...},
  "tables": {...}
}
```

---

### Get Specific Round Tables
```http
GET /get_tables/<round_num>
```

**Response:**
```json
{
  "success": true,
  "tables": {...},
  "round": 1,
  "message": "Round 1 pairings (locked since tournament start)"
}
```

---

### Get Finals Data
```http
GET /get_semifinals
```

**Response:**
```json
{
  "success": true,
  "semifinals": {
    "advancing_teams": ["Team Alpha", "Team Beta", "Team Gamma", "Team Delta"],
    "tables": {...}
  },
  "round_5_tables": {...}
}
```

---

### Get Final Standings
```http
GET /get_final_standings
```

**Response:**
```json
{
  "success": true,
  "final_standings": [
    {
      "team_name": "Team Alpha",
      "total_points": 45,
      "finals_points": 10,
      "swiss_points": 35,
      "rank": 1
    },
    ...
  ],
  "mvp": {
    "player_name": "Alice",
    "team_name": "Team Alpha",
    "total_points": 17
  }
}
```

---

## 🔍 VALIDATION ENDPOINTS

### Validate Specific Round
```http
GET /validate_round/<round_num>
```

**Response:**
```json
{
  "round": 1,
  "validation_issues": [],
  "group_issues": [],
  "repeat_issues": [],
  "is_valid": true
}
```

---

### Validate Full Swiss Tournament
```http
GET /validate_full_swiss
```

**Response:**
```json
{
  "overall_success": true,
  "rounds": {
    "Round 1": {"issues": [], "valid": true},
    "Round 2": {"issues": [], "valid": true},
    ...
  },
  "summary": {
    "total_issues": 0,
    "group_violations": 0,
    "repeat_matchups": 0
  }
}
```

---

### Get Tournament Statistics
```http
GET /tournament_statistics
```

**Response:**
```json
{
  "success": true,
  "tournament_config": {
    "team_count": 16,
    "swiss_rounds": 4,
    "total_rounds": 5
  },
  "pairing_quality": {
    "total_matchups": 384,
    "unique_matchups": 70,
    "repeat_rate": 81.7,
    "pairing_efficiency": 18.3
  },
  "validation": {
    "is_perfect": true,
    "total_violations": 0
  },
  "performance": {
    "generation_time": 8.5,
    "algorithm_used": "UnifiedSwissPairing"
  }
}
```

---

## 🎯 COMMON WORKFLOWS

### Complete Tournament Setup
```javascript
// 1. Load participants
await fetch('/load_data');

// 2. Configure Swiss rounds (optional, defaults to 4)
await fetch('/set_swiss_rounds', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({rounds_count: 4})
});

// 3. Setup tournament (generates all rounds)
await fetch('/setup_tournament', {method: 'POST'});

// 4. Load Round 1
const round1 = await fetch('/setup_round/1').then(r => r.json());
```

---

### Score a Round
```javascript
// 1. Submit each table
for (let table of tables) {
  await fetch('/submit_table_results', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      round: currentRound,
      table: table.name,
      results: table.scores
    })
  });
}

// 2. Finalize round (auto-advances)
const result = await fetch('/submit_player_results', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    round: currentRound,
    player_results: allPlayerScores
  })
}).then(r => r.json());

// 3. Load next round
if (result.next_round) {
  await fetch(`/setup_round/${result.next_round}`);
}
```

---

## 📝 NOTES

### Scoring Values
- Win: 5 points
- Draw: 1 point
- Loss: 0 points

### Team Count Validation
- Only 8 or 16 teams supported
- Strict validation enforced
- Error returned if invalid count

### Round Locking
- All Swiss rounds generated at tournament setup
- Pairings are LOCKED (cannot regenerate)
- Ensures consistency throughout tournament

### Auto-Advance
- After submitting round results, next round auto-loads
- Round 4 → Finals generation
- Finals → Championship modal

---

**END OF API REFERENCE**

For complete documentation, see DOCUMENTATION.md

