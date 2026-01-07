# 12-Hour Production Readiness Improvement Plan
**MTG Tournament Dashboard - Production Hardening**

---

## Executive Summary

The MTG Tournament Dashboard has a solid foundation with automatic backup mechanisms already in place. However, for guaranteed 12-hour stability in production environments, several critical improvements are needed to address concurrency, persistence, error handling, and monitoring.

**Current Risk Level:** MEDIUM (for single-threaded local use)
**Target Risk Level:** LOW (production-ready for 12-hour events)

### Your Situation:
- **Timeline:** 3-5 days available (8-10 hours implementation)
- **Deployment:** Local PC (single machine)
- **Concurrency:** Single user only

**Recommended Approach:** Implement **Critical + High Priority** fixes (Phases 1-2). This provides excellent reliability for your single-user local PC deployment without over-engineering.

---

## Phase 1: Critical Fixes (Must Have)

### 1.1 Thread Safety Implementation

**Problem:** The global `tournament` object is accessed without locking. If Flask runs with `threaded=True` or multiple workers, race conditions can corrupt data.

**Files to Modify:**
- [tournament_dashboard.py](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py)

**Implementation:**
1. Add `threading.Lock()` at module level (after line 1657)
2. Wrap all state-modifying endpoints with lock context:
   - `/submit_table_results` (line 2212)
   - `/edit_table_results` (line 2449)
   - `/submit_player_results` (line 1936)
   - `/setup_round/<N>` (line 2811)
   - `/load_data` (line 1658)
   - `/setup_tournament` (line 1838)
   - All timer endpoints (lines 3804-3860)

**Example:**
```python
tournament_lock = threading.Lock()

@app.route('/submit_table_results', methods=['POST'])
def submit_table_results():
    with tournament_lock:
        # existing code...
```

**Impact:** Prevents data corruption with concurrent access
**Effort:** 2 hours (add lock to ~15 endpoints)

---

### 1.2 Timer State Persistence

**Problem:** Timer state (`timer_running`, `timer_start_time`, `timer_paused_at`, `timer_duration`) is not saved to backup. Server restart loses timer.

**Files to Modify:**
- [tournament_dashboard.py:78-129](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L78-L129) (save_state)
- [tournament_dashboard.py:151-262](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L151-L262) (load_state)

**Implementation:**

**In `save_state()` (add after line 101):**
```python
"timer": {
    "running": self.timer_running,
    "start_time": self.timer_start_time.isoformat() if self.timer_start_time else None,
    "paused_at": self.timer_paused_at,
    "duration": self.timer_duration
}
```

**In `load_state()` (add after line 220):**
```python
timer_data = state_data.get('timer', {})
self.timer_running = timer_data.get('running', False)
start_time_str = timer_data.get('start_time')
self.timer_start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
self.timer_paused_at = timer_data.get('paused_at', 0)
self.timer_duration = timer_data.get('duration', 3000)
```

**Impact:** Timer survives server restarts
**Effort:** 30 minutes

---

### 1.3 Backup Failure Monitoring & Alerts

**Problem:** If `save_backup()` fails (disk full, permissions), the system continues silently. Frontend is never notified. By the time of a crash, backups may have been failing for hours.

**Files to Modify:**
- [tournament_dashboard.py:78-149](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L78-L149) (save_state)
- [tournament_dashboard.py](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py) (all endpoints that call save_backup)
- [templates/dashboard_ultra_modern.html](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\templates\dashboard_ultra_modern.html) (add backup status indicator)

**Implementation:**

**Step 1: Add Last Backup Timestamp Tracking**
```python
# In TournamentManager.__init__ (after line 62)
self.last_backup_success = None
self.last_backup_failure = None
self.consecutive_backup_failures = 0
```

