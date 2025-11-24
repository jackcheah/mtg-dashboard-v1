# Data Persistence & Backup Guide

**Last Updated:** 2025-11-24  
**Version:** 2.1  
**Feature:** Auto-Save & Crash Recovery

---

## 🎯 Overview

The MTG Tournament Dashboard now includes **automatic data persistence** to protect your tournament data from Docker container crashes or restarts.

### What's Protected ✅

- ✅ **All tournament data** (teams, players, scores)
- ✅ **Round results** (all submitted rounds)
- ✅ **Tournament configuration** (Swiss rounds, structure)
- ✅ **Current state** (which rounds are completed)
- ✅ **Playoff data** (semifinals, finals)

### How It Works

1. **Auto-Save**: Data is automatically saved after every important operation
2. **Auto-Restore**: Data is automatically restored when container starts
3. **Persistent Storage**: Backup file is stored outside the container (survives restarts)

---

## 🔄 Auto-Save Triggers

The system automatically saves your tournament data after:

1. **Loading Participants** - After clicking "Load Participants"
2. **Setup Tournament** - After clicking "Setup Tournament"
3. **Submit Round Results** - After submitting scores for any round
4. **Manual Save** - Via API endpoint (optional)

### Console Messages

You'll see these messages in the logs:

```
✅ Auto-saved tournament state at 14:23:45
✅ Restored tournament state from backup (saved: 2025-11-24T14:23:45)
ℹ️ No backup file found - starting fresh
```

---

## 💾 Backup File Location

### Docker Deployment

**Backup File:** `./tournament_backups/tournament_backup.json`

This folder is **mounted from your host machine**, so the backup survives:
- ✅ Docker container restarts
- ✅ Docker container crashes
- ✅ `docker-compose restart`
- ✅ `docker-compose down` + `docker-compose up`

**Location on your computer:**
```
C:\Users\cheah\Documents\MTG-Dashboard\MTG-Tournament-Dashboard-AugmentCode\tournament_backups\
```

### Local Python Deployment

**Backup File:** `./tournament_backups/tournament_backup.json`

Same location, works the same way!

---

## 🚨 Recovery Scenarios

### Scenario 1: Docker Container Crashes

**What Happens:**
1. Container crashes during tournament
2. You run `docker-compose restart`
3. Container starts up
4. **Data is automatically restored** ✅
5. Continue tournament from where you left off!

**Steps:**
```powershell
# Container crashed - restart it
docker-compose restart

# Open browser
http://localhost:5000

# Your data is back! ✅
```

---

### Scenario 2: Accidental `docker-compose down`

**What Happens:**
1. You accidentally run `docker-compose down`
2. Container stops and is removed
3. You run `docker-compose up -d`
4. **Data is automatically restored** ✅
5. Continue tournament!

**Steps:**
```powershell
# Oops! Stopped the container
docker-compose down

# Start it again
docker-compose up -d

# Open browser
http://localhost:5000

# Your data is back! ✅
```

---

### Scenario 3: Computer Restart

**What Happens:**
1. Computer restarts (power outage, Windows update, etc.)
2. Docker Desktop starts automatically (if configured)
3. You run `docker-compose up -d`
4. **Data is automatically restored** ✅
5. Continue tournament!

**Steps:**
```powershell
# After computer restart
# 1. Start Docker Desktop (if not auto-started)
# 2. Navigate to project folder
cd C:\Users\cheah\Documents\MTG-Dashboard\MTG-Tournament-Dashboard-AugmentCode

# 3. Start container
docker-compose up -d

# 4. Open browser
http://localhost:5000

# Your data is back! ✅
```

---

### Scenario 4: Need to Rebuild Container

**What Happens:**
1. You need to rebuild with new code
2. You run `docker-compose down`
3. You run `docker-compose up -d --build`
4. **Data is automatically restored** ✅
5. Continue tournament with new code!

**Steps:**
```powershell
# Rebuild with latest code
docker-compose down
docker-compose up -d --build

# Open browser
http://localhost:5000

# Your data is back! ✅
```

---

## 🛡️ What's NOT Protected

### Data Loss Scenarios ⚠️

**You WILL lose data if:**

1. **Backup file is deleted**
   - If you manually delete `tournament_backups/tournament_backup.json`
   - Solution: Don't delete this file during tournament!

