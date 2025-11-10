# AI Development Guide - MTG Tournament Dashboard

**Generated:** 2025-11-10
**Purpose:** Guide for AI assistants working on this codebase
**Audience:** Claude, GPT, and other AI coding assistants

---

## 🎯 QUICK START FOR AI ASSISTANTS

### First Time Working on This Codebase?

**Read these files in order:**
1. **CODEBASE_INDEX.md** - System overview and architecture (THIS IS YOUR MAP)
2. **DOCUMENTATION.md** - Complete user documentation
3. **SWISS_ROUNDS_CONFIG_PLAN.md** - Next feature to implement
4. **CLAUDE.md** - Long-term roadmap (v2.0 restructuring)

### Before Making Any Changes

**Always do this:**
1. Use `codebase-retrieval` to find relevant code
2. Use `view` tool to read the actual implementation
3. Confirm method signatures and class structures
4. Check for downstream dependencies
5. Make changes using `str-replace-editor` (NEVER recreate files)

---

## 🏗️ ARCHITECTURE MENTAL MODEL

### Think of the System as 3 Layers

**Layer 1: Frontend (dashboard_ultra_modern.html)**
- Pure vanilla JavaScript (no frameworks)
- Glassmorphic UI with modern CSS
- Event-driven architecture
- Communicates via fetch() API calls

**Layer 2: Backend (tournament_dashboard.py)**
- Flask app with 21 RESTful endpoints
- TournamentManager class (in-memory state)
- Orchestrates pairing algorithm
- Generates finals from Swiss results

**Layer 3: Pairing Engine (unified_swiss_pairing.py)**
- Advanced constraint satisfaction solver
- Generates all rounds at once (locked pairings)
- Zero repeat matchups for 8 teams
- 18.3% unique for 16 teams (mathematically optimal)

### Data Flow Pattern
```
User Action → Frontend JS → Fetch API → Flask Endpoint 
→ TournamentManager Method → Update State → JSON Response 
→ Frontend Update → UI Refresh
```

---

## 🔑 KEY DESIGN DECISIONS

### Why All Rounds Generated at Setup?
**Decision:** Generate all 4 Swiss rounds at tournament start (locked pairings)

**Rationale:**
- Ensures consistency (no mid-tournament algorithm changes)
- Prevents repeat matchups (global optimization)
- Faster round transitions (no generation delay)
- Simpler implementation (no dynamic pairing logic)

**Trade-offs:**
- ✅ Zero/minimal repeat matchups (global optimization)
- ✅ Consistent pairings throughout tournament
- ❌ NOT true Swiss pairing (no winner vs winner)
- ❌ Random seating (no score-based positioning)

**Implication:** Cannot regenerate rounds after setup

**Future:** v2.0 will add intelligent seating (score-based seat positions within pods)

---

### Why Only 8 or 16 Teams?
**Decision:** Strict validation - only 8 or 16 teams allowed

**Rationale:**
- Perfect pod configuration (teams divisible by 4)
- Optimal pairing quality (96.8% for 8 teams)
- Mathematical sweet spot for Commander format
- Prevents incomplete pods

**Implication:** Reject any other team count with clear error

---

### Why In-Memory State?
**Decision:** No database, all state in TournamentManager instance

**Rationale:**
- Simplicity (no DB setup required)
- Fast performance (no I/O overhead)
- Single-day tournaments (no persistence needed)
- Easy deployment (Docker or local Python)

**Implication:** State lost on server restart (acceptable for use case)

---

### Why Vanilla JavaScript?
**Decision:** No React/Vue/Angular, pure vanilla JS

**Rationale:**
- Zero dependencies (faster load time)
- Easier deployment (no build step)
- Full control over UI behavior
- Smaller bundle size

**Implication:** More verbose code, but simpler architecture

---

## 🛠️ COMMON DEVELOPMENT TASKS

### Task 1: Add New API Endpoint

**Steps:**
1. Add route decorator in `tournament_dashboard.py`
2. Implement handler function
3. Return JSON response
4. Add frontend fetch() call in `dashboard_ultra_modern.html`
5. Update API_QUICK_REFERENCE.md

**Example:**
```python
@app.route('/get_player_stats/<int:player_id>')
def get_player_stats(player_id):
    stats = tournament.calculate_player_stats(player_id)
    return jsonify({
        'success': True,
        'player_id': player_id,
        'stats': stats
    })
```

---

### Task 2: Modify TournamentManager

**Steps:**
1. Use `codebase-retrieval` to find the method
2. Use `view` to read current implementation
3. Check for callers using `codebase-retrieval`
4. Make changes with `str-replace-editor`
5. Update all callers if signature changed

**Important:** Always check downstream impacts!

---

### Task 3: Update Frontend UI

**Steps:**
1. Locate HTML section in `dashboard_ultra_modern.html`
2. Find corresponding CSS styles (usually nearby)
3. Find JavaScript event handlers
4. Make changes preserving glassmorphic design
5. Test responsive behavior

**Design System:**
- Colors: `--color-primary` (purple), `--color-secondary` (cyan)
- Spacing: `--spacing-sm/md/lg/xl`
- Radius: `--radius-sm/md/lg/xl`
- Transitions: `--transition-fast/base/slow`

---

### Task 4: Modify Pairing Algorithm

**Steps:**
1. Read `unified_swiss_pairing.py` carefully
2. Understand constraint satisfaction approach
3. Make changes to `UnifiedSwissPairing` class
4. Test with both 8 and 16 teams
5. Validate pairing quality metrics

**Warning:** This is complex code. Make small changes and test thoroughly.

---

## 🎨 UI/UX GUIDELINES