**Step 2: Update save_state() to Track Status (around line 148)**
```python
try:
    # ... existing save logic ...
    self.last_backup_success = datetime.now()
    self.consecutive_backup_failures = 0
    print(f"[BACKUP] Tournament state saved successfully to {filepath}")
    return True
except Exception as e:
    self.last_backup_failure = datetime.now()
    self.consecutive_backup_failures += 1
    print(f"[ERROR] Failed to save backup: {e}")
    traceback.print_exc()
    return False
```

**Step 3: Return Backup Status in All Endpoints**
Modify endpoints to include backup status in response:
```python
# Example in submit_table_results (after line 2382)
success = tournament.save_backup()
if not success:
    # Don't fail the request, but warn user
    return jsonify({
        'success': True,
        'warning': 'Scores saved but backup failed! Please manually backup.',
        'backup_failed': True
    })
```

**Step 4: Add Backup Health Endpoint**
```python
@app.route('/backup_health', methods=['GET'])
def backup_health():
    return jsonify({
        'last_success': tournament.last_backup_success.isoformat() if tournament.last_backup_success else None,
        'last_failure': tournament.last_backup_failure.isoformat() if tournament.last_backup_failure else None,
        'consecutive_failures': tournament.consecutive_backup_failures,
        'backup_file_exists': os.path.exists(tournament.backup_file),
        'backup_file_size': os.path.getsize(tournament.backup_file) if os.path.exists(tournament.backup_file) else 0
    })
```

**Step 5: Frontend Backup Status Indicator**
Add to dashboard header (near timer):
```html
<div id="backup-status" class="backup-indicator">
    <i class="fas fa-save"></i>
    <span id="backup-status-text">Backup OK</span>
</div>
```

```javascript
// Poll backup health every 30 seconds
async function checkBackupHealth() {
    const res = await fetch('/backup_health');
    const data = await res.json();

    const indicator = document.getElementById('backup-status');
    const text = document.getElementById('backup-status-text');

    if (data.consecutive_failures > 0) {
        indicator.className = 'backup-indicator backup-error';
        text.textContent = `Backup Failed (${data.consecutive_failures}x)`;
        showToast('Backup Warning', 'Automatic backup is failing! Please check disk space.', 'error', 10000);
    } else {
        indicator.className = 'backup-indicator backup-ok';
        text.textContent = 'Backup OK';
    }
}

setInterval(checkBackupHealth, 30000);
```

**Impact:** Immediate visibility of backup failures
**Effort:** 3 hours

---

### 1.4 Redundant Backup Strategy

**Problem:** Single backup file. If corruption occurs during write, backup is lost.

**Files to Modify:**
- [tournament_dashboard.py:78-149](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L78-L149)

**Implementation:**

**Rotating Backup Strategy:**
```python
def save_state(self, filepath='tournament_state.json.bak'):
    """Save with rotation: keep last 3 backups"""
    try:
        # Rotate existing backups
        for i in range(2, 0, -1):
            old_file = f"{filepath}.{i}"
            new_file = f"{filepath}.{i+1}"
            if os.path.exists(old_file):
                os.replace(old_file, new_file)

        # Move current backup to .1
        if os.path.exists(filepath):
            os.replace(filepath, f"{filepath}.1")

        # Save new backup
        temp_path = filepath + '.tmp'
        with open(temp_path, 'w') as f:
            json.dump(state, f, indent=2)

        os.rename(temp_path, filepath)

        # Verify backup is readable
        with open(filepath, 'r') as f:
            json.load(f)  # Verify it's valid JSON

        self.last_backup_success = datetime.now()
        self.consecutive_backup_failures = 0
        return True
    except Exception as e:
        # ... error handling ...
```

**Result:**
- `tournament_state.json.bak` (latest)
- `tournament_state.json.bak.1` (previous)
- `tournament_state.json.bak.2` (2 rounds ago)
- `tournament_state.json.bak.3` (3 rounds ago)

**Impact:** Protection against backup corruption
**Effort:** 1 hour

---

### 1.5 Flask Production Configuration

**Problem:** Running on Werkzeug development server with no timeouts, no request limits, no proper error handling.