2. **Reset Tournament button clicked**
   - This intentionally clears all data AND deletes backup
   - Solution: Only use this when you want to start fresh

3. **Backup directory is deleted**
   - If you delete the entire `tournament_backups` folder
   - Solution: Don't delete this folder!

---

## 📊 Manual Backup (Optional)

### Save Backup Manually

You can manually trigger a backup save:

**Via API:**
```bash
curl -X POST http://localhost:5000/save_backup
```

**Response:**
```json
{
  "success": true,
  "message": "Tournament state saved successfully"
}
```

### When to Use Manual Backup

- Before making risky changes
- Before testing new features
- As extra safety during critical moments
- Before closing laptop/computer

---

## 🔍 Verify Backup Exists

### Check if Backup File Exists

**Windows:**
```powershell
dir tournament_backups\tournament_backup.json
```

**Should show:**
```
11/24/2025  02:30 PM            12,345 tournament_backup.json
```

### View Backup Contents

The backup file is JSON format - you can open it with any text editor:

```powershell
notepad tournament_backups\tournament_backup.json
```

**Example content:**
```json
{
  "timestamp": "2025-11-24T14:30:45.123456",
  "teams": {...},
  "scores": {...},
  "player_scores": {...},
  "current_round": 3,
  "swiss_rounds_count": 4,
  ...
}
```

---

## 🎮 Tournament Day Workflow

### Before Tournament

1. **Start Docker**
   ```powershell
   docker-compose up -d
   ```

2. **Load Participants**
   - Click "Load Participants"
   - ✅ Auto-saved!

3. **Setup Tournament**
   - Click "Setup Tournament"
   - ✅ Auto-saved!

4. **Verify Backup**
   ```powershell
   dir tournament_backups\tournament_backup.json
   ```

### During Tournament

1. **Submit Each Round**
   - Enter scores
   - Click "Submit Round Results"
   - ✅ Auto-saved after each round!

2. **If Container Crashes**
   ```powershell
   docker-compose restart
   ```
   - ✅ Data automatically restored!

3. **Continue Tournament**
   - No data loss!
   - Continue from where you left off

### After Tournament

1. **Optional: Keep Backup**
   - Copy `tournament_backups/tournament_backup.json` to safe location
   - Rename with tournament date: `tournament_2025-11-24.json`

2. **Reset for Next Tournament**
   - Click "Reset Tournament" button
   - Backup file is deleted
   - Ready for next event!

---

## 🔧 Troubleshooting

### Backup Not Restoring

**Problem:** Container starts but data is not restored

**Solutions:**
1. Check if backup file exists:
   ```powershell
   dir tournament_backups\tournament_backup.json
   ```

2. Check Docker logs for errors:
   ```powershell
   docker-compose logs | findstr backup
   ```

3. Look for these messages:
   - ✅ `Restored tournament state from backup`
   - ⚠️ `No backup file found - starting fresh`
   - ❌ `Warning: Could not restore backup`

### Backup File Corrupted

**Problem:** Backup file exists but won't restore

**Solutions:**
1. Check file is valid JSON:
   ```powershell
   notepad tournament_backups\tournament_backup.json
   ```

2. If corrupted, delete and start fresh:
   ```powershell
   del tournament_backups\tournament_backup.json
   ```

3. Reload participants and setup tournament again

### Backup Directory Not Created

**Problem:** `tournament_backups` folder doesn't exist

**Solutions:**
1. Create it manually:
   ```powershell
   mkdir tournament_backups
   ```

2. Restart container:
   ```powershell
   docker-compose restart
   ```

---

## ✅ Best Practices

### DO ✅

- ✅ Keep `tournament_backups` folder
- ✅ Let auto-save do its job
- ✅ Check backup file exists before tournament
- ✅ Test recovery before tournament day
- ✅ Keep Docker Desktop running during tournament

### DON'T ❌

- ❌ Delete `tournament_backups` folder during tournament
- ❌ Manually edit backup file
- ❌ Stop Docker Desktop during tournament
- ❌ Click "Reset Tournament" during active tournament

---

## 📈 Summary

**Data Persistence:** ✅ ENABLED  
**Auto-Save:** ✅ ACTIVE  
**Auto-Restore:** ✅ ACTIVE  
**Crash Recovery:** ✅ SUPPORTED  
**Tournament Day Ready:** ✅ YES!

Your tournament data is now protected! 🛡️


