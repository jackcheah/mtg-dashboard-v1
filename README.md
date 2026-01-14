# MTG Tournament Dashboard

A comprehensive web-based tournament management system for Magic: The Gathering (MTG) Commander (cEDH) tournaments. Supports Swiss-system rounds with automatic pairing, intelligent seating, and finals generation.

## Features

- **Swiss-System Management**: Supports 8, 12, or 16 teams (4 players per team).
- **Automated Workflow**: Automatic pairing (no repeats), intelligent seating (by score), and round generation.
- **Robust Scoring**: Track individual and team scores with a comprehensive tiebreaker system.
- **Production-Ready**: Automatic backups every 5 minutes, crash recovery, and thread-safe operations.
- **Modern UI**: Responsive "Ultra Modern" glassmorphism interface with dark mode.
- **Projector View**: Dedicated read-only display for audiences with champion and MVP showcases.

## System Requirements
- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Edge, Safari)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd MTG-Tournament-Dashboard
```

### 2. Install Dependencies
```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install flask openpyxl

# Windows
python -m venv venv
venv\Scripts\activate
pip install flask openpyxl
```

## Quick Start

### 1. Run the Application
```bash
# activate your venv first, then:
python tournament_dashboard.py
```
Access the dashboard at: **http://127.0.0.1:5001**

### 2. Tournament Workflow
1.  **Load Participants**: Click "Load Participants" (loads `participants/participant_team.xlsx` or sample data).
2.  **Setup**: Click "Setup Tournament" to generate Round 1.
3.  **Swiss Rounds**: 
    - Enter results (W/D/L) for each table. 
    - Click "Submit Table" -> "Submit Round". 
    - Repeat for 4 rounds.
4.  **Finals**: The system automatically generates Top 8 (for 16 teams) or Finals (for 8/12 teams).

### Key Shortcuts
- **W / 1**: Win
- **D / 2**: Draw
- **L / 3**: Loss
- **Tab**: Next input
- **Ctrl+Enter**: Submit Table
- **?**: View all shortcuts

## Configuration

### Custom Participants
To use your own roster, create an Excel file at `participants/participant_team.xlsx` with columns: `Player ID`, `Player Name`, `Team Name`.
- Teams must have exactly 4 players.
- Total teams must be 8, 12, or 16.

### Backups
The system automatically backs up state every 5 minutes.
- **Manual Backup**: Click "Save Backup" in the UI before critical rounds.
- **Restoration**: Just restart the server (`python tournament_dashboard.py`) to auto-restore the last valid state.

## Tournament Rules & Structure

### Structure
- **8 Teams**: 4 Swiss Rounds → Finals (Top 4)
- **12 Teams**: 4 Swiss Rounds → Finals (Top 4)
- **16 Teams**: 4 Swiss Rounds → Top 8 Cut → Finals (Top 4)

### Scoring
- **Win**: 5 pts | **Draw**: 1 pt | **Loss**: 0 pts
- **Advancement**: Based on current stage performance.
- **Tiebreakers**: Total Score → Best Player → Average Player → Early Wins.

## Troubleshooting

- **Round Not Generating**: Ensure all tables in the current round are submitted. Refresh the page.
- **App Not Loading**: Check if port 5001 is in use or the terminal window is closed.
- **Data Mismatch**: Restart the server to reload ground-truth state from the backup file.

## Credits
Developed for **Knights of Round Table** - cEDH Team Championship tournaments.