**Files to Modify:**
- [tournament_dashboard.py:3863-3871](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L3863-L3871)
- [tournament_dashboard.py:11](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L11)

**Implementation:**

**Step 1: Add Flask App Configuration (after line 11)**
```python
app = Flask(__name__)

# Production configuration
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
    JSON_SORT_KEYS=False,  # Performance
    SEND_FILE_MAX_AGE_DEFAULT=0,  # No caching for dynamic content
    JSONIFY_PRETTYPRINT_REGULAR=False  # Smaller responses
)
```

**Step 2: Update run configuration (replace lines 3863-3871)**
```python
if __name__ == '__main__':
    # Restore state from backup on startup
    if os.path.exists(tournament.backup_file):
        print("🔄 Restoring tournament state from backup...")
        tournament.load_backup(tournament.backup_file)

    # Production server settings
    import os
    debug_mode = os.getenv('FLASK_ENV') != 'production'

    # Enable threading for better responsiveness (safe with our locks)
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=5001,
        threaded=True,  # Enable concurrent requests
        use_reloader=False  # Prevent double initialization
    )
```

**Step 3: Optional - Add Gunicorn for True Production**
Create `run_production.sh`:
```bash
#!/bin/bash
# Restore backup on startup
python -c "from tournament_dashboard import tournament; tournament.load_backup('tournament_state.json.bak')"

# Run with Gunicorn (install: pip install gunicorn)
gunicorn -w 1 -b 0.0.0.0:5001 --timeout 300 --log-level info tournament_dashboard:app
```

**Note:** Use `-w 1` (single worker) since we have global state. Multiple workers would need Redis/database.

**Impact:** More stable under load, proper timeout handling
**Effort:** 1 hour (Flask config) + 2 hours (Gunicorn setup, optional)

---

## Phase 2: High Priority Fixes (Should Have)

### 2.1 Fix Silent Exception Handling

**Problem:** Bare `except:` clause at line 202 swallows all exceptions when restoring tournament state enum.

**Files to Modify:**
- [tournament_dashboard.py:194-203](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L194-L203)

**Implementation:**
```python
# Replace bare except (line 202)
try:
    for state_enum in TournamentState:
        if state_enum.value == state_str:
            self.state = state_enum
            break
except (ValueError, AttributeError, KeyError) as e:
    print(f"[ERROR] Failed to restore state enum '{state_str}': {e}")
    self.state = TournamentState.INITIAL
```

**Impact:** Better error diagnostics
**Effort:** 15 minutes

---

### 2.2 Frontend Timer Interval Cleanup

**Problem:** `setInterval(pollTimer, 1000)` is never cleared. Multiple intervals accumulate if user navigates or page is reloaded via soft refresh.