### Design Principles
1. **Glassmorphism:** Translucent cards with backdrop blur
2. **Smooth Animations:** Use CSS transitions (0.3s default)
3. **Clear Feedback:** Toast notifications for all actions
4. **Auto-Advance:** Next round loads automatically
5. **Responsive:** Works on desktop, tablet, mobile

### Color Usage
- **Purple (`--color-primary`):** Primary actions, highlights
- **Cyan (`--color-secondary`):** Secondary actions, info
- **Green (`--color-success`):** Success states, wins
- **Red (`--color-danger`):** Errors, losses
- **Orange (`--color-warning`):** Warnings, draws

### Button States
```css
.button {
  background: var(--gradient-primary);
  transition: var(--transition-base);
}

.button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow);
}

.button:active {
  transform: translateY(0);
}
```

---

## 🧪 TESTING STRATEGY

### Manual Testing Checklist
- [ ] Load 8 teams → Setup → Complete tournament
- [ ] Load 16 teams → Setup → Complete tournament
- [ ] Test all score combinations (Win/Draw/Loss)
- [ ] Verify auto-advance between rounds
- [ ] Ensure no repeat matchups
- [ ] Check semifinals generation (Top 8)
- [ ] Check finals generation (Top 4)
- [ ] Validate championship modal
- [ ] Test responsive design (mobile/tablet/desktop)

### Validation Endpoints
```javascript
// Check pairing quality
fetch('/tournament_statistics').then(r => r.json());

// Validate all rounds
fetch('/validate_full_swiss').then(r => r.json());

// Check specific round
fetch('/validate_round/1').then(r => r.json());
```

---

## 🚨 COMMON PITFALLS

### Pitfall 1: Modifying Locked Pairings
**Problem:** Trying to regenerate rounds after setup
**Solution:** All rounds locked at setup. Don't try to change them.

### Pitfall 2: Forgetting Team Count Validation
**Problem:** Allowing 10 teams, 12 teams, etc.
**Solution:** Always validate team count is exactly 8 or 16

### Pitfall 3: Breaking Auto-Advance
**Problem:** Changing round submission logic
**Solution:** Preserve `next_round` in response, frontend expects it

### Pitfall 4: Losing Glassmorphic Design
**Problem:** Adding elements without proper styling
**Solution:** Use existing CSS classes and design tokens

### Pitfall 5: Not Checking Downstream Callers
**Problem:** Changing method signature breaks other code
**Solution:** Use `codebase-retrieval` to find all callers first

---

## 📋 NEXT FEATURE: SWISS ROUNDS CONFIG

**Status:** Ready to implement (4-6 hours)

**Goal:** Add UI to select 4 or 5 Swiss rounds before loading participants

**Implementation Plan:** See SWISS_ROUNDS_CONFIG_PLAN.md

**Key Changes:**
1. Add configuration panel to frontend (HTML + CSS + JS)
2. Add `configure_swiss_rounds()` method to TournamentManager
3. Update `/load_data` endpoint to accept configuration
4. Update `UnifiedSwissPairing` to support 5 rounds
5. Test with both 4 and 5 rounds

**Files to Modify:**
- `templates/dashboard_ultra_modern.html` (Frontend UI)
- `tournament_dashboard.py` (Backend configuration)
- `unified_swiss_pairing.py` (Support 5 rounds)

---

## 🔮 LONG-TERM VISION (v2.0)

**See CLAUDE.md for complete plan**

**Major Changes:**
- 7-round structure (5 Swiss → Semifinals → Finals)
- Intelligent seating (score-based positioning)
- Semifinals phase (Top 8 teams)
- Enhanced tiebreakers
- UI enhancements

**Timeline:** 13 days (~3 weeks)

**Approach:** Implement in phases (Swiss → Semifinals → Finals → UI → Testing → Docs)

---

## 💡 BEST PRACTICES FOR AI ASSISTANTS

### DO:
✅ Read documentation before making changes
✅ Use `codebase-retrieval` to find code
✅ Use `view` to read actual implementation
✅ Use `str-replace-editor` for all edits
✅ Check for downstream impacts
✅ Preserve existing design patterns
✅ Test with both 8 and 16 teams
✅ Update documentation after changes

### DON'T:
❌ Recreate entire files (use str-replace-editor)
❌ Change method signatures without checking callers
❌ Break auto-advance functionality
❌ Allow invalid team counts (not 8 or 16)
❌ Modify locked pairings after setup
❌ Add dependencies without discussion
❌ Break glassmorphic design
❌ Skip validation endpoints

---

## 📚 REFERENCE DOCUMENTATION

### For Users
- **DOCUMENTATION.md** - Complete user guide

### For Developers
- **CODEBASE_INDEX.md** - System overview
- **API_QUICK_REFERENCE.md** - API endpoints
- **CLAUDE.md** - Implementation plan
- **SWISS_ROUNDS_CONFIG_PLAN.md** - Next feature

### For Understanding
- **Architecture Diagrams** - See Mermaid diagrams above
- **Code Comments** - Inline documentation in source files

---

## 🎓 LEARNING RESOURCES

### Understanding the Pairing Algorithm
1. Read `unified_swiss_pairing.py` header comments
2. Study `HybridConstraintSolver` class
3. Review validation reports from `/tournament_statistics`
4. Test with 8 teams (simpler to understand)

### Understanding the Frontend
1. Read CSS variables (`:root` section)
2. Study glassmorphic card styles
3. Follow fetch() API calls
4. Trace event handlers

### Understanding the Backend
1. Read `TournamentManager.__init__()` for state
2. Study API endpoints (21 total)
3. Follow tournament flow (Load → Setup → Rounds → Finals)
4. Review validation methods

---

**END OF AI DEVELOPMENT GUIDE**

Remember: This is a production-ready system. Make changes carefully and test thoroughly!