**Files to Modify:**
- [templates/dashboard_ultra_modern.html:3538-3551](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\templates\dashboard_ultra_modern.html#L3538-L3551)

**Implementation:**
```javascript
// Add at top of script section
let timerIntervalId = null;
let backupHealthIntervalId = null;

function startTimerPolling() {
    // Clear existing interval
    if (timerIntervalId) {
        clearInterval(timerIntervalId);
    }

    // Start new interval
    timerIntervalId = setInterval(pollTimer, 1000);
}

function stopTimerPolling() {
    if (timerIntervalId) {
        clearInterval(timerIntervalId);
        timerIntervalId = null;
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', () => {
    startTimerPolling();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    stopTimerPolling();
    if (backupHealthIntervalId) clearInterval(backupHealthIntervalId);
});
```

**Impact:** Prevents memory leak in long-running sessions
**Effort:** 30 minutes

---

### 2.3 Manual Backup Button in Frontend

**Problem:** Only automatic backups exist. No way for admin to manually trigger backup before critical operations.

**Files to Modify:**
- [templates/dashboard_ultra_modern.html](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\templates\dashboard_ultra_modern.html) (add button near Restore Backup)
- [tournament_dashboard.py:3759-3772](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L3759-L3772) (endpoint already exists)

**Implementation:**

**Add button (near line 3086, next to Restore Backup):**
```html
<button class="btn btn-primary" onclick="manualBackup()">
    <i class="fas fa-save"></i>
    <span>Save Backup Now</span>
</button>
```

**Add JavaScript function:**
```javascript
async function manualBackup() {
    try {
        showToast('Saving...', 'Creating manual backup...', 'info');

        const response = await fetch('/save_backup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            showToast('Success', 'Backup saved successfully!', 'success');
        } else {
            showToast('Backup Failed', data.message, 'error');
        }
    } catch (error) {
        showToast('Error', 'Failed to save backup: ' + error.message, 'error');
    }
}
```

**Impact:** User control over backups
**Effort:** 30 minutes

---

### 2.4 Periodic Auto-Save (Belt and Suspenders)

**Problem:** Auto-save only triggers on explicit actions. If admin enters scores but doesn't submit for 30 minutes, no backup created.

**Files to Modify:**
- [tournament_dashboard.py](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py) (add background thread)

**Implementation:**

**Add after TournamentManager class definition:**
```python
import threading
import time

def periodic_backup_thread(tournament_obj, interval=300):
    """Background thread to save backup every 5 minutes"""
    while True:
        time.sleep(interval)
        try:
            with tournament_lock:  # Use the lock from 1.1
                tournament_obj.save_backup()
                print(f"[AUTO-BACKUP] Periodic backup completed at {datetime.now()}")
        except Exception as e:
            print(f"[AUTO-BACKUP ERROR] {e}")

# Start background backup thread (add in __main__ section, after line 3867)
backup_thread = threading.Thread(target=periodic_backup_thread, args=(tournament,), daemon=True)
backup_thread.start()
```

**Impact:** Guaranteed backup every 5 minutes regardless of user actions
**Effort:** 30 minutes

---

## Phase 3: Medium Priority Improvements (Nice to Have)

### 3.1 State History Limit

**Problem:** `state_history` list grows unbounded.

**Files to Modify:**
- [tournament_dashboard.py:74](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L74)

**Implementation:**
```python
self.state_history.append(transition)

# Keep only last 100 transitions
if len(self.state_history) > 100:
    self.state_history = self.state_history[-100:]
```

**Impact:** Prevents unbounded memory growth
**Effort:** 5 minutes

---

### 3.2 Score Edit History Limit

**Problem:** `score_history` per table grows unbounded with edits.

**Files to Modify:**
- [tournament_dashboard.py:2614-2625](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py#L2614-L2625)

**Implementation:**
```python
tournament.round_results[round_num]['score_history'][table_name].append(edit_entry)

# Keep only last 10 edits per table
history = tournament.round_results[round_num]['score_history'][table_name]
if len(history) > 10:
    tournament.round_results[round_num]['score_history'][table_name] = history[-10:]
```

**Impact:** Bounds memory usage for heavily-edited tables
**Effort:** 5 minutes

---

### 3.3 Frontend State Sync Polling

**Problem:** If page is left open and server state changes (via another client or server restart), frontend shows stale data.

**Files to Modify:**
- [templates/dashboard_ultra_modern.html](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\templates\dashboard_ultra_modern.html)

**Implementation:**
```javascript
let lastKnownRound = null;
let lastKnownState = null;

async function checkStateSync() {
    try {
        const res = await fetch('/get_state_info');
        const data = await res.json();

        // Detect if server state changed unexpectedly
        if (lastKnownRound !== null && data.current_round !== lastKnownRound) {
            showToast('State Changed',
                `Server round changed from ${lastKnownRound} to ${data.current_round}. Reloading...`,
                'warning', 5000);
            setTimeout(() => location.reload(), 2000);
        }

        lastKnownRound = data.current_round;
        lastKnownState = data.state;
    } catch (e) {
        console.error('State sync check failed:', e);
    }
}

// Poll every 30 seconds
setInterval(checkStateSync, 30000);
```

**Impact:** Prevents stale data scenarios
**Effort:** 1 hour

---

### 3.4 Health Check Endpoint

**Problem:** No way to monitor if server is healthy during 12-hour operation.

**Files to Modify:**
- [tournament_dashboard.py](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py)

**Implementation:**
```python
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'uptime_seconds': (datetime.now() - app_start_time).total_seconds(),
        'current_round': tournament.current_round,
        'tournament_state': tournament.state.value,
        'backup_status': {
            'last_success': tournament.last_backup_success.isoformat() if tournament.last_backup_success else None,
            'consecutive_failures': tournament.consecutive_backup_failures
        },
        'memory_mb': get_memory_usage()  # Optional: requires psutil
    })

# Track app start time
app_start_time = datetime.now()

def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except ImportError:
        return None
```

**Impact:** External monitoring capability
**Effort:** 30 minutes

---

### 3.5 Add Watchdog for Automatic Recovery

**Problem:** If Python process crashes, someone needs to manually restart it.

**Implementation:**

**Create `watchdog.sh` (Linux/Mac):**
```bash
#!/bin/bash
while true; do
    echo "[WATCHDOG] Starting tournament dashboard..."
    python tournament_dashboard.py
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[WATCHDOG] Clean exit, stopping watchdog"
        break
    else
        echo "[WATCHDOG] Crashed with code $EXIT_CODE, restarting in 5 seconds..."
        sleep 5
    fi
done
```

**Create `watchdog.bat` (Windows):**
```batch
@echo off
:start
echo [WATCHDOG] Starting tournament dashboard...
python tournament_dashboard.py
if %ERRORLEVEL% EQU 0 (
    echo [WATCHDOG] Clean exit, stopping watchdog
    exit /b 0
) else (
    echo [WATCHDOG] Crashed with code %ERRORLEVEL%, restarting in 5 seconds...
    timeout /t 5 /nobreak
    goto start
)
```

**Impact:** Automatic recovery from crashes
**Effort:** 15 minutes

---

## Phase 4: Long-Term Improvements (Future)

### 4.1 Database Migration (Redis/SQLite)

**Problem:** In-memory state doesn't support multiple workers or true high availability.

**Solution:** Migrate to database for state storage:
- **Redis:** Best for single-server deployment with fast state access
- **SQLite:** Best for single-server with file persistence
- **PostgreSQL:** Best for multi-server deployment

**Effort:** 40+ hours (major refactor)

---

### 4.2 WebSocket for Real-Time Updates

**Problem:** Polling creates unnecessary traffic and has latency.

**Solution:** Use Flask-SocketIO for push notifications:
- Score submissions broadcast to all connected clients
- Round transitions notify immediately
- Timer updates via WebSocket

**Effort:** 20+ hours

---

### 4.3 User Authentication & Multi-User Support

**Problem:** No user roles, anyone can edit anything.

**Solution:** Add authentication with roles:
- **Admin:** Full control
- **Scorekeeper:** Can enter/edit scores
- **Viewer:** Read-only access

**Effort:** 15+ hours

---

## Implementation Priority for 12-Hour Event

### ⭐ RECOMMENDED FOR YOUR SITUATION (8-10 hours total):

**Phase 1 - Critical Fixes (4-6 hours):**
1. **Thread Safety** (1.1) - 2 hours
   - *Note: Lower priority for single-user, but good practice*
2. **Timer Persistence** (1.2) - 30 min ✅ CRITICAL
3. **Backup Failure Alerts** (1.3) - 3 hours ✅ CRITICAL
4. **Redundant Backups** (1.4) - 1 hour ✅ CRITICAL

**Phase 2 - High Priority Fixes (2-4 hours):**
5. **Manual Backup Button** (2.3) - 30 min ✅ CRITICAL
6. **Periodic Auto-Save** (2.4) - 30 min ✅ CRITICAL
7. **Timer Interval Cleanup** (2.2) - 30 min
8. **Flask Production Config** (1.5) - 1 hour
9. **Silent Exception Fix** (2.1) - 15 min

**This gives you:** Belt-and-suspenders reliability perfect for local PC single-user deployment. Timer won't reset, backups have visibility and redundancy, automatic recovery.

---

### Alternative: Minimum Viable (4-6 hours total):
If you're short on time, prioritize items marked with ✅ CRITICAL above:
- Timer Persistence (1.2)
- Backup Failure Alerts (1.3)
- Redundant Backups (1.4)
- Manual Backup Button (2.3)
- Periodic Auto-Save (2.4)

**This gives you:** Essential reliability for 12-hour operation.

---

### Optional: Comprehensive (12-15 hours total):
If you have extra time after recommended fixes:
10. **State History Limits** (3.1, 3.2) - 10 min
11. **Health Check Endpoint** (3.4) - 30 min
12. **Watchdog Script** (3.5) - 15 min
13. **Frontend State Sync** (3.3) - 1 hour

**This gives you:** Production-grade monitoring and recovery.

---

## Files to Modify Summary

| File | Changes | LOC Added/Modified |
|------|---------|-------------------|
| [tournament_dashboard.py](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\tournament_dashboard.py) | Thread locks, timer persistence, backup monitoring, config | ~150 lines |
| [dashboard_ultra_modern.html](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\templates\dashboard_ultra_modern.html) | Backup status UI, timer cleanup, manual backup button | ~100 lines |
| New: `watchdog.sh` / `watchdog.bat` | Crash recovery scripts | ~20 lines each |
| New: `run_production.sh` | Gunicorn launcher (optional) | ~10 lines |

---

## Testing Strategy

### Pre-Event Testing (1 week before):
1. **Load Test:** Run simulate_full_tournament.py 10 times consecutively
2. **Crash Test:** Kill Python process mid-round, verify recovery
3. **Backup Test:** Delete backup file, verify alert appears
4. **Timer Test:** Start timer, restart server, verify timer resumes
5. **Concurrent Test:** Open dashboard in 3 browsers, submit scores simultaneously

### Day-Of Preparation:
1. **Disable Windows Updates:** Prevent forced restart
2. **Disable Sleep/Hibernation:** Keep PC running
3. **Close Unnecessary Apps:** Minimize resource usage
4. **Test Backup/Restore:** Verify recovery process works
5. **Print Emergency Guide:** Keep paper copy of recovery steps

### During Event Monitoring:
1. Watch backup status indicator (top of dashboard)
2. Check `/health` endpoint every hour
3. Monitor Python console for errors
4. Manually backup before Round 4 (semifinals) transition

---

## Risk Assessment After Improvements

| Risk | Before | After | Mitigation |
|------|--------|-------|------------|
| Data Loss on Crash | HIGH | LOW | Auto-backups + rotation + monitoring |
| Concurrent Access Corruption | CRITICAL* | LOW | Thread locks on all endpoints |
| Timer Reset on Restart | HIGH | LOW | Timer persistence |
| Silent Backup Failure | HIGH | LOW | Real-time monitoring + alerts |
| Memory Leak | MEDIUM | LOW | Interval cleanup + history limits |
| Process Crash | MEDIUM | LOW | Watchdog auto-restart |

*Currently mitigated by single-threaded server

---

## Conclusion

The MTG Tournament Dashboard already has a solid foundation with automatic backup mechanisms. The improvements outlined in this plan address the remaining risks for 12-hour production operation:

1. **Phase 1 (Critical):** Makes the system truly production-ready with thread safety, persistence, and monitoring
2. **Phase 2 (High):** Adds user-facing improvements and robustness
3. **Phase 3 (Medium):** Nice-to-have monitoring and polish
4. **Phase 4 (Long-term):** Architectural improvements for scaling

### Final Recommendation for Your Situation:

Given your 3-5 day timeline, local PC deployment, and single-user operation, implement the **Recommended set (8-10 hours)**:

**Must-Have (5.5 hours):**
- Timer Persistence (1.2) - 30 min
- Backup Failure Alerts (1.3) - 3 hours
- Redundant Backups (1.4) - 1 hour
- Manual Backup Button (2.3) - 30 min
- Periodic Auto-Save (2.4) - 30 min

**Should-Have (2.5 hours):**
- Thread Safety (1.1) - 2 hours *(good practice even for single-user)*
- Timer Interval Cleanup (2.2) - 30 min

**Nice-to-Have (1-2 hours):**
- Flask Production Config (1.5) - 1 hour
- Silent Exception Fix (2.1) - 15 min
- Watchdog Script (3.5) - 15 min

With these improvements, **your risk level drops from MEDIUM to LOW** for 12-hour operation.

---

## Day-Of Event Checklist

### Before Event Starts:
- [ ] Disable Windows Updates and automatic restarts
- [ ] Disable sleep/hibernation mode
- [ ] Close unnecessary applications (browsers, Discord, etc.)
- [ ] Ensure laptop is plugged into power (not battery)
- [ ] Test backup/restore process one final time
- [ ] Clear old backup files to free disk space
- [ ] Open Python console where you can see logs
- [ ] Bookmark `http://127.0.0.1:5001` and `/health` endpoint

### During Event (Hourly):
- [ ] Check backup status indicator (top of dashboard)
- [ ] Glance at Python console for errors
- [ ] Verify disk space not running low
- [ ] Check timer is running correctly

### Critical Moments (Before Each Phase):
- [ ] **Before Round 4 ends:** Click "Save Backup Now"
- [ ] **Before Top 8 Cut:** Click "Save Backup Now"
- [ ] **Before Finals:** Click "Save Backup Now"

### If Server Crashes:
1. Don't panic - backups exist!
2. Restart: `python tournament_dashboard.py`
3. Server auto-restores from `tournament_state.json.bak`
4. Verify current round matches expectation
5. Continue tournament

### If Backup Fails:
1. Check disk space: `dir` (Windows) or `df -h` (Mac/Linux)
2. Check file permissions on `tournament_state.json.bak`
3. Manually navigate to backup location and verify file exists
4. If repeated failures, copy backup file to USB drive manually

---

## Emergency Recovery Procedures

### Scenario 1: PC Force Restarts (Windows Update)
1. Restart application: `python tournament_dashboard.py`
2. Auto-restore loads last backup
3. Verify current round and scores
4. If state looks wrong, check backup timestamps
5. Use Restore Backup button to try `.bak.1` or `.bak.2`

### Scenario 2: Corrupted Backup File
1. Stop application
2. Check for backup rotation files:
   - `tournament_state.json.bak.1` (previous)
   - `tournament_state.json.bak.2` (2 rounds ago)
3. Copy desired backup over main backup:
   ```bash
   copy tournament_state.json.bak.1 tournament_state.json.bak
   ```
4. Restart application

### Scenario 3: Lost Round Data
1. Check `score_history` for edited scores
2. Reference paper scoresheets if available
3. Use "Edit Table Results" to correct scores
4. Backup immediately after correction

### Scenario 4: Timer Shows Wrong Time
1. If timer is WAY off, check server uptime in logs
2. If needed, manually adjust by:
   - Pause timer
   - Restart server (timer resets)
   - Start timer fresh for current round
3. Consider adding announcement: "Timer reset, 50 minutes from now"

---

## Contact and Support

If you encounter issues not covered here:
1. Check Python console logs for error messages
2. Check backup file timestamps and sizes
3. Review [CLAUDE.md](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\CLAUDE.md) troubleshooting section
4. Check [README.md](c:\Users\cheah\Documents\MTG-Dashboard\mtg-dashboard-v1\README.md) troubleshooting section

**With the recommended improvements implemented, your tournament will run smoothly through all 12 hours!**
