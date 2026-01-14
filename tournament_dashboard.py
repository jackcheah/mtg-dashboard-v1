from flask import Flask, render_template, request, jsonify, send_from_directory
from openpyxl import load_workbook
import json
import random
from datetime import datetime
import os
from itertools import combinations
from enum import Enum
from functools import wraps
import threading
import time

app = Flask(__name__)

# Production configuration
app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload
    JSON_SORT_KEYS=False,  # Performance
    SEND_FILE_MAX_AGE_DEFAULT=0,  # No caching for dynamic content
    JSONIFY_PRETTYPRINT_REGULAR=False  # Smaller responses
)

# Tournament State Machine (Phase 3.4)
class TournamentState(Enum):
    """Enum representing the tournament lifecycle states."""
    INITIAL = "initial"                           # Server started, no data loaded
    PARTICIPANTS_LOADED = "participants_loaded"   # Participants loaded, not set up
    TOURNAMENT_SETUP = "tournament_setup"         # Tournament initialized, Round 1 ready
    SWISS_IN_PROGRESS = "swiss_in_progress"       # Swiss rounds being played
    SWISS_COMPLETE = "swiss_complete"             # All Swiss rounds completed
    TOP8_IN_PROGRESS = "top8_in_progress"         # Top 8 Cut in progress (16-team only)
    TOP8_COMPLETE = "top8_complete"               # Top 8 Cut completed (16-team only)
    FINALS_IN_PROGRESS = "finals_in_progress"     # Finals round in progress
    FINALS_COMPLETE = "finals_complete"           # Finals completed, champion determined

@app.route('/projector')
def projector_view():
    """Serve the read-only projector view"""
    return render_template('projector_view.html')

class TournamentManager:
    def __init__(self):
        self.participants = []
        self.teams = {}
        self.tournament_teams = []  # Single unified group of all teams (8, 12, or 16)
        self.scores = {}
        self.player_scores = {}  # Individual player scores
        self.current_round = 1
        self.swiss_rounds_count = 4  # Configurable: 4 or 5 Swiss rounds (default: 4)
        self.swiss_rounds_configured = False  # Track if configuration is set
        self.max_rounds = 6  # Will be recalculated: Swiss rounds + Semifinals (if 16 teams) + Finals
        self.round_results = {}
        self.tables = {}  # Table assignments for each round
        self.final_round_scores = {}  # Track final round scores separately
        self.semifinal_round_scores = {}  # Track semifinal round scores separately
        self.swiss_round_scores = {}  # Track Swiss rounds scores
        self.supported_team_counts = [8, 12, 16]  # Support 8, 12, or 16 teams
        self.max_teams = 16  # Maximum supported teams
        self.has_semifinals = False  # Track if tournament structure includes semifinals
        self.submitted_rounds = set()  # Track which rounds have been submitted
        self.finalized_rounds = set()  # Track which rounds have been finalized

        # State machine tracking (Phase 3.4)
        self.state = TournamentState.INITIAL
        self.state_history = []  # Track state transitions for debugging

        # Timer State
        self.timer_running = False
        self.timer_start_time = None
        self.timer_paused_at = 0  # Seconds elapsed when paused
        self.timer_duration = 3000 # Default 50 mins
        self.backup_file = 'tournament_state.json.bak'

        # Backup health tracking
        self.last_backup_success = None
        self.last_backup_failure = None
        self.consecutive_backup_failures = 0

    def transition_to(self, new_state: TournamentState, reason: str = ""):
        """Transition to a new state with logging (Phase 3.4)."""
        old_state = self.state
        self.state = new_state
        transition = {
            'from': old_state.value,
            'to': new_state.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.state_history.append(transition)
        print(f"[STATE] {old_state.value} → {new_state.value} ({reason})")


    def save_state(self, filepath='tournament_state.json.bak'):
        """
        Save tournament state to a JSON file.
        Uses a temporary file and atomic rename to prevent corruption.
        """
        def convert_sets_to_lists(obj):
            """Recursively convert sets to lists for JSON serialization."""
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_sets_to_lists(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets_to_lists(item) for item in obj]
            else:
                return obj

        try:
            # Rotate existing backups (keep last 3)
            for i in range(2, 0, -1):
                old_file = f"{filepath}.{i}"
                new_file = f"{filepath}.{i+1}"
                if os.path.exists(old_file):
                    try:
                        os.replace(old_file, new_file)
                    except Exception as e:
                        print(f"[BACKUP] Warning: Failed to rotate {old_file}: {e}")

            # Move current backup to .1
            if os.path.exists(filepath):
                try:
                    os.replace(filepath, f"{filepath}.1")
                except Exception as e:
                    print(f"[BACKUP] Warning: Failed to rotate current backup: {e}")

            # Convert sets to lists for JSON serialization
            submitted_rounds_list = list(self.submitted_rounds)
            finalized_rounds_list = list(self.finalized_rounds)
            # Convert nested sets in round_results (e.g., submitted_tables)
            round_results_serializable = convert_sets_to_lists(self.round_results)

            state = {
                "version": "2.0",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "swiss_rounds_count": self.swiss_rounds_count,
                    "max_rounds": self.max_rounds,
                    "has_semifinals": self.has_semifinals,
                    "swiss_rounds_configured": self.swiss_rounds_configured,
                    "supported_team_counts": self.supported_team_counts
                },
                "state": {
                    "current_round": self.current_round,
                    "submitted_rounds": submitted_rounds_list,
                    "finalized_rounds": finalized_rounds_list,
                    "tournament_state": self.state.value
                },
                "timer": {
                    "running": self.timer_running,
                    "start_time": self.timer_start_time.isoformat() if self.timer_start_time else None,
                    "paused_at": self.timer_paused_at,
                    "duration": self.timer_duration
                },
                "data": {
                    "teams": self.teams,
                    "participants": self.participants,
                    "tournament_teams": self.tournament_teams,
                    "scores": self.scores,
                    "player_scores": self.player_scores,
                    "tables": self.tables,
                    "round_results": round_results_serializable,
                    "_tournament_rounds": getattr(self, '_tournament_rounds', []),
                    "finals_data": getattr(self, 'finals_data', {}),
                    "semifinals": getattr(self, 'semifinals', {})
                }
            }
            
            # Save to temporary file first
            temp_path = filepath + '.tmp'
            with open(temp_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Atomic rename (or replace)
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)

            # Track backup success
            self.last_backup_success = datetime.now()
            self.consecutive_backup_failures = 0
            print(f"[BACKUP] Tournament state saved successfully to {filepath}")
            return True

        except Exception as e:
            # Track backup failure
            self.last_backup_failure = datetime.now()
            self.consecutive_backup_failures += 1
            print(f"[ERROR] Failed to save backup: {e}")
            print(f"[ERROR] Consecutive failures: {self.consecutive_backup_failures}")
            import traceback
            traceback.print_exc()
            return False

    def load_state(self, filepath='tournament_state.json.bak'):
        """
        Load tournament state from JSON file and restore pairing engine.
        Replays round history to rebuild internal constraint state.
        """
        if not os.path.exists(filepath):
            print(f"[BACKUP] No backup file found at {filepath}")
            return False

        try:
            print(f"[BACKUP] Loading state from {filepath}...")
            with open(filepath, 'r') as f:
                state_data = json.load(f)
            
            # Restore Configuration
            config = state_data.get('config', {})
            self.swiss_rounds_count = config.get('swiss_rounds_count', 4)
            self.max_rounds = config.get('max_rounds', 6)
            self.has_semifinals = config.get('has_semifinals', False)
            self.swiss_rounds_configured = config.get('swiss_rounds_configured', False)
            
            # Restore State
            state = state_data.get('state', {})
            self.current_round = state.get('current_round', 1)
            
            # [SELF-HEALING] Fix current_round if it's stale (e.g. backend restart but tables exist for later rounds)
            try:
                raw_tables = state_data.get('data', {}).get('tables', {})
                max_table_round = 1
                for r in raw_tables:
                    if str(r).isdigit():
                        max_table_round = max(max_table_round, int(r))
                
                if self.state != TournamentState.INITIAL and max_table_round > self.current_round:
                    print(f"[RECOVERY] Healing current_round mismatch: State says {self.current_round}, Tables say {max_table_round}")
                    self.current_round = max_table_round
            except Exception as e:
                print(f"[RECOVERY] Failed to self-heal round: {e}")

            self.submitted_rounds = set(state.get('submitted_rounds', []))
            self.submitted_rounds = set(state.get('submitted_rounds', []))
            self.finalized_rounds = set(state.get('finalized_rounds', []))
            
            # Restore Enum State
            saved_state_str = state.get('tournament_state', 'initial')
            try:
                # Find matching enum
                for s in TournamentState:
                    if s.value == saved_state_str:
                        self.state = s
                        break
            except (ValueError, AttributeError, KeyError) as e:
                print(f"[ERROR] Failed to restore state enum '{saved_state_str}': {e}")
                self.state = TournamentState.INITIAL

            # Restore Timer State
            timer_data = state_data.get('timer', {})
            self.timer_running = timer_data.get('running', False)
            start_time_str = timer_data.get('start_time')
            self.timer_start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
            self.timer_paused_at = timer_data.get('paused_at', 0)
            self.timer_duration = timer_data.get('duration', 3000)
            print(f"[BACKUP] Timer restored: running={self.timer_running}, paused_at={self.timer_paused_at}s")

            # Restore Data
            data = state_data.get('data', {})
            self.teams = data.get('teams', {})
            self.participants = data.get('participants', [])
            self.tournament_teams = data.get('tournament_teams', [])
            self.scores = data.get('scores', {})
            
            # Fix integer keys for player_scores and tables (JSON converts keys to strings)
            raw_player_scores = data.get('player_scores', {})
            self.player_scores = {int(k) if k.isdigit() else k: v for k, v in raw_player_scores.items()}
            
            raw_tables = data.get('tables', {})
            self.tables = {int(k) if k.isdigit() else k: v for k, v in raw_tables.items()}
            
            raw_round_results = data.get('round_results', {})
            self.round_results = {int(k) if k.isdigit() else k: v for k, v in raw_round_results.items()}
            
            self._tournament_rounds = data.get('_tournament_rounds', [])
            self.finals_data = data.get('finals_data', {})
            self.semifinals = data.get('semifinals', {})
            
            # === CRITICAL: REHYDRATE PAIRING ENGINE ===
            # We must recreate the UnifiedSwissPairing instance and replay the history
            # so it knows which players/teams have already faced each other.
            
            if self.tournament_teams:
                print("[BACKUP] Rehydrating Swiss Pairing Engine...")
                from unified_swiss_pairing import UnifiedSwissPairing
                
                # Initialize fresh engine
                self._unified_pairing = UnifiedSwissPairing(
                    self.teams, 
                    self.tournament_teams,
                    self.swiss_rounds_count, 
                    self.scores
                )
                
                # Replay history
                if self._tournament_rounds:
                    print(f"[BACKUP] Replaying {len(self._tournament_rounds)} rounds of history...")
                    for round_idx, round_solution in enumerate(self._tournament_rounds):
                        # The engine updates its internal sets (constraints) based on this solution
                        self._unified_pairing._update_constraints_after_round(round_solution)
                        # Also add it to the engine's internal memory of solutions if needed
                        self._unified_pairing.round_solutions.append(round_solution)
                    
                    print("[BACKUP] Engine rehydration complete.")
                else:
                    print("[BACKUP] No round history to replay.")
            
            print(f"[BACKUP] Tournament state restored successfully!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to restore backup: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_backup(self):
        """Legacy method wrapper"""
        return self.save_state()

    def load_backup(self, filepath):
        """Legacy method wrapper"""
        return self.load_state(filepath)

    def configure_swiss_rounds(self, rounds):
        """
        Configure the number of Swiss rounds before tournament setup.
        Can be called multiple times before teams are loaded.

        Args:
            rounds (int): Number of Swiss rounds (4 or 5)

        Returns:
            tuple: (success: bool, message: str)
        """
        # Allow reconfiguration if teams haven't been loaded yet
        if self.swiss_rounds_configured and self.teams:
            return False, "Swiss rounds already configured and teams loaded. Cannot change after loading participants."

        if rounds not in [4, 5]:
            return False, "Swiss rounds must be either 4 or 5."

        self.swiss_rounds_count = rounds
        self.swiss_rounds_configured = True

        # Determine if semifinals are needed based on team count
        # This will be finalized when teams are loaded
        # For now, just configure Swiss rounds
        self.max_rounds = self.swiss_rounds_count + 2  # Placeholder: Swiss + Semifinals + Finals

        print(f"[OK] Swiss rounds configured: {self.swiss_rounds_count} rounds")
        print(f"[OK] Tournament structure will be determined when teams are loaded")

        return True, f"Configured for {self.swiss_rounds_count} Swiss rounds"

    def determine_tournament_structure(self):
        """Determine tournament structure based on team count

        Rules:
        - 8 teams: 4 Swiss rounds -> Finals (top 4)
        - 12 teams: 4 Swiss rounds -> Finals (top 4)
        - 16 teams: 4 Swiss rounds -> Top 8 Cut (8 pods) -> Finals (top 4)

        Note: Repeat matchups may occur in 8 and 12 team tournaments
        """
        team_count = len(self.teams)

        if team_count in [8, 12]:
            # 8 or 12 teams: 4 Swiss rounds -> Direct to Finals (top 4)
            if not self.swiss_rounds_configured:
                self.swiss_rounds_count = 4  # Default: 4 Swiss rounds
            self.has_semifinals = False
            self.max_rounds = self.swiss_rounds_count + 1  # Swiss + Finals

            print(f"[OK] Tournament structure: {team_count} teams")
            print(f"  - Swiss rounds: {self.swiss_rounds_count}")
            print(f"  - Top 8 Cut: NO (top 4 teams advance directly to Finals)")
            print(f"  - Finals: YES (top 4 teams, 4 pods)")
            print(f"  - Total rounds: {self.max_rounds}")
            if team_count in [8, 12]:
                print(f"  [WARNING]  Note: Some repeat matchups may occur during Swiss rounds")

        elif team_count == 16:
            # 16 teams: 4 Swiss rounds -> Top 8 Cut -> Finals
            if not self.swiss_rounds_configured:
                self.swiss_rounds_count = 4  # Default: 4 Swiss rounds
            self.has_semifinals = True  # "Top 8 Cut" uses the semifinals logic
            self.max_rounds = self.swiss_rounds_count + 2  # Swiss + Top8Cut + Finals

            print(f"[OK] Tournament structure: {team_count} teams")
            print(f"  - Swiss rounds: {self.swiss_rounds_count}")
            print(f"  - Top 8 Cut: YES (top 8 teams, 8 pods)")
            print(f"  - Finals: YES (top 4 teams, 4 pods)")
            print(f"  - Total rounds: {self.max_rounds}")

        else:
            print(f"[WARNING]  Unsupported team count: {team_count}")
            print(f"   Supported: 8, 12, or 16 teams")
            return False

        return True

    def load_participants(self, excel_file):
        """Load participants from Excel file using openpyxl"""
        try:
            workbook = load_workbook(excel_file)
            sheet = workbook.active  # Get the active sheet
            
            # Read headers from first row
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(cell.value)
            
            # Initialize teams and participants
            self.teams = {}
            self.participants = []
            
            # Check if headers look like team names (not standard column names)
            standard_columns = ['Team Name', 'Player ID', 'Player Name', 'team_name', 'player_id', 'name']
            has_standard_columns = any(header in standard_columns for header in headers if header)
            
            if not has_standard_columns and len(headers) > 0:
                # Headers appear to be team names - read data vertically under each team
                for col_idx, team_name in enumerate(headers):
                    if team_name and str(team_name).strip():
                        team_name = str(team_name).strip()
                        self.teams[team_name] = []
                        
                        # Read players from this column (only first 4 players, exclude reserves)
                        player_count = 0
                        for row_idx in range(2, sheet.max_row + 1):
                            if player_count >= 4:  # Only take first 4 players
                                break
                                
                            cell_value = sheet.cell(row=row_idx, column=col_idx + 1).value
                            if cell_value and str(cell_value).strip():
                                player_name = str(cell_value).strip()
                                
                                # Skip reserve players
                                if 'reserve' in player_name.lower():
                                    continue
                                
                                participant = {
                                    'Team Name': team_name,
                                    'Player Name': player_name,
                                    'Player ID': len(self.participants) + 1
                                }
                                self.teams[team_name].append(participant)
                                self.participants.append(participant)
                                player_count += 1
            else:
                # Standard column format - original logic with 4 player limit
                team_player_counts = {}
                
                for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
                    if row[0] is not None:  # Skip empty rows
                        participant = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                participant[header] = row[i]
                        
                        # Check if this is a reserve player
                        player_name = participant.get('Player Name', '')
                        if 'reserve' in str(player_name).lower():
                            continue
                        
                        team_name = (participant.get('Team Name') or 
                                    participant.get('Team') or 
                                    participant.get('team_name') or 
                                    participant.get('team') or 
                                    'Unknown Team')
                        
                        # Limit to 4 players per team
                        if team_name not in team_player_counts:
                            team_player_counts[team_name] = 0
                        
                        if team_player_counts[team_name] < 4:
                            self.participants.append(participant)
                            team_player_counts[team_name] += 1
                
                # Organize by teams
                for participant in self.participants:
                    team_name = (participant.get('Team Name') or 
                                participant.get('Team') or 
                                participant.get('team_name') or 
                                participant.get('team') or 
                                'Unknown Team')
                    
                    if team_name not in self.teams:
                        self.teams[team_name] = []
                    self.teams[team_name].append(participant)
            
            # Sort teams by player ID within each team
            for team_name in self.teams:
                self.teams[team_name].sort(key=lambda x: x.get('Player ID', x.get('player_id', x.get('ID', 0))))
            
            # Initialize scores
            self.scores = {team: 0 for team in self.teams.keys()}
            self.player_scores = {}
            for participant in self.participants:
                player_id = participant.get('Player ID')
                self.player_scores[player_id] = 0
            
        except Exception as e:
            print(f"Error loading participants: {e}")
            import traceback
            traceback.print_exc()
            # Create sample data for testing
            self.create_sample_data()
            # Determine tournament structure after creating sample data
            self.determine_tournament_structure()
            return True  # Return true since we have sample data

        print(f"Successfully loaded {len(self.teams)} teams with {len(self.participants)} participants")

        # Determine tournament structure based on team count
        self.determine_tournament_structure()

        return True
    
    def create_sample_data(self, num_teams=8):
        """Create sample data if Excel file can't be loaded

        Args:
            num_teams: Number of teams to create (8, 12, or 16, default: 8)
        """
        all_teams = {
            'Team Alpha': [
                {'Player ID': 1, 'Player Name': 'Alice', 'Team Name': 'Team Alpha'},
                {'Player ID': 2, 'Player Name': 'Bob', 'Team Name': 'Team Alpha'},
                {'Player ID': 3, 'Player Name': 'Charlie', 'Team Name': 'Team Alpha'},
                {'Player ID': 4, 'Player Name': 'Diana', 'Team Name': 'Team Alpha'}
            ],
            'Team Beta': [
                {'Player ID': 5, 'Player Name': 'Eve', 'Team Name': 'Team Beta'},
                {'Player ID': 6, 'Player Name': 'Frank', 'Team Name': 'Team Beta'},
                {'Player ID': 7, 'Player Name': 'Grace', 'Team Name': 'Team Beta'},
                {'Player ID': 8, 'Player Name': 'Henry', 'Team Name': 'Team Beta'}
            ],
            'Team Gamma': [
                {'Player ID': 9, 'Player Name': 'Iris', 'Team Name': 'Team Gamma'},
                {'Player ID': 10, 'Player Name': 'Jack', 'Team Name': 'Team Gamma'},
                {'Player ID': 11, 'Player Name': 'Kate', 'Team Name': 'Team Gamma'},
                {'Player ID': 12, 'Player Name': 'Leo', 'Team Name': 'Team Gamma'}
            ],
            'Team Delta': [
                {'Player ID': 13, 'Player Name': 'Mia', 'Team Name': 'Team Delta'},
                {'Player ID': 14, 'Player Name': 'Noah', 'Team Name': 'Team Delta'},
                {'Player ID': 15, 'Player Name': 'Olivia', 'Team Name': 'Team Delta'},
                {'Player ID': 16, 'Player Name': 'Paul', 'Team Name': 'Team Delta'}
            ],
            'Team Epsilon': [
                {'Player ID': 17, 'Player Name': 'Quinn', 'Team Name': 'Team Epsilon'},
                {'Player ID': 18, 'Player Name': 'Rose', 'Team Name': 'Team Epsilon'},
                {'Player ID': 19, 'Player Name': 'Sam', 'Team Name': 'Team Epsilon'},
                {'Player ID': 20, 'Player Name': 'Tina', 'Team Name': 'Team Epsilon'}
            ],
            'Team Zeta': [
                {'Player ID': 21, 'Player Name': 'Uma', 'Team Name': 'Team Zeta'},
                {'Player ID': 22, 'Player Name': 'Victor', 'Team Name': 'Team Zeta'},
                {'Player ID': 23, 'Player Name': 'Wendy', 'Team Name': 'Team Zeta'},
                {'Player ID': 24, 'Player Name': 'Xavier', 'Team Name': 'Team Zeta'}
            ],
            'Team Eta': [
                {'Player ID': 25, 'Player Name': 'Yara', 'Team Name': 'Team Eta'},
                {'Player ID': 26, 'Player Name': 'Zack', 'Team Name': 'Team Eta'},
                {'Player ID': 27, 'Player Name': 'Amy', 'Team Name': 'Team Eta'},
                {'Player ID': 28, 'Player Name': 'Ben', 'Team Name': 'Team Eta'}
            ],
            'Team Theta': [
                {'Player ID': 29, 'Player Name': 'Cora', 'Team Name': 'Team Theta'},
                {'Player ID': 30, 'Player Name': 'Dan', 'Team Name': 'Team Theta'},
                {'Player ID': 31, 'Player Name': 'Ella', 'Team Name': 'Team Theta'},
                {'Player ID': 32, 'Player Name': 'Felix', 'Team Name': 'Team Theta'}
            ],
            'Team Iota': [
                {'Player ID': 33, 'Player Name': 'Gina', 'Team Name': 'Team Iota'},
                {'Player ID': 34, 'Player Name': 'Hugo', 'Team Name': 'Team Iota'},
                {'Player ID': 35, 'Player Name': 'Ivy', 'Team Name': 'Team Iota'},
                {'Player ID': 36, 'Player Name': 'Jake', 'Team Name': 'Team Iota'}
            ],
            'Team Kappa': [
                {'Player ID': 37, 'Player Name': 'Kara', 'Team Name': 'Team Kappa'},
                {'Player ID': 38, 'Player Name': 'Liam', 'Team Name': 'Team Kappa'},
                {'Player ID': 39, 'Player Name': 'Maya', 'Team Name': 'Team Kappa'},
                {'Player ID': 40, 'Player Name': 'Nick', 'Team Name': 'Team Kappa'}
            ],
            'Team Lambda': [
                {'Player ID': 41, 'Player Name': 'Ola', 'Team Name': 'Team Lambda'},
                {'Player ID': 42, 'Player Name': 'Pete', 'Team Name': 'Team Lambda'},
                {'Player ID': 43, 'Player Name': 'Quin', 'Team Name': 'Team Lambda'},
                {'Player ID': 44, 'Player Name': 'Rita', 'Team Name': 'Team Lambda'}
            ],
            'Team Mu': [
                {'Player ID': 45, 'Player Name': 'Sara', 'Team Name': 'Team Mu'},
                {'Player ID': 46, 'Player Name': 'Tom', 'Team Name': 'Team Mu'},
                {'Player ID': 47, 'Player Name': 'Una', 'Team Name': 'Team Mu'},
                {'Player ID': 48, 'Player Name': 'Vince', 'Team Name': 'Team Mu'}
            ],
            'Team Nu': [
                {'Player ID': 49, 'Player Name': 'Wanda', 'Team Name': 'Team Nu'},
                {'Player ID': 50, 'Player Name': 'Xander', 'Team Name': 'Team Nu'},
                {'Player ID': 51, 'Player Name': 'Yvonne', 'Team Name': 'Team Nu'},
                {'Player ID': 52, 'Player Name': 'Zane', 'Team Name': 'Team Nu'}
            ],
            'Team Xi': [
                {'Player ID': 53, 'Player Name': 'Anna', 'Team Name': 'Team Xi'},
                {'Player ID': 54, 'Player Name': 'Brad', 'Team Name': 'Team Xi'},
                {'Player ID': 55, 'Player Name': 'Cara', 'Team Name': 'Team Xi'},
                {'Player ID': 56, 'Player Name': 'Dave', 'Team Name': 'Team Xi'}
            ],
            'Team Omicron': [
                {'Player ID': 57, 'Player Name': 'Emma', 'Team Name': 'Team Omicron'},
                {'Player ID': 58, 'Player Name': 'Fred', 'Team Name': 'Team Omicron'},
                {'Player ID': 59, 'Player Name': 'Gail', 'Team Name': 'Team Omicron'},
                {'Player ID': 60, 'Player Name': 'Hank', 'Team Name': 'Team Omicron'}
            ],
            'Team Pi': [
                {'Player ID': 61, 'Player Name': 'Iris', 'Team Name': 'Team Pi'},
                {'Player ID': 62, 'Player Name': 'John', 'Team Name': 'Team Pi'},
                {'Player ID': 63, 'Player Name': 'Kelly', 'Team Name': 'Team Pi'},
                {'Player ID': 64, 'Player Name': 'Luke', 'Team Name': 'Team Pi'}
            ]
        }

        # Select the appropriate number of teams
        if num_teams == 8:
            sample_teams = dict(list(all_teams.items())[:8])
        elif num_teams == 12:
            sample_teams = dict(list(all_teams.items())[:12])
        elif num_teams == 16:
            sample_teams = all_teams
        else:
            # Default to 8 teams
            sample_teams = dict(list(all_teams.items())[:8])

        self.teams = sample_teams
        self.tournament_teams = list(sample_teams.keys())
        self.scores = {team: 0 for team in self.teams.keys()}
        self.participants = []
        self.player_scores = {}
        for team_name, players in sample_teams.items():
            for player in players:
                self.participants.append(player)
                self.player_scores[player['Player ID']] = 0
    
    def setup_tournament(self, swiss_rounds=None):
        """Setup tournament with exactly 8, 12, or 16 teams in a single unified group"""
        
        # Set Swiss rounds count if provided
        if swiss_rounds is not None:
            if swiss_rounds not in [3, 4, 5]:
                return False, "Swiss rounds must be 3, 4, or 5"
            self.swiss_rounds_count = swiss_rounds
            self.swiss_rounds_configured = True
        
        # STRICT VALIDATION: Only 8, 12, or 16 teams allowed
        if len(self.teams) not in [8, 12, 16]:
            error_msg = (
                f"Tournament only supports exactly 8, 12, or 16 teams. "
                f"Current teams loaded: {len(self.teams)}. "
                f"Please adjust your participant list to have exactly "
                f"8 teams (32 players), 12 teams (48 players), or "
                f"16 teams (64 players)."
            )
            print(f"[X] VALIDATION FAILED: {error_msg}")
            return False, error_msg

        # Auto-configure tournament structure based on team count
        success = self.determine_tournament_structure()
        if not success:
            return False, f"Failed to determine tournament structure for {len(self.teams)} teams"

        # Log tournament configuration (optimal configuration confirmed)
        print(f"[OK] Tournament configuration: {len(self.teams)} teams (OPTIMAL), {self.swiss_rounds_count} Swiss rounds")
        print(f"[OK] All teams will compete in ONE unified tournament group")
        print(f"[OK] Pods per round: {len(self.teams)} (4 players each)")
        print(f"[OK] This configuration guarantees perfect pairings with zero repeat matchups")
        
        # RESET ALL TOURNAMENT STATE for fresh start
        print("[ROTATING] RESETTING tournament state for new tournament...")
        self.scores = {team: 0 for team in self.teams}
        self.player_scores = {}
        for participant in self.participants:
            player_id = participant.get('Player ID')
            self.player_scores[player_id] = 0
        
        self.round_results = {}
        self.tables = {}

        # Clear finalized and submitted rounds tracking
        if hasattr(self, 'finalized_rounds'):
            self.finalized_rounds = set()
        if hasattr(self, 'submitted_rounds'):
            self.submitted_rounds = set()
            
        # Reset unified pairing engine
        self._unified_pairing = None
        self._tournament_rounds = []

        print("[OK] Tournament state reset complete")
        
        # Get all team names and randomize them
        team_names = list(self.teams.keys())
        random.shuffle(team_names)
        
        # Use all teams in a single tournament (no artificial limits)
        self.tournament_teams = team_names
        
        print(f"Tournament Teams ({len(self.tournament_teams)}): {self.tournament_teams}")

        print(f"=== GENERATING ROUND 1 (subsequent rounds generated after results) ===")

        # Generate only Round 1 - subsequent rounds will be generated after results are submitted
        try:
            success = self.generate_swiss_round(1)

            if success:
                print(f"[OK] Round 1 generated successfully!")
                print(f"   Remaining rounds will be generated after each round's results are submitted.")
                print(f"   This ensures proper Swiss pairing based on current standings.")
                return True, f"Tournament setup complete with {len(self.tournament_teams)} teams. Round 1 is ready!"
            else:
                print("[X] Failed to generate Round 1")
                return False, "Failed to generate Round 1. Please try setup again."
        except Exception as e:
            print(f"[X] Error during tournament generation: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error generating tournament: {str(e)}"
    
    def generate_all_swiss_rounds(self):
        """Generate all Swiss rounds using the unified algorithm"""
        from unified_swiss_pairing import UnifiedSwissPairing
        
        print(f"Generating complete Swiss tournament for {len(self.tournament_teams)} teams...")
        print(f"Tournament teams: {self.tournament_teams}")
        print(f"Swiss rounds: {self.swiss_rounds_count}")
        
        try:
            # Create unified Swiss pairing system with team scores for score-based pairing
            unified_pairing = UnifiedSwissPairing(self.teams, self.tournament_teams,
                                                 self.swiss_rounds_count, self.scores)

            # Generate all rounds
            success, solution = unified_pairing.generate_all_rounds()
            
            if not success:
                print("[X] Failed to generate Swiss tournament")
                return False
            
            # Validate the solution
            validation_report = unified_pairing.validate_solution(solution)
            
            # Get statistics
            stats = unified_pairing.get_detailed_statistics()
            
            print(f"[OK] Tournament generated successfully!")
            print(f"  Perfect tournament: {validation_report.is_perfect}")
            print(f"  Total violations: {validation_report.total_violations}")
            print(f"  Pairing efficiency: {stats.pairing_efficiency:.1f}%")
            print(f"  Generation time: {stats.generation_time:.2f} seconds")
            
            # Store the solution
            self._tournament_rounds = solution
            
            # Organize rounds into tables structure
            self.organize_rounds_into_tables()
            
            return True
            
        except Exception as e:
            print(f"[X] Error during tournament generation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def generate_swiss_round(self, round_num: int) -> bool:
        """
        Generate a single Swiss round based on current standings.
        This is the proper Swiss pairing approach - each round is generated
        after the previous round's results are known.

        Args:
            round_num: The round number to generate (1-based)

        Returns:
            True if successful, False otherwise
        """
        from unified_swiss_pairing import UnifiedSwissPairing

        print(f"Generating Swiss Round {round_num} for {len(self.tournament_teams)} teams...")
        print(f"   Current team scores: {self.scores}")

        try:
            # Initialize or get the pairing system
            if not hasattr(self, '_unified_pairing') or self._unified_pairing is None:
                # First round - create new pairing system
                self._unified_pairing = UnifiedSwissPairing(
                    self.teams, self.tournament_teams,
                    self.swiss_rounds_count, self.scores
                )
                self._tournament_rounds = []
            else:
                # Update team scores for subsequent rounds
                self._unified_pairing.update_team_scores(self.scores)

            # Generate this specific round
            success, round_solution = self._unified_pairing.generate_single_round(round_num)

            if not success:
                print(f"[X] Failed to generate Round {round_num}")
                return False

            # Add to tournament rounds
            self._tournament_rounds.append(round_solution)

            # Organize this round into tables structure
            self._organize_single_round_into_tables(round_num, round_solution)

            print(f"[OK] Round {round_num} generated successfully!")
            return True

        except Exception as e:
            print(f"[X] Error generating Round {round_num}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _organize_single_round_into_tables(self, round_num: int, round_solution: list):
        """
        Organize a single round's pods into the tables structure.

        Args:
            round_num: The round number
            round_solution: List of pods for this round
        """
        self.tables[round_num] = {}

        for table_idx, pod in enumerate(round_solution, 1):
            if round_num == 1:
                # Round 1: Random seating
                print(f"   Round {round_num}, Table {table_idx}: Random seating (no prior scores)")
                random.shuffle(pod)
            else:
                # Rounds 2+: Sort by individual player score (highest first)
                # Best player from each team faces best players from other teams
                pod.sort(key=lambda p: self.player_scores.get(p['Player ID'], 0), reverse=True)
                print(f"   Round {round_num}, Table {table_idx}: Intelligent seating (individual score-based)")
                seating_str = " | ".join([f"Seat {i+1}: {p['Player Name']} ({self.player_scores.get(p['Player ID'], 0)}pts)"
                                        for i, p in enumerate(pod)])
                print(f"      Seating: {seating_str}")

                print(f"      Seating: {seating_str}")

            table_name = f"Table {table_idx}"
            self.tables[round_num][table_name] = pod

        print(f"[OK] Round {round_num}: {len(round_solution)} tables organized")


    def _validate_group_rounds(self, round_pairings, group_name):
        """Validate that the generated rounds have no repeat matchups"""
        print(f"  Validating {group_name} rounds...")
        
        seen_pairs = set()
        duplicate_violations = 0
        teammate_violations = 0
        
        for rnd, pods in enumerate(round_pairings, 1):
            for pod_idx, pod in enumerate(pods, 1):
                # Check teammates
                teams_in_pod = {player['Team Name'] for player in pod}
                if len(teams_in_pod) < 4:
                    teammate_violations += 1
                    print(f"    [WARNING]  Round {rnd} Pod {pod_idx}: Teammate violation - Teams: {list(teams_in_pod)}")
                
                # Check duplicate matchups
                for a, b in combinations(pod, 2):
                    pair = tuple(sorted([a['Player ID'], b['Player ID']]))
                    if pair in seen_pairs:
                        duplicate_violations += 1
                        print(f"    [WARNING]  Round {rnd} Pod {pod_idx}: Duplicate pairing - {a['Player Name']} vs {b['Player Name']}")
                    seen_pairs.add(pair)
        
        print(f"  Validation results for {group_name}:")
        print(f"    Teammate violations: {teammate_violations}")
        print(f"    Duplicate violations: {duplicate_violations}")
        print(f"    Total unique pairings: {len(seen_pairs)}")
        print(f"    Expected pairings: {4 * 4 * 6} (4 rounds × 4 pods × 6 pairs per pod)")
        
        if duplicate_violations == 0 and teammate_violations == 0:
            print(f"    [OK] {group_name}: PERFECT - No violations found!")
        else:
            print(f"    [ERROR] {group_name}: {teammate_violations + duplicate_violations} total violations")
    
    def organize_rounds_into_tables(self):
        """Organize the generated rounds into the tables structure with intelligent seating

        Round 1: Random seating (no prior scores)
        Rounds 2+: Score-based seating (higher team score -> Seat 1)
        """
        for round_num in range(1, self.swiss_rounds_count + 1):
            self.tables[round_num] = {}
            round_index = round_num - 1

            # Tournament tables
            if hasattr(self, '_tournament_rounds') and round_index < len(self._tournament_rounds):
                tournament_pods = self._tournament_rounds[round_index]
                for pod_idx, pod in enumerate(tournament_pods):
                    table_name = f'Table {pod_idx + 1}'

                    # Round 1: Random seating (no prior scores)
                    if round_num == 1:
                        shuffled_pod = pod.copy()
                        random.shuffle(shuffled_pod)
                        self.tables[round_num][table_name] = shuffled_pod
                        
                        # Log to verify randomization
                        if pod_idx < 3:
                            t_names = [p.get('Team Name', '') for p in shuffled_pod]
                            print(f"   Round 1, {table_name}: Random seating -> {t_names}")
                            
                        print(f"   Round {round_num}, {table_name}: Random seating (no prior scores)")
                    else:
                        # Rounds 2+: Intelligent seating based on team scores
                        sorted_pod = self._apply_intelligent_seating(pod, round_num)
                        self.tables[round_num][table_name] = sorted_pod
                        print(f"   Round {round_num}, {table_name}: Intelligent seating (score-based)")

        print(f"[OK] Organized all rounds into tables structure with intelligent seating")
        print(f"[OK] Tournament ready: {len(self.tables)} rounds with {len(self.tables[1]) if self.tables else 0} tables each")

    def _apply_intelligent_seating(self, pod, round_num):
        """Apply intelligent seating: higher individual player score -> Seat 1

        Args:
            pod: List of player dictionaries
            round_num: Current round number (for score calculation)

        Returns:
            List of players sorted by individual player score (descending)
        """
        # Sort pod by individual player score (descending)
        # Best players get better seats (Seat 1, 2, 3, 4)
        sorted_pod = sorted(pod, key=lambda p: self.player_scores.get(p['Player ID'], 0), reverse=True)

        # Debug output
        if sorted_pod:
            seat_info = []
            for idx, player in enumerate(sorted_pod):
                player_name = player['Player Name']
                player_score = self.player_scores.get(player['Player ID'], 0)
                seat_info.append(f"Seat {idx+1}: {player_name} ({player_score}pts)")
            print(f"      Seating: {' | '.join(seat_info)}")

        return sorted_pod

    def apply_intelligent_seating_to_round(self, round_num):
        """Apply intelligent seating to a round based on current scores

        Round 1: Random seating (no prior scores)
        Rounds 2+: Score-based seating (higher individual player score -> Seat 1)

        Args:
            round_num: Round number to apply seating to

        Returns:
            Dictionary of tables with intelligently seated players
        """
        if round_num not in self.tables:
            return {}

        seated_tables = {}

        for table_name, players in self.tables[round_num].items():
            if round_num == 1:
                # Round 1: Keep random seating
                seated_tables[table_name] = players
            else:
                # Rounds 2+: Apply intelligent seating based on individual player scores
                # Sort players by individual player score (descending)
                sorted_players = sorted(players, key=lambda p: self.player_scores.get(p['Player ID'], 0), reverse=True)
                seated_tables[table_name] = sorted_players

        return seated_tables
    
    def get_player_opponents(self, player_id, through_round):
        """Get list of opponents a player has faced through a given round"""
        opponents = set()
        
        for round_num in range(1, through_round + 1):
            if round_num in self.tables:
                # Find which table this player was at
                for table_name, players in self.tables[round_num].items():
                    player_ids_at_table = [p['Player ID'] for p in players]
                    if player_id in player_ids_at_table:
                        # Add all other players at this table as opponents
                        for pid in player_ids_at_table:
                            if pid != player_id:
                                opponents.add(pid)
                        break
        
        return list(opponents)
    
    def validate_swiss_pairings(self, round_num):
        """Validate that Swiss pairing rules are followed"""
        issues = []
        
        if round_num not in self.tables:
            return ["No tables set up for this round"]
        
        for table_name, players in self.tables[round_num].items():
            # Check table has exactly 4 players
            if len(players) != 4:
                issues.append(f"{table_name} has {len(players)} players instead of 4")
                continue
            
            # Check no players from same team
            teams_at_table = [p['Team Name'] for p in players]
            if len(set(teams_at_table)) != 4:
                issues.append(f"{table_name} has players from same team: {teams_at_table}")
            
            # Check for repeat matchups (only for rounds 2+)
            if round_num > 1:
                for i, player1 in enumerate(players):
                    for j, player2 in enumerate(players):
                        if i < j:  # Avoid checking same pair twice
                            # Check if these players faced each other in previous rounds
                            player1_opponents = self.get_player_opponents(player1['Player ID'], round_num - 1)
                            if player2['Player ID'] in player1_opponents:
                                issues.append(f"{table_name}: {player1['Player Name']} and {player2['Player Name']} have faced each other before")
        
        return issues
    
    def submit_player_results(self, round_num, player_results):
        """Submit individual player results for a round (only once per round)"""
        if round_num not in self.round_results:
            self.round_results[round_num] = {}
        
        # Check if this round has already been submitted
        if 'players' in self.round_results[round_num]:
            print(f"Warning: Round {round_num} player results already exist! Preventing duplicate submission.")
            return False
        
        # Initialize players dict for this round
        self.round_results[round_num]['players'] = {}
        
        # Update individual player scores
        for result in player_results:
            player_id = result['player_id']
            points = result['points']
            
            if player_id in self.player_scores:
                # Store round-specific results
                self.round_results[round_num]['players'][player_id] = points
                
                # Update total player score
                self.player_scores[player_id] += points
        
        # Recalculate team scores from individual player scores
        self.calculate_team_scores()
        
        print(f"Round {round_num} player results submitted and finalized successfully")
        return True
    
    def calculate_team_scores(self):
        """Calculate team scores from individual player scores"""
        self.scores = {team: 0 for team in self.teams.keys()}
        
        for team_name, players in self.teams.items():
            team_total = 0
            for player in players:
                player_id = player.get('Player ID')
                if player_id in self.player_scores:
                    team_total += self.player_scores[player_id]
            self.scores[team_name] = team_total
    
    def calculate_final_round_standings(self):
        """Calculate final round standings with Swiss round tiebreaker
        
        Champion determination logic:
        1. PRIMARY: Points scored in final round (highest wins)
        2. TIEBREAKER: Swiss round points (if tied on finals, higher Swiss wins)
        """
        # Support both old (semifinals) and new (finals_data) structure
        advancing_teams = []
        
        if hasattr(self, 'finals_data') and self.finals_data:
            advancing_teams = self.finals_data.get('advancing_teams', [])
        elif hasattr(self, 'semifinals') and self.semifinals:
            advancing_teams = self.semifinals.get('advancing_teams', [])
        else:
            print("[ERROR] No finals data available")
            return None
        
        if not advancing_teams:
            print("[ERROR] No advancing teams found")
            return None
        
        print(f"\n[TROPHY] CALCULATING CHAMPION - Teams in finals: {advancing_teams}")
        print(f"[CHART] Final round scores: {self.final_round_scores}")
        print(f"[CHART] Swiss round scores: {self.swiss_round_scores}")
        if hasattr(self, 'top8_cut_scores'):
            print(f"[CHART] Top 8 Cut scores: {self.top8_cut_scores}")

        # Calculate final round team scores
        final_standings = []
        has_top8_cut = hasattr(self, 'top8_cut_scores') and self.top8_cut_scores

        for team_name in advancing_teams:
            final_round_points = self.final_round_scores.get(team_name, 0)
            swiss_round_points = self.swiss_round_scores.get(team_name, 0)
            top8_cut_points = self.top8_cut_scores.get(team_name, 0) if has_top8_cut else 0

            # For 16-team: tiebreaker = Swiss + Top 8 Cut
            # For 8-team: tiebreaker = Swiss only
            tiebreaker_points = swiss_round_points + top8_cut_points
            total_points = final_round_points + tiebreaker_points

            final_standings.append({
                'team': team_name,
                'final_points': final_round_points,
                'swiss_points': swiss_round_points,
                'top8_cut_points': top8_cut_points,
                'tiebreaker_points': tiebreaker_points,
                'total_points': total_points
            })

            if has_top8_cut:
                print(f"  {team_name}: Final={final_round_points} pts, Top8Cut={top8_cut_points} pts, Swiss={swiss_round_points} pts, Tiebreaker={tiebreaker_points} pts, Total={total_points} pts")
            else:
                print(f"  {team_name}: Final={final_round_points} pts, Swiss={swiss_round_points} pts, Total={total_points} pts")

        # Sort by FINAL ROUND POINTS first (primary), then tiebreaker points (Swiss + Top 8 Cut for 16-team)
        # This ensures the team with highest final round score wins
        # Only if teams are tied on final points do we use tiebreaker (Swiss or Swiss+Top8Cut)
        if has_top8_cut:
            print(f"\n[ROTATING] Sorting by: (final_points DESC, swiss+top8cut DESC)")
        else:
            print(f"\n[ROTATING] Sorting by: (final_points DESC, swiss_points DESC)")

        final_standings.sort(key=lambda x: (x['final_points'], x['tiebreaker_points']), reverse=True)

        print(f"\n[OK] FINAL STANDINGS (sorted by FINAL points first, then tiebreaker):")
        for rank, s in enumerate(final_standings, 1):
            medal = "[1st]" if rank == 1 else "[2nd]" if rank == 2 else "[3rd]" if rank == 3 else f"{rank}."
            if has_top8_cut:
                print(f"  {medal} {s['team']}: Final={s['final_points']} pts (PRIMARY), Tiebreaker={s['tiebreaker_points']} pts (Swiss={s['swiss_points']}+Top8={s['top8_cut_points']}), Total={s['total_points']} pts")
            else:
                print(f"  {medal} {s['team']}: Final={s['final_points']} pts (PRIMARY), Swiss={s['swiss_points']} pts (tiebreaker), Total={s['total_points']} pts")

        if len(final_standings) > 1:
            winner = final_standings[0]
            runner_up = final_standings[1]
            if winner['final_points'] == runner_up['final_points']:
                if has_top8_cut:
                    print(f"[WARNING] TIE on final points! Using Swiss+Top8Cut as tiebreaker:")
                    print(f"   Winner: {winner['team']} (Tiebreaker: {winner['tiebreaker_points']} = Swiss {winner['swiss_points']} + Top8 {winner['top8_cut_points']})")
                    print(f"   Runner-up: {runner_up['team']} (Tiebreaker: {runner_up['tiebreaker_points']} = Swiss {runner_up['swiss_points']} + Top8 {runner_up['top8_cut_points']})")
                else:
                    print(f"[WARNING] TIE on final points! Using Swiss points as tiebreaker:")
                    print(f"   Winner: {winner['team']} (Swiss: {winner['swiss_points']} pts)")
                    print(f"   Runner-up: {runner_up['team']} (Swiss: {runner_up['swiss_points']} pts)")
            else:
                print(f"[OK] Winner determined by final round points: {winner['team']} ({winner['final_points']} pts)")
        
        return final_standings
    
    def get_tournament_winner(self):
        """Get tournament winner and MVP after finals completion"""
        try:
            # Get final standings
            final_standings = self.calculate_final_round_standings()
            if not final_standings:
                return None
            
            # Winner is the top team
            winning_team = final_standings[0]['team']
            
            # Get team members
            team_members = self.teams.get(winning_team, [])
            
            # Calculate MVP (player with highest total points across entire tournament)
            mvp_player = None
            max_points = -1
            
            for player_id, total_points in self.player_scores.items():
                if total_points > max_points:
                    max_points = total_points
                    # Find player details
                    for participant in self.participants:
                        if participant.get('Player ID') == player_id:
                            mvp_player = {
                                'id': player_id,
                                'name': participant.get('Player Name', 'Unknown'),
                                'team': participant.get('Team Name', 'Unknown'),
                                'total_points': total_points
                            }
                            break
            
            return {
                'winning_team': winning_team,
                'team_members': team_members,
                'mvp_player': mvp_player,
                'final_standings': final_standings,
                'final_round_points': final_standings[0]['final_points'],
                'swiss_round_points': final_standings[0]['swiss_points']
            }
            
        except Exception as e:
            print(f"[ERROR] Error determining tournament winner: {str(e)}")
            return None

    def get_mvp(self):
        """Get MVP from Top 4 teams - player with highest individual total score

        Returns:
            dict: {
                'player_name': str,
                'team_name': str,
                'total_score': int
            } or None if data unavailable
        """
        try:
            # Get final standings
            final_standings = self.calculate_final_round_standings()
            if not final_standings or len(final_standings) < 4:
                print("[MVP] Cannot calculate MVP - insufficient final standings data")
                return None

            # Get Top 4 team names
            top4_teams = [team['team'] for team in final_standings[:4]]
            print(f"[MVP] Calculating MVP among Top 4 teams: {top4_teams}")

            # Find all players belonging to Top 4 teams
            top4_players = {}
            for participant in self.participants:
                team_name = participant.get('Team Name')
                if team_name in top4_teams:
                    player_id = participant.get('Player ID')
                    if player_id in self.player_scores:
                        top4_players[player_id] = {
                            'player_name': participant.get('Player Name', 'Unknown'),
                            'team_name': team_name,
                            'total_score': self.player_scores[player_id]
                        }

            if not top4_players:
                print("[MVP] No players found in Top 4 teams")
                return None

            # Find player with highest score
            mvp_id = max(top4_players.keys(), key=lambda pid: top4_players[pid]['total_score'])
            mvp_data = top4_players[mvp_id]

            print(f"[MVP] MVP: {mvp_data['player_name']} ({mvp_data['team_name']}) - {mvp_data['total_score']} pts")

            return mvp_data

        except Exception as e:
            print(f"[ERROR] Error calculating MVP: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def get_team_tiebreaker_key(self, team_name, total_score):
        """Calculate comprehensive tiebreaker key for team ranking

        Tiebreaker hierarchy:
        1. Total team score (primary)
        2. Best individual player score
        3. Average player score
        4. Earliest wins (more wins in earlier rounds)

        Returns:
            tuple: (total_score, best_player_score, avg_player_score, early_wins_score)
        """
        team_players = self.teams.get(team_name, [])

        # Get all player scores for this team
        player_scores = []
        for player in team_players:
            player_id = player.get('Player ID')
            score = self.player_scores.get(player_id, 0)
            player_scores.append(score)

        # Tiebreaker 2: Best player score
        best_player_score = max(player_scores) if player_scores else 0

        # Tiebreaker 3: Average player score (as integer to avoid float comparison issues)
        avg_player_score = int(sum(player_scores) / len(player_scores) * 1000) if player_scores else 0

        # Tiebreaker 4: Early wins score
        # Calculate weighted score: Round 1 wins worth more than Round 2, etc.
        early_wins_score = self.calculate_early_wins_score(team_name)

        return (total_score, best_player_score, avg_player_score, early_wins_score)

    def calculate_early_wins_score(self, team_name):
        """Calculate weighted score based on when wins occurred

        Wins in earlier rounds are worth more:
        - Round 1 win: 1000 points
        - Round 2 win: 100 points
        - Round 3 win: 10 points
        - Round 4 win: 1 point

        This ensures teams with more early wins rank higher.
        """
        if not hasattr(self, 'round_results') or not self.round_results:
            return 0

        team_players = self.teams.get(team_name, [])
        player_ids = [p.get('Player ID') for p in team_players]

        early_wins_score = 0
        round_weights = {1: 1000, 2: 100, 3: 10, 4: 1}

        # Iterate through each round
        for round_num in sorted(self.round_results.keys()):
            if round_num > 4:  # Only consider Swiss rounds (1-4)
                continue

            if 'players' not in self.round_results[round_num]:
                continue

            # Get weight for this round (earlier rounds = higher weight)
            weight = round_weights.get(round_num, 0)

            # Count points scored by team players in this round
            round_team_points = 0
            for player_id in player_ids:
                if player_id in self.round_results[round_num]['players']:
                    round_team_points += self.round_results[round_num]['players'][player_id]

            # Add weighted score (each point in earlier rounds worth more)
            early_wins_score += round_team_points * weight

        return early_wins_score

    def update_final_round_scores(self, round_num, player_results):
        """Update final round scores separately from Swiss round scores"""
        # Only process the actual finals round (last round of the tournament)
        if round_num != self.max_rounds:
            return  # Only process the finals round (Round 5 for 8-team, Round 6 for 16-team)
        
        # Initialize final round scores if not exists
        if not hasattr(self, 'final_round_scores') or not self.final_round_scores:
            self.final_round_scores = {}
            for team_name in self.teams.keys():
                self.final_round_scores[team_name] = 0
        
        # Add points from this table submission to accumulating final round totals
        for result in player_results:
            player_id = result['player_id']
            points = result['points']
            
            # Find which team this player belongs to
            for team_name, players in self.teams.items():
                for player in players:
                    if player['Player ID'] == player_id:
                        self.final_round_scores[team_name] += points
                        break
        
        # Ensure Swiss round scores are preserved
        if not hasattr(self, 'swiss_round_scores') or not self.swiss_round_scores:
            # If swiss_round_scores not set, calculate it
            # For 16-team: this should never happen as it's saved before Top 8 Cut
            # For 8-team: calculate from total before finals
            self.swiss_round_scores = {}
            for team_name in self.teams.keys():
                # Total accumulated before finals = Swiss + (Top 8 Cut if 16-team tournament)
                total_before_finals = self.scores.get(team_name, 0) - self.final_round_scores.get(team_name, 0)
                self.swiss_round_scores[team_name] = max(0, total_before_finals)
            print(f"[WARNING] Swiss scores not found - calculated from totals: {self.swiss_round_scores}")
        else:
            print(f"[OK] Swiss scores already saved: {self.swiss_round_scores}")

        print(f"[FINALS] Final round scores updated: {self.final_round_scores}")
        print(f"[FINALS] Swiss round scores: {self.swiss_round_scores}")

    def update_top8_cut_scores(self, round_num, player_results):
        """Update Top 8 Cut round scores separately from Swiss round scores

        For 16-team tournaments:
        - Top 8 Cut is Round 5 (swiss_rounds_count + 1)
        - Scores earned in Round 5 are tracked separately
        - Used to determine Finals advancement (with Swiss as tiebreaker)
        """
        # Determine if this is the Top 8 Cut round
        top8_cut_round = self.swiss_rounds_count + 1 if self.has_semifinals else None

        if round_num != top8_cut_round:
            return  # Only process Top 8 Cut round

        # Initialize Top 8 Cut scores if not exists
        if not hasattr(self, 'top8_cut_scores') or not self.top8_cut_scores:
            self.top8_cut_scores = {}
            for team_name in self.teams.keys():
                self.top8_cut_scores[team_name] = 0

        # Add points from this table submission to accumulating Top 8 Cut totals
        for result in player_results:
            player_id = result['player_id']
            points = result['points']

            # Find which team this player belongs to
            for team_name, players in self.teams.items():
                for player in players:
                    if player['Player ID'] == player_id:
                        self.top8_cut_scores[team_name] += points
                        break

        print(f"[TOP 8 CUT] Scores updated: {self.top8_cut_scores}")
        print(f"[TOP 8 CUT] Swiss scores (tiebreaker): {self.swiss_round_scores}")

    def generate_unified_finals(self, after_semifinals=False):
        """Generate finals - ALL players from top 4 teams, strength-based seating

        Args:
            after_semifinals: If True, use semifinal scores to determine top 4 teams
                            If False, use Swiss scores (for 8-team tournaments)

        CRITICAL: Ensures NO teammates are paired together (one player per team per table)
        """
        try:
            if after_semifinals:
                print("[TROPHY] Generating FINALS after semifinals (16-team tournament)")
                # Use Top 8 Cut scores (primary) with comprehensive tiebreaker
                # Top 8 Cut scores should be in self.top8_cut_scores
                # Swiss scores should already be saved from generate_semifinals_round()

                print(f"[TIEBREAKER] Applying multi-level tiebreaker for Top 4 Finals:")
                print(f"   1. Top 8 Cut score")
                print(f"   2. Swiss round score")
                print(f"   3. Best individual player score")
                print(f"   4. Average player score")
                print(f"   5. Early wins (Round 1 > Round 2 > Round 3 > Round 4)")

                # Sort by: (1) Top 8 Cut scores DESC, (2) Comprehensive tiebreaker
                def get_top8_ranking(team_score_tuple):
                    team_name = team_score_tuple[0]
                    top8_score = self.top8_cut_scores.get(team_name, 0) if hasattr(self, 'top8_cut_scores') else 0
                    swiss_score = self.swiss_round_scores.get(team_name, 0)

                    # Get additional tiebreakers (best player, avg, early wins)
                    tiebreaker_key = self.get_team_tiebreaker_key(team_name, swiss_score)
                    best_player = tiebreaker_key[1]
                    avg_player = tiebreaker_key[2]
                    early_wins = tiebreaker_key[3]

                    return (top8_score, swiss_score, best_player, avg_player, early_wins)

                sorted_teams = sorted(
                    self.scores.items(),
                    key=get_top8_ranking,
                    reverse=True
                )
                top_4_teams = [team for team, score in sorted_teams[:4]]

                print(f"\n[RANK] Finals advancement with comprehensive tiebreakers:")
                for rank, (team_name, total_score) in enumerate(sorted_teams[:8], 1):  # Show all Top 8
                    top8_score = self.top8_cut_scores.get(team_name, 0) if hasattr(self, 'top8_cut_scores') else 0
                    swiss_score = self.swiss_round_scores.get(team_name, 0)
                    tiebreaker_key = self.get_team_tiebreaker_key(team_name, swiss_score)
                    best_player = tiebreaker_key[1]
                    avg_player = tiebreaker_key[2] / 1000.0
                    early_wins = tiebreaker_key[3]
                    status = "→ FINALS" if rank <= 4 else "eliminated"
                    print(f"  {rank}. {team_name}: Top8={top8_score}, Swiss={swiss_score}, Best={best_player}, Avg={avg_player:.1f}, Early={early_wins} [{status}]")

            else:
                print("[TROPHY] Generating FINALS after Swiss rounds (8-team tournament)")
                # Save Swiss round scores before finals begin (8-team tournament)
                if not hasattr(self, 'swiss_round_scores') or not self.swiss_round_scores:
                    print(f"[SAVE] Preserving Swiss round scores before Finals")
                    self.swiss_round_scores = dict(self.scores)  # Deep copy current scores as Swiss scores
                    print(f"Swiss scores saved: {self.swiss_round_scores}")

                # For 8-team: Use comprehensive tiebreaker to get top 4
                print(f"[TIEBREAKER] Applying multi-level tiebreaker for Top 4 Finals:")
                print(f"   1. Total team score")
                print(f"   2. Best individual player score")
                print(f"   3. Average player score")
                print(f"   4. Early wins (Round 1 > Round 2 > Round 3 > Round 4)")

                def get_ranking_key(team_score_tuple):
                    team_name, total_score = team_score_tuple
                    return self.get_team_tiebreaker_key(team_name, total_score)

                sorted_teams = sorted(self.scores.items(), key=get_ranking_key, reverse=True)
                top_4_teams = [team for team, score in sorted_teams[:4]]

            print(f"\n   Top 4 teams advancing to finals (with tiebreakers):")
            for rank, (team, score) in enumerate(sorted_teams[:4], 1):
                tiebreaker_key = self.get_team_tiebreaker_key(team, score)
                best_player = tiebreaker_key[1]
                avg_player = tiebreaker_key[2] / 1000.0
                early_wins = tiebreaker_key[3]
                print(f"     {rank}. {team}: {score} pts (Best: {best_player}, Avg: {avg_player:.1f}, Early: {early_wins})")
            
            # CRITICAL FIX: Organize players by team, then rank within each team
            # This ensures we can assign one player per team per table
            team_ranked_players = {}
            for team_name in top_4_teams:
                team_players = []
                for player in self.teams[team_name]:
                    player_score = self.player_scores.get(player['Player ID'], 0)
                    team_players.append((player, player_score))
                
                # Sort players within each team by Swiss performance (highest first)
                team_players.sort(key=lambda x: x[1], reverse=True)
                team_ranked_players[team_name] = team_players
                
                print(f"\n   {team_name} players (ranked by Swiss points):")
                for rank, (player, score) in enumerate(team_players, 1):
                    print(f"     Rank {rank}: {player['Player Name']} - {score} pts")
            
            # Determine finals round number
            finals_round_num = self.max_rounds  # Last round is always finals

            print(f"\n   Creating finals tables (Round {finals_round_num}) (NO teammates together, ordered by team ranking):")

            # Create 4 finals tables with strength-based seating
            # Table 1: Strongest player from each team (rank 1 from each team)
            # Table 2: 2nd strongest player from each team (rank 2 from each team)
            # Table 3: 3rd strongest player from each team (rank 3 from each team)
            # Table 4: 4th strongest player from each team (rank 4 from each team)

            # Store team order by score (highest first) for seating arrangement
            team_order_by_score = top_4_teams.copy()  # Already sorted by score from sorted_teams

            # Initialize tables for finals round
            if not hasattr(self, 'tables'):
                self.tables = {}
            self.tables[finals_round_num] = {}
            
            for table_num in range(4):
                table_name = f'Finals Table {table_num + 1}'
                table_players = []
                table_players_with_team = []  # Store (player, team_name, score) for sorting
                
                # Get the player at position (table_num) from each team
                # This ensures one player per team per table (NO teammates together!)
                for team_name in top_4_teams:
                    if table_num < len(team_ranked_players[team_name]):
                        player, score = team_ranked_players[team_name][table_num]
                        table_players_with_team.append((player, team_name, score))
                
                # Arrange seating order by team ranking (highest team score = first seat)
                # Sort by team's position in top_4_teams (which is already sorted by score)
                table_players_with_team.sort(key=lambda x: team_order_by_score.index(x[1]))
                
                # Extract just the players in the correct order
                for player, team_name, score in table_players_with_team:
                    table_players.append(player)
                    team_rank = team_order_by_score.index(team_name) + 1
                    team_score = self.scores.get(team_name, 0)
                    print(f"     {table_name} Seat {team_rank}: {player['Player Name']} ({team_name}) - {score} pts (Team: {team_score} pts)")
                
                # Verify no teammates are together (safety check)
                teams_at_table = set()
                for player in table_players:
                    # Find which team this player belongs to
                    player_team = None
                    for team_name, players in team_ranked_players.items():
                        if any(p[0]['Player ID'] == player['Player ID'] for p in players):
                            player_team = team_name
                            break
                    
                    if player_team:
                        if player_team in teams_at_table:
                            print(f"     [WARNING]  WARNING: Multiple players from {player_team} detected at {table_name}!")
                        teams_at_table.add(player_team)
                
                # Seating order is now arranged by team ranking (highest team score = first seat)
                # No randomization - fixed order based on team performance
                self.tables[finals_round_num][table_name] = table_players

            print(f"\n[OK] Finals created: 4 tables with strength-based matchups")
            print(f"   - Table 1: Strongest player from each team (NO teammates)")
            print(f"   - Table 2: 2nd strongest player from each team (NO teammates)")
            print(f"   - Table 3: 3rd strongest player from each team (NO teammates)")
            print(f"   - Table 4: 4th strongest player from each team (NO teammates)")
            print(f"   [OK] VERIFIED: No teammates are paired together!")
            print(f"   [OK] Seating order: Arranged by team ranking (highest team score = first seat)")
            
            # Store finals data for winner calculation
            finals_data = {
                'advancing_teams': top_4_teams,
                'finals_tables': self.tables[finals_round_num],
                'round_num': finals_round_num
            }
            
            self.finals_data = finals_data
            self.semifinals = finals_data  # For compatibility
            
            return finals_data

        except Exception as e:
            print(f"[ERROR] Error generating finals: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_semifinals_round(self):
        """Generate Top 8 Cut for 16-team tournaments - top 8 teams advance

        Structure: 8 pods/tables with 4 players each (32 players total from 8 teams)
        - 2 groups of 4 teams each
        - 4 tables per group (8 total tables/pods)
        - Each table has one player from 4 different teams (no teammates together)
        - Players are matched by skill level (rank 1 vs rank 1, etc.)
        """
        try:
            # CRITICAL: Save Swiss round scores before Top 8 Cut begins
            # This ensures we can separate Swiss performance from Top 8 Cut performance
            if not hasattr(self, 'swiss_round_scores') or not self.swiss_round_scores:
                print(f"[SAVE] Preserving Swiss round scores before Top 8 Cut")
                self.swiss_round_scores = dict(self.scores)  # Deep copy current scores as Swiss scores
                print(f"Swiss scores saved: {self.swiss_round_scores}")

            # Validate we have enough teams for semifinals
            if len(self.scores) < 8:
                print(f"[ERROR] Cannot generate semifinals: Only {len(self.scores)} teams (need at least 8)")
                return None

            team_count = len(self.teams)
            print(f"[TROPHY] Generating TOP 8 CUT for {team_count}-team tournament")

            # Get top 8 teams by total score WITH comprehensive tiebreaker
            print(f"[TIEBREAKER] Applying multi-level tiebreaker system:")
            print(f"   1. Total team score")
            print(f"   2. Best individual player score")
            print(f"   3. Average player score")
            print(f"   4. Early wins (Round 1 > Round 2 > Round 3 > Round 4)")

            def get_ranking_key(team_score_tuple):
                team_name, total_score = team_score_tuple
                return self.get_team_tiebreaker_key(team_name, total_score)

            sorted_teams = sorted(self.scores.items(), key=get_ranking_key, reverse=True)
            top_8_teams = [team for team, score in sorted_teams[:8]]

            print(f"\n   Top 8 teams advancing to Top 8 Cut (with tiebreakers):")
            for rank, (team, score) in enumerate(sorted_teams[:8], 1):
                tiebreaker_key = self.get_team_tiebreaker_key(team, score)
                best_player = tiebreaker_key[1]
                avg_player = tiebreaker_key[2] / 1000.0  # Convert back from integer
                early_wins = tiebreaker_key[3]
                print(f"     {rank}. {team}: {score} pts (Best: {best_player}, Avg: {avg_player:.1f}, Early: {early_wins})")

            # Rank players within each team by their Swiss performance
            team_ranked_players = {}
            for team_name in top_8_teams:
                team_players = self.teams[team_name]
                # Get player scores and sort
                players_with_scores = []
                for player in team_players:
                    player_score = self.player_scores.get(player['Player ID'], 0)
                    players_with_scores.append((player, player_score))

                # Sort by score (highest first)
                players_with_scores.sort(key=lambda x: x[1], reverse=True)
                team_ranked_players[team_name] = players_with_scores

                print(f"\n   {team_name} player rankings:")
                for rank, (player, score) in enumerate(players_with_scores, 1):
                    print(f"     Rank {rank}: {player['Player Name']} - {score} pts")

            # Create Top 8 Cut round (round number = swiss_rounds_count + 1)
            semifinals_round_num = self.swiss_rounds_count + 1
            print(f"\n   Creating Top 8 Cut tables (Round {semifinals_round_num}):")

            # Initialize tables for semifinals round
            if not hasattr(self, 'tables'):
                self.tables = {}
            self.tables[semifinals_round_num] = {}

            # Create 8 semifinals tables
            # We need to distribute 8 teams across 8 tables, with 4 players per table
            # Strategy: Create 2 groups of 4 teams each, then create 4 tables per group

            # Split top 8 teams into 2 groups (teams 1,3,5,7 and teams 2,4,6,8)
            group_1_teams = [top_8_teams[i] for i in [0, 2, 4, 6]]  # 1st, 3rd, 5th, 7th
            group_2_teams = [top_8_teams[i] for i in [1, 3, 5, 7]]  # 2nd, 4th, 6th, 8th

            print(f"   Group 1 teams: {group_1_teams}")
            print(f"   Group 2 teams: {group_2_teams}")

            # Create 4 tables for each group (8 tables total)
            table_num = 1
            for group_teams in [group_1_teams, group_2_teams]:
                for player_rank in range(4):  # Rank 0-3 (strongest to weakest)
                    table_name = f'Semifinals Table {table_num}'
                    table_players = []

                    # Add one player from each team in this group (same rank)
                    for team_name in group_teams:
                        if player_rank < len(team_ranked_players[team_name]):
                            player, score = team_ranked_players[team_name][player_rank]
                            table_players.append(player)

                    if len(table_players) == 4:
                        self.tables[semifinals_round_num][table_name] = table_players
                        player_names = [p['Player Name'] for p in table_players]
                        print(f"     {table_name}: {player_names}")
                        table_num += 1

            print(f"\n[OK] Semifinals created: 8 tables with strength-based matchups")
            print(f"   - Top 8 teams (32 players total)")
            print(f"   - Each table: 4 players from 4 different teams (NO teammates)")
            print(f"   - Players matched by skill level")

            # Store semifinals data
            semifinals_data = {
                'advancing_teams': top_8_teams,
                'semifinals_tables': self.tables[semifinals_round_num],
                'round_num': semifinals_round_num
            }

            self.semifinals_data = semifinals_data

            return semifinals_data

        except Exception as e:
            print(f"[ERROR] Error generating semifinals: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_semifinals(self):
        """Generate finals after Swiss Round 4 - top 2 teams from each group advance (LEGACY)"""
        try:
            # Check if we have the necessary data
            if not hasattr(self, 'group_a') or not hasattr(self, 'group_b') or not self.scores:
                print("[ERROR] Using unified tournament - calling generate_unified_finals instead")
                return self.generate_unified_finals()
            
            # Calculate team standings for each group
            group_a_standings = [(team, self.scores.get(team, 0)) for team in self.group_a]
            group_b_standings = [(team, self.scores.get(team, 0)) for team in self.group_b]
            
            # Sort by points (descending)
            group_a_standings.sort(key=lambda x: x[1], reverse=True)
            group_b_standings.sort(key=lambda x: x[1], reverse=True)
            
            # Select top 2 teams from each group
            advancing_teams = []
            advancing_teams.append(group_a_standings[0][0])  # Group A 1st
            advancing_teams.append(group_a_standings[1][0])  # Group A 2nd
            advancing_teams.append(group_b_standings[0][0])  # Group B 1st
            advancing_teams.append(group_b_standings[1][0])  # Group B 2nd
            
            print(f"[TROPHY] Advancing teams:")
            print(f"   Group A: {group_a_standings[0][0]} ({group_a_standings[0][1]} pts), {group_a_standings[1][0]} ({group_a_standings[1][1]} pts)")
            print(f"   Group B: {group_b_standings[0][0]} ({group_b_standings[0][1]} pts), {group_b_standings[1][0]} ({group_b_standings[1][1]} pts)")
            
            # Get all players from advancing teams and rank them by Swiss performance
            advancing_players = []
            for team_name in advancing_teams:
                team_players = self.teams[team_name]
                # Sort team players by their Swiss points (descending)
                team_players_with_points = []
                for player in team_players:
                    swiss_points = self.player_scores.get(player['Player ID'], 0)
                    team_players_with_points.append((player, swiss_points))
                
                # Sort by Swiss points (highest first)
                team_players_with_points.sort(key=lambda x: x[1], reverse=True)
                
                # Add to advancing players with team and rank info
                for rank, (player, points) in enumerate(team_players_with_points):
                    advancing_players.append({
                        'player': player,
                        'team': team_name,
                        'swiss_points': points,
                        'team_rank': rank + 1  # 1=best, 2=second, etc.
                    })
            
            # Create 4 pods based on skill level (same rank players compete together)
            semifinals_pods = {}
            for pod_rank in range(1, 5):  # Pod 1-4
                pod_players = []
                for team_name in advancing_teams:
                    # Find the player with this rank from this team
                    team_player = next((p for p in advancing_players if p['team'] == team_name and p['team_rank'] == pod_rank), None)
                    if team_player:
                        pod_players.append(team_player['player'])
                
                if len(pod_players) == 4:  # Should have exactly 4 players (one from each team)
                    semifinals_pods[f'Table {pod_rank}'] = pod_players
            
            print(f"[TARGET] Finals pods created:")
            for pod_name, players in semifinals_pods.items():
                print(f"   {pod_name}: {[p['Player Name'] for p in players]}")
            
            # Store finals data
            self.semifinals = {
                'advancing_teams': advancing_teams,
                'group_a_standings': group_a_standings,
                'group_b_standings': group_b_standings,
                'pods': semifinals_pods
            }
            
            # Add Round 5 (finals) to tables
            if not hasattr(self, 'tables'):
                self.tables = {}
            self.tables[5] = semifinals_pods
            
            # Initialize final round scores for the advancing teams
            self.final_round_scores = {}
            for team_name in advancing_teams:
                self.final_round_scores[team_name] = 0
            
            return self.semifinals
            
        except Exception as e:
            print(f"[ERROR] Error generating semifinals: {str(e)}")
            return None

    def validate_group_separation(self, round_num):
        """Validate that players only face opponents within their own group"""
        issues = []
        
        if round_num not in self.tables:
            return ["No tables set up for this round"]
        
        # Check each table for group violations
        for table_name, players in self.tables[round_num].items():
            if len(players) < 4:
                continue
                
            # Determine which group this table should belong to
            table_num = int(table_name.replace('Table ', ''))
            expected_group = 'A' if table_num <= 4 else 'B'
            expected_teams = self.group_a if expected_group == 'A' else self.group_b
            
            # Check if all players are from the correct group
            for player in players:
                player_team = player['Team Name']
                if player_team not in expected_teams:
                    issues.append(f"{table_name}: Player {player['Player Name']} from {player_team} is not in Group {expected_group}")
            
            # Check if players are from different teams within the group
            teams_at_table = [p['Team Name'] for p in players]
            if len(set(teams_at_table)) != 4:
                issues.append(f"{table_name}: Players should be from 4 different teams, found teams: {list(set(teams_at_table))}")
        
        return issues
    
    def validate_swiss_no_repeats(self, through_round):
        """Validate that no players face the same opponents twice during Swiss rounds"""
        issues = []
        
        # Track all pairings for each player
        player_opponents = {}
        
        for round_num in range(1, through_round + 1):
            if round_num not in self.tables:
                continue
                
            for table_name, players in self.tables[round_num].items():
                if len(players) != 4:
                    continue
                    
                # Generate all pairs at this table
                for i in range(len(players)):
                    for j in range(i + 1, len(players)):
                        player1 = players[i]
                        player2 = players[j]
                        
                        # Initialize tracking if needed
                        if player1['Player ID'] not in player_opponents:
                            player_opponents[player1['Player ID']] = {}
                        if player2['Player ID'] not in player_opponents:
                            player_opponents[player2['Player ID']] = {}
                        
                        # Check if these players faced each other before
                        if player2['Player ID'] in player_opponents[player1['Player ID']]:
                            prev_round = player_opponents[player1['Player ID']][player2['Player ID']]
                            issues.append(f"Round {round_num} {table_name}: {player1['Player Name']} and {player2['Player Name']} previously faced each other in Round {prev_round}")
                        else:
                            # Record this pairing
                            player_opponents[player1['Player ID']][player2['Player ID']] = round_num
                            player_opponents[player2['Player ID']][player1['Player ID']] = round_num
        
        return issues

# Initialize tournament manager
tournament = TournamentManager()

# Thread safety lock for concurrent access protection
tournament_lock = threading.Lock()


def periodic_backup_thread(tournament_obj, interval=300):
    """Background thread to save backup every 5 minutes (300 seconds)"""
    while True:
        time.sleep(interval)
        try:
            with tournament_lock:
                success = tournament_obj.save_backup()
                if success:
                    print(f"[AUTO-BACKUP] Periodic backup completed at {datetime.now()}")
                else:
                    print(f"[AUTO-BACKUP ERROR] Backup failed at {datetime.now()}")
        except Exception as e:
            print(f"[AUTO-BACKUP ERROR] {e}")

# Thread-safe decorator for state-modifying endpoints
def with_lock(f):
    """
    Decorator to ensure thread-safe access to tournament state.
    Wraps endpoint execution in tournament_lock context.

    Usage:
        @with_lock
        def my_endpoint():
            # This code is protected by tournament_lock
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        with tournament_lock:
            return f(*args, **kwargs)
    return decorated_function

# State validation decorator (Phase 3.4)
def require_state(*allowed_states):
    """
    Decorator to ensure endpoint is called in a valid tournament state.

    Usage:
        @require_state(TournamentState.SWISS_IN_PROGRESS, TournamentState.FINALS_IN_PROGRESS)
        def my_endpoint():
            ...

    Returns 400 error if current state is not in allowed_states.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if tournament.state not in allowed_states:
                allowed_names = [s.value for s in allowed_states]
                return jsonify({
                    'success': False,
                    'error': f'Invalid operation in current state: {tournament.state.value}',
                    'user_message': f'Cannot perform this action right now.',
                    'suggestion': f'Current state: {tournament.state.value}. This action requires one of: {", ".join(allowed_names)}',
                    'current_state': tournament.state.value,
                    'allowed_states': allowed_names
                }), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return render_template('dashboard_ultra_modern.html')

@app.route('/load_data', methods=['GET', 'POST'])
@with_lock
def load_data():
    """Load participant data from Excel file and configure Swiss rounds"""
    try:
        # Get Swiss rounds configuration from request (if POST)
        swiss_rounds = 4  # Default
        use_sample_data = False
        sample_team_count = 8  # Default for sample data

        if request.method == 'POST':
            data = request.get_json() or {}
            swiss_rounds = data.get('swiss_rounds', 4)
            use_sample_data = data.get('use_sample_data', False)
            sample_team_count = data.get('sample_team_count', 8)

            force_reload = data.get('force_reload', False)

            # Configure Swiss rounds before loading participants
            # Allow reconfiguration if the requested rounds differ from current configuration
            if not tournament.swiss_rounds_configured or tournament.swiss_rounds_count != swiss_rounds:
                success, message = tournament.configure_swiss_rounds(swiss_rounds)
                if not success:
                    return jsonify({
                        'success': False,
                        'message': message
                    })

        # Only reload from Excel if teams aren't already loaded or forced
        if not tournament.teams or (request.method == 'POST' and force_reload):
            # Check if we should force sample data
            if use_sample_data:
                print(f"Using sample data with {sample_team_count} teams (forced by request)...")
                tournament.create_sample_data(sample_team_count)
                # Determine tournament structure after creating sample data
                tournament.determine_tournament_structure()
                success = True
            else:
                excel_path = 'participants/participant_team.xlsx'

                # Try to load from Excel, fallback to sample data
                if os.path.exists(excel_path):
                    try:
                        success = tournament.load_participants(excel_path)
                        print(f"Load data result: {success}")
                        print(f"Teams loaded: {len(tournament.teams)}")
                        print(f"Team names: {list(tournament.teams.keys())}")
                    except Exception as e:
                        print(f"Error loading Excel file: {e}")
                        print("Falling back to sample data...")
                        tournament.create_sample_data(sample_team_count)
                        # Determine tournament structure after creating sample data
                        tournament.determine_tournament_structure()
                        success = True
                else:
                    print(f"Excel file not found: {excel_path}")
                    print(f"Creating sample data with {sample_team_count} teams...")
                    tournament.create_sample_data(sample_team_count)
                    # Determine tournament structure after creating sample data
                    tournament.determine_tournament_structure()
                    success = True
        else:
            success = True
            print(f"Returning existing tournament data (scores preserved)")
            print(f"Team scores: {tournament.scores}")
            print(f"Player scores (first 5): {dict(list(tournament.player_scores.items())[:5])}")

        # Auto-save after loading data
        tournament.save_backup()

        # State transition: Participants loaded (Phase 3.4)
        # Only transition to PARTICIPANTS_LOADED if we're in INITIAL state
        # Don't reset state if tournament is already set up
        if success and len(tournament.teams) > 0:
            if tournament.state == TournamentState.INITIAL:
                tournament.transition_to(
                    TournamentState.PARTICIPANTS_LOADED,
                    f"Loaded {len(tournament.teams)} teams"
                )

        return jsonify({
            'success': success,
            'teams': tournament.teams,
            'scores': tournament.scores,
            'player_scores': tournament.player_scores,
            'team_count': len(tournament.teams),
            'participant_count': len(tournament.participants),
            'player_count': len(tournament.participants),
            'swiss_rounds': tournament.swiss_rounds_count,
            'has_semifinals': tournament.has_semifinals,
            'max_rounds': tournament.max_rounds,
            'message': f'Loaded {len(tournament.teams)} teams - {tournament.swiss_rounds_count} Swiss rounds configured'
        })

    except FileNotFoundError as e:
        print(f"Error in load_data (File not found): {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Participant file not found. Using sample data instead.',
            'suggestion': 'To load custom participants, place an Excel file at: participants/participant_team.xlsx'
        }), 404
    except ValueError as e:
        print(f"Error in load_data (Invalid data): {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Invalid participant data format.',
            'suggestion': 'Please ensure each team has exactly 4 players and total teams is 8, 12, or 16.'
        }), 400
    except Exception as e:
        print(f"Error in load_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Failed to load participants. Please try again or use sample data.',
            'suggestion': 'Click "Load Sample Data" to test the system with dummy participants.'
        }), 500

@app.route('/restore_backup', methods=['POST'])
@with_lock
def restore_backup():
    """Restore tournament state from backup"""
    try:
        success = tournament.load_state()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Tournament restored from backup successfully',
                'current_round': tournament.current_round,
                'swiss_rounds': tournament.swiss_rounds_count,
                'teams': len(tournament.teams)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to restore backup or no backup found'
            })
            
    except Exception as e:
        print(f"Error in restore_backup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/set_swiss_rounds', methods=['POST'])
def set_swiss_rounds():
    """Set the number of Swiss rounds (4 or 5)"""
    data = request.get_json()
    rounds_count = data.get('rounds_count', 4)

    # Use the new configuration method
    success, message = tournament.configure_swiss_rounds(rounds_count)

    return jsonify({
        'success': success,
        'message': message,
        'swiss_rounds_count': tournament.swiss_rounds_count if success else None
    })

@app.route('/configure_swiss_rounds', methods=['POST'])
def configure_swiss_rounds():
    """Configure the number of Swiss rounds (4 or 5) - API endpoint for tests"""
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': 'No data provided'
        })

    rounds = data.get('swiss_rounds')

    if rounds is None:
        return jsonify({
            'success': False,
            'error': 'swiss_rounds parameter is required'
        })

    if rounds not in [4, 5]:
        return jsonify({
            'success': False,
            'error': 'Swiss rounds must be either 4 or 5'
        })

    success, message = tournament.configure_swiss_rounds(rounds)

    return jsonify({
        'success': success,
        'message': message,
        'swiss_rounds': tournament.swiss_rounds_count
    })

@app.route('/setup_tournament', methods=['POST'])
@with_lock
@require_state(TournamentState.PARTICIPANTS_LOADED, TournamentState.TOURNAMENT_SETUP)
def setup_tournament():
    """Setup tournament with all teams in a single group"""
    try:
        success, message = tournament.setup_tournament()
        
        if not success:
            return jsonify({
                'success': False,
                'message': message,
                'error': 'Tournament setup failed'
            })
        
        # Get validation issues for Round 1
        validation_issues = tournament.validate_swiss_pairings(1) if hasattr(tournament, 'validate_swiss_pairings') else []

        # Auto-save after tournament setup
        tournament.save_backup()

        # State transition: Tournament setup complete (Phase 3.4)
        tournament.transition_to(
            TournamentState.TOURNAMENT_SETUP,
            "Tournament setup complete, Round 1 ready"
        )

        return jsonify({
            'success': success,
            'message': message,
            'tournament_teams': tournament.tournament_teams,
            'swiss_rounds_count': tournament.swiss_rounds_count,
            'has_semifinals': tournament.has_semifinals,
            'max_rounds': tournament.max_rounds,
            'tables': tournament.tables.get(1, {}),
            'validation_issues': validation_issues,
            'scores': tournament.scores,  # Include reset scores
            'player_scores': tournament.player_scores  # Include reset player scores
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in setup_tournament: {error_details}")
        return jsonify({
            'success': False,
            'message': f'Error setting up tournament: {str(e)}',
            'error': str(e),
            'error_details': error_details
        }), 500

@app.route('/submit_player_results', methods=['POST'])
@with_lock
def submit_player_results():
    """Finalize round (without adding points again - they're already added via table submissions)"""
    try:
        data = request.json
        round_num = data.get('round')

        # Initialize tracking sets if they don't exist
        if not hasattr(tournament, 'finalized_rounds'):
            tournament.finalized_rounds = set()

        if not hasattr(tournament, 'submitted_rounds'):
            tournament.submitted_rounds = set()

        # Check if round is already finalized or submitted
        if round_num in tournament.finalized_rounds:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} has already been finalized!',
                'message': f'Round {round_num} has already been finalized!'
            })

        if round_num in tournament.submitted_rounds:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} results have already been submitted!',
                'message': f'Round {round_num} results have already been submitted!'
            })
    
        # Check if this round has table submissions (points already added)
        has_table_submissions = (round_num in tournament.round_results and 
                               'table_submissions' in tournament.round_results[round_num])
    
        if has_table_submissions:
            print(f"Round {round_num} has table submissions - points already added via table submissions")
            print("Finalizing round WITHOUT adding points again to prevent double counting")

            # Mark the round as finalized and submitted
            tournament.finalized_rounds.add(round_num)
            tournament.submitted_rounds.add(round_num)

            # Store finalization timestamp in round results
            if round_num not in tournament.round_results:
                tournament.round_results[round_num] = {}
            tournament.round_results[round_num]['finalized'] = True
            tournament.round_results[round_num]['submitted'] = True

            print(f"Round {round_num} has been FINALIZED and SUBMITTED - preventing future submissions")
        
            # Check if this is Round 4 (end of Swiss) - trigger finals
            # OR Round 5 (end of Finals) - trigger winner announcement
            semifinals_data = None
            tournament_winner_data = None

            # Determine what happens after this round based on tournament structure
            last_swiss_round = tournament.swiss_rounds_count
            semifinals_round = last_swiss_round + 1 if tournament.has_semifinals else None
            finals_round = tournament.max_rounds
            next_round_generated = None

            # Generate next Swiss round if not the last one
            if round_num < last_swiss_round:
                next_round = round_num + 1
                print(f"[ROTATING] Generating Swiss Round {next_round} based on current standings...")
                success = tournament.generate_swiss_round(next_round)
                if success:
                    print(f"[OK] Swiss Round {next_round} generated successfully!")
                    next_round_generated = next_round
                    # CRITICAL FIX: Increment current round
                    tournament.current_round = next_round
                else:
                    print(f"[ERROR] Failed to generate Swiss Round {next_round}")

            if round_num == last_swiss_round:
                # End of Swiss rounds
                print(f"[TROPHY] Swiss Round {last_swiss_round} completed!")

                # Store Swiss round scores
                tournament.swiss_round_scores = tournament.scores.copy()

                if tournament.has_semifinals:
                    # 16 teams: Generate top 8 cut (8 pods)
                    print("   Generating Top 8 Cut (8 teams, 8 pods)...")
                    semifinals_data = tournament.generate_semifinals_round()
                    if semifinals_data:
                        print("[OK] Semifinals generated successfully!")
                        # CRITICAL FIX: Update state to enable Top 8 submissions
                        tournament.state = TournamentState.TOP8_IN_PROGRESS
                        # CRITICAL FIX: Increment current round for Top 8
                        tournament.current_round = last_swiss_round + 1
                        print(f"[STATE] Transitioning to {tournament.state}")
                    else:
                        print("[ERROR] Failed to generate semifinals")
                else:
                    # 8 or 12 teams: Generate finals directly
                    print("   Generating Finals (top 4 teams, 4 pods)...")
                    semifinals_data = tournament.generate_unified_finals(after_semifinals=False)
                    if semifinals_data:
                        print("[OK] Finals generated successfully!")
                        # CRITICAL FIX: Update state to enable Finals submissions
                        tournament.state = TournamentState.FINALS_IN_PROGRESS
                        # CRITICAL FIX: Increment current round for Finals
                        tournament.current_round = tournament.max_rounds
                        print(f"[STATE] Transitioning to {tournament.state}")
                    else:
                        print("[ERROR] Failed to generate finals")

            elif tournament.has_semifinals and round_num == semifinals_round:
                # End of top 8 cut (16-team tournament)
                print(f"[TROPHY] Top 8 Cut completed! Generating Finals...")

                # Store semifinal scores
                tournament.semifinal_round_scores = tournament.scores.copy()

                # Generate finals after semifinals
                semifinals_data = tournament.generate_unified_finals(after_semifinals=True)
                if semifinals_data:
                    print("[OK] Finals generated successfully!")
                    # CRITICAL FIX: Update state to enable Finals submissions
                    tournament.state = TournamentState.FINALS_IN_PROGRESS
                    # CRITICAL FIX: Increment current round for Finals (Round 6 for 16-team)
                    tournament.current_round = tournament.max_rounds
                    print(f"[STATE] Transitioning to {tournament.state}, Round {tournament.current_round}")
                else:
                    print("[ERROR] Failed to generate finals")

            elif round_num == finals_round:
                # End of finals
                print("[TROPHY] Finals completed! Determining tournament winner...")
                tournament_winner_data = tournament.get_tournament_winner()
                if tournament_winner_data:
                    print("[OK] Tournament winner determined!")
                    print(f"[1st] Champion: {tournament_winner_data['winning_team']}")
                    print(f"[STAR] MVP: {tournament_winner_data['mvp_player']['name']} ({tournament_winner_data['mvp_player']['total_points']} pts)")
                else:
                    print("[ERROR] Failed to determine tournament winner")
        
            response_data = {
                'success': True,
                'scores': tournament.scores,
                'player_scores': tournament.player_scores,
                'message': f'Round {round_num} finalized successfully (points were already added via table submissions)'
            }

            if next_round_generated:
                response_data['next_round'] = next_round_generated
                response_data['message'] += f' | [ROTATING] Swiss Round {next_round_generated} generated based on current standings!'

            if semifinals_data:
                response_data['semifinals'] = semifinals_data
                response_data['message'] += ' | [TARGET] Finals have been generated! Top 2 teams from each group advance.'

            if tournament_winner_data:
                response_data['tournament_winner'] = tournament_winner_data
                response_data['message'] += f" | [TROPHY] Tournament Complete! Champion: {tournament_winner_data['winning_team']}"

            # Auto-save tournament state after successful submission
            tournament.save_backup()

            return jsonify(response_data)
        else:
            print(f"Round {round_num} has NO table submissions - using legacy point addition method")
            # Legacy method: add points from form inputs (for backward compatibility)
            player_results = data.get('results', [])
            success = tournament.submit_player_results(round_num, player_results)
        
            if success:
                # Mark round as finalized and submitted
                tournament.finalized_rounds.add(round_num)
                tournament.submitted_rounds.add(round_num)
                print(f"Round {round_num} has been FINALIZED and SUBMITTED - preventing future submissions")
            
                # Determine what happens after this round based on tournament structure
                semifinals_data = None
                tournament_winner_data = None
                next_round_generated = None

                last_swiss_round = tournament.swiss_rounds_count
                semifinals_round = last_swiss_round + 1 if tournament.has_semifinals else None
                finals_round = tournament.max_rounds

                # Generate next Swiss round if not the last one
                if round_num < last_swiss_round:
                    next_round = round_num + 1
                    print(f"[ROTATING] Generating Swiss Round {next_round} based on current standings...")
                    success = tournament.generate_swiss_round(next_round)
                    if success:
                        print(f"[OK] Swiss Round {next_round} generated successfully!")
                        next_round_generated = next_round
                    else:
                        print(f"[ERROR] Failed to generate Swiss Round {next_round}")

                if round_num == last_swiss_round:
                    # End of Swiss rounds
                    print(f"[TROPHY] Swiss Round {last_swiss_round} completed!")

                    # Store Swiss round scores
                    tournament.swiss_round_scores = tournament.scores.copy()

                    if tournament.has_semifinals:
                        # 16 teams: Generate top 8 cut (8 pods)
                        print("   Generating Top 8 Cut (8 teams, 8 pods)...")
                        semifinals_data = tournament.generate_semifinals_round()
                        if semifinals_data:
                            print("[OK] Semifinals generated successfully!")
                        else:
                            print("[ERROR] Failed to generate semifinals")
                    else:
                        # 8 or 12 teams: Generate finals directly
                        print("   Generating Finals (top 4 teams, 4 pods)...")
                        semifinals_data = tournament.generate_semifinals()  # Legacy method calls generate_unified_finals
                        if semifinals_data:
                            print("[OK] Finals generated successfully!")
                        else:
                            print("[ERROR] Failed to generate finals")

                elif tournament.has_semifinals and round_num == semifinals_round:
                    # End of top 8 cut (16-team tournament)
                    print(f"[TROPHY] Top 8 Cut completed! Generating Finals...")

                    # Store semifinal scores
                    tournament.semifinal_round_scores = tournament.scores.copy()

                    # Generate finals after semifinals
                    semifinals_data = tournament.generate_unified_finals(after_semifinals=True)
                    if semifinals_data:
                        print("[OK] Finals generated successfully!")
                    else:
                        print("[ERROR] Failed to generate finals")

                elif round_num == finals_round:
                    # End of finals
                    print("[TROPHY] Finals completed! Determining tournament winner...")
                    tournament_winner_data = tournament.get_tournament_winner()
                    if tournament_winner_data:
                        print("[OK] Tournament winner determined!")
                        print(f"[1st] Champion: {tournament_winner_data['winning_team']}")
                        print(f"[STAR] MVP: {tournament_winner_data['mvp_player']['name']} ({tournament_winner_data['mvp_player']['total_points']} pts)")
                    else:
                        print("[ERROR] Failed to determine tournament winner")
            
                response_data = {
                    'success': True,
                    'scores': tournament.scores,
                    'player_scores': tournament.player_scores,
                    'message': f'Round {round_num} finalized successfully'
                }

                if next_round_generated:
                    response_data['next_round'] = next_round_generated
                    response_data['message'] += f' | [ROTATING] Swiss Round {next_round_generated} generated based on current standings!'

                if semifinals_data:
                    response_data['semifinals'] = semifinals_data
                    response_data['message'] += ' | [TARGET] Finals have been generated! Top 2 teams from each group advance.'

                if tournament_winner_data:
                    response_data['tournament_winner'] = tournament_winner_data
                    response_data['message'] += f" | [TROPHY] Tournament Complete! Champion: {tournament_winner_data['winning_team']}"

                return jsonify(response_data)
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to finalize round results'
                })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Error in submit_player_results: {str(e)}")
        print(f"Traceback: {error_trace}")
        return jsonify({
            'success': False,
            'message': f'Error finalizing round: {str(e)}',
            'error': str(e)
        }), 500

@app.route('/submit_table_results', methods=['POST'])
@with_lock
@require_state(
    TournamentState.TOURNAMENT_SETUP,
    TournamentState.SWISS_IN_PROGRESS,
    TournamentState.TOP8_IN_PROGRESS,
    TournamentState.FINALS_IN_PROGRESS
)
def submit_table_results():
    """Submit results for a specific table with comprehensive validation."""
    try:
        data = request.json

        # Validate request body exists
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Validate round number
        round_num = data.get('round')
        if round_num is None:
            return jsonify({'success': False, 'error': 'Round number is required'}), 400
        if not isinstance(round_num, int):
            return jsonify({'success': False, 'error': f'Round number must be an integer, got {type(round_num).__name__}'}), 400
        if round_num < 1:
            return jsonify({'success': False, 'error': f'Round number must be at least 1, got {round_num}'}), 400
        if round_num > tournament.max_rounds:
            return jsonify({'success': False, 'error': f'Round number {round_num} exceeds maximum rounds ({tournament.max_rounds})'}), 400

        # Validate table name
        table_name = data.get('table')
        if not table_name:
            return jsonify({'success': False, 'error': 'Table name is required'}), 400
        if not isinstance(table_name, str):
            return jsonify({'success': False, 'error': f'Table name must be a string, got {type(table_name).__name__}'}), 400

        # Validate table exists in round
        if round_num in tournament.tables:
            if table_name not in tournament.tables[round_num]:
                available_tables = list(tournament.tables[round_num].keys())
                return jsonify({
                    'success': False,
                    'error': f'Table "{table_name}" not found in round {round_num}. Available tables: {available_tables}'
                }), 400
        else:
            return jsonify({'success': False, 'error': f'Round {round_num} has not been set up yet'}), 400

        # Validate player results
        player_results = data.get('results', [])
        if not isinstance(player_results, list):
            return jsonify({'success': False, 'error': f'Results must be a list, got {type(player_results).__name__}'}), 400
        if len(player_results) == 0:
            return jsonify({'success': False, 'error': 'No player results provided'}), 400

        # Validate each player result
        for idx, result in enumerate(player_results):
            # Check result is a dict
            if not isinstance(result, dict):
                return jsonify({'success': False, 'error': f'Result {idx} must be an object, got {type(result).__name__}'}), 400

            # Check required fields exist
            if 'player_id' not in result:
                return jsonify({'success': False, 'error': f'Result {idx} missing required field: player_id'}), 400
            if 'points' not in result:
                return jsonify({'success': False, 'error': f'Result {idx} missing required field: points'}), 400

            # Validate player_id
            player_id = result['player_id']
            if not isinstance(player_id, int):
                return jsonify({'success': False, 'error': f'Result {idx}: player_id must be an integer, got {type(player_id).__name__}'}), 400
            if player_id not in tournament.player_scores:
                return jsonify({'success': False, 'error': f'Result {idx}: Invalid player_id {player_id}. Player not found in tournament.'}), 400

            # Validate points (must be 0, 1, or 5)
            points = result['points']
            if not isinstance(points, int):
                return jsonify({'success': False, 'error': f'Result {idx}: points must be an integer, got {type(points).__name__}'}), 400
            if points not in [0, 1, 5]:
                return jsonify({'success': False, 'error': f'Result {idx}: Invalid points value {points}. Must be 0 (Loss), 1 (Draw), or 5 (Win)'}), 400

        print(f"[OK] Validation passed for Round {round_num}, {table_name}")
        print(f"Player results: {player_results}")

        # Initialize round results if not exists
        if round_num not in tournament.round_results:
            tournament.round_results[round_num] = {}

        if 'table_submissions' not in tournament.round_results[round_num]:
            tournament.round_results[round_num]['table_submissions'] = {}

        # Initialize submitted_tables tracking set
        if 'submitted_tables' not in tournament.round_results[round_num]:
            tournament.round_results[round_num]['submitted_tables'] = set()

        # Check if table already submitted (prevent double-submission)
        if table_name in tournament.round_results[round_num]['submitted_tables']:
            print(f"[WARNING] Table {table_name} already submitted for round {round_num}")
            return jsonify({
                'success': False,
                'error': f'{table_name} has already been submitted for round {round_num}. Scores are locked.',
                'already_submitted': True
            }), 400

        # Store table-specific results
        tournament.round_results[round_num]['table_submissions'][table_name] = player_results

        # Update individual player scores
        for result in player_results:
            player_id = result['player_id']
            points = result['points']

            print(f"  Processing player_id={player_id}, points={points}")

            if player_id in tournament.player_scores:
                # Add points to player's total
                old_score = tournament.player_scores[player_id]
                tournament.player_scores[player_id] += points
                new_score = tournament.player_scores[player_id]
                print(f"  Updated player {player_id}: {old_score} -> {new_score}")
            else:
                # This should never happen due to validation above, but kept for safety
                print(f"  WARNING: Player ID {player_id} not found in player_scores!")

        # Handle Top 8 Cut round scoring separately (for 16-team tournaments)
        if hasattr(tournament, 'has_semifinals') and tournament.has_semifinals:
            tournament.update_top8_cut_scores(round_num, player_results)

        # Handle final round scoring separately
        if round_num == tournament.max_rounds:
            tournament.update_final_round_scores(round_num, player_results)

        # Recalculate team scores from individual player scores
        tournament.calculate_team_scores()

        # Mark table as submitted (prevent double-submission)
        tournament.round_results[round_num]['submitted_tables'].add(table_name)
        print(f"[OK] Table {table_name} marked as submitted for round {round_num}")

        # State transition logic (Phase 3.4)
        total_tables = len(tournament.tables.get(round_num, {}))
        submitted_count = len(tournament.round_results[round_num]['submitted_tables'])
        all_tables_submitted = (submitted_count == total_tables)

        # Transition from TOURNAMENT_SETUP to SWISS_IN_PROGRESS on first table submission
        if tournament.state == TournamentState.TOURNAMENT_SETUP and round_num == 1:
            tournament.transition_to(
                TournamentState.SWISS_IN_PROGRESS,
                f"First table submitted in Round {round_num}"
            )

        # Transition to SWISS_COMPLETE when all Swiss rounds are done
        if round_num == tournament.swiss_rounds_count and all_tables_submitted:
            tournament.transition_to(
                TournamentState.SWISS_COMPLETE,
                f"All {tournament.swiss_rounds_count} Swiss rounds completed"
            )

        # Transition for Top 8 Cut (16-team tournaments)
        if tournament.has_semifinals and round_num == (tournament.swiss_rounds_count + 1) and all_tables_submitted:
            tournament.transition_to(
                TournamentState.TOP8_COMPLETE,
                "Top 8 Cut completed"
            )

        # Transition to FINALS_COMPLETE when finals are done
        if round_num == tournament.max_rounds and all_tables_submitted:
            tournament.transition_to(
                TournamentState.FINALS_COMPLETE,
                "Finals completed, tournament finished"
            )

        # Auto-save after table submission
        tournament.save_backup()

        return jsonify({
            'success': True,
            'message': f'Results submitted for {table_name}',
            'table': table_name,
            'round': round_num,
            'scores': tournament.scores,
            'player_scores': tournament.player_scores
        })

    except Exception as e:
        print(f"[ERROR] submit_table_results failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/get_submission_status/<int:round_num>')
def get_submission_status(round_num):
    """Get submission status for a specific round (Phase 3.1)."""
    try:
        if round_num not in tournament.tables:
            return jsonify({
                'success': False,
                'error': f'Round {round_num} not found',
                'user_message': f'Round {round_num} has not been set up yet.',
                'suggestion': 'Please wait for the previous round to complete.'
            }), 404

        total_tables = len(tournament.tables[round_num])
        submitted_tables = set()

        if round_num in tournament.round_results:
            submitted_tables = tournament.round_results[round_num].get('submitted_tables', set())

        # Convert set to list for JSON serialization
        submitted_list = list(submitted_tables)

        progress_percent = (len(submitted_tables) / total_tables * 100) if total_tables > 0 else 0

        return jsonify({
            'success': True,
            'round': round_num,
            'total_tables': total_tables,
            'submitted_count': len(submitted_tables),
            'submitted_tables': submitted_list,
            'progress_percent': round(progress_percent, 1),
            'is_complete': len(submitted_tables) == total_tables
        })
    except Exception as e:
        print(f"[ERROR] get_submission_status failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Failed to get submission status',
            'suggestion': 'Please refresh the page and try again.'
        }), 500

# ============================================
# SCORE EDITING ENDPOINTS (Task 3.2)
# ============================================

@app.route('/edit_table_results', methods=['POST'])
@with_lock
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

            # Auto-save after edit
            tournament.save_backup()

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


@app.route('/get_score_history/<int:round_num>/<path:table_name>')
def get_score_history(round_num, table_name):
    """Get edit history for a specific table (Task 3.2)."""
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
        print(f"[ERROR] get_score_history failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Failed to retrieve score history.',
            'suggestion': 'Please try again.'
        }), 500

@app.route('/get_tournament_state')
def get_tournament_state():
    """Get current tournament state with intelligent seating"""
    # Apply intelligent seating to all rounds
    seated_tables = {}
    for round_num in tournament.tables.keys():
        seated_tables[round_num] = tournament.apply_intelligent_seating_to_round(round_num)

    # Build submission status for all rounds (Phase 3.1)
    submission_status = {}
    for round_num in tournament.tables.keys():
        total = len(tournament.tables.get(round_num, {}))
        submitted = list(tournament.round_results.get(round_num, {}).get('submitted_tables', set()))
        submission_status[round_num] = {
            'total': total,
            'submitted_count': len(submitted),
            'submitted_tables': submitted,
            'progress_percent': round((len(submitted) / total * 100) if total > 0 else 0, 1),
            'is_complete': len(submitted) == total
        }

    # Convert round_results for JSON serialization (Phase 3.1 - convert sets to lists)
    serializable_round_results = {}
    for round_num, results in tournament.round_results.items():
        serializable_round_results[round_num] = {}
        for key, value in results.items():
            if isinstance(value, set):
                serializable_round_results[round_num][key] = list(value)
            else:
                serializable_round_results[round_num][key] = value

    response_data = {
        'success': True,
        'teams': tournament.teams,
        'scores': tournament.scores,
        'player_scores': tournament.player_scores,
        'current_round': tournament.current_round,
        'round_results': serializable_round_results,
        'tables': seated_tables,
        'swiss_rounds_count': tournament.swiss_rounds_count,
        'max_rounds': tournament.max_rounds,
        'has_semifinals': tournament.has_semifinals,
        'submission_status': submission_status  # Phase 3.1
    }

    # Add legacy group support for backward compatibility (all teams in single group)
    response_data['group_a'] = getattr(tournament, 'tournament_teams', list(tournament.teams.keys()))
    response_data['group_b'] = []  # Empty for single-group tournaments

    # Add final round data if available
    if hasattr(tournament, 'final_round_scores'):
        response_data['final_round_scores'] = tournament.final_round_scores
    if hasattr(tournament, 'swiss_round_scores'):
        response_data['swiss_round_scores'] = tournament.swiss_round_scores

    # Add final standings if Round 5 is available
    final_standings = tournament.calculate_final_round_standings()
    if final_standings:
        response_data['final_standings'] = final_standings

    return jsonify(response_data)

@app.route('/get_tables/<int:round_num>')
def get_tables(round_num):
    """Get table assignments for a specific round with intelligent seating"""
    if round_num in tournament.tables and tournament.tables[round_num]:
        # Apply intelligent seating dynamically based on current scores
        tables_with_seating = tournament.apply_intelligent_seating_to_round(round_num)

        return jsonify({
            'success': True,
            'tables': tables_with_seating,
            'round': round_num,
            'player_scores': tournament.player_scores,  # Include cumulative player scores
            'message': f'Round {round_num} pairings with intelligent seating'
        })
    else:
        return jsonify({
            'success': False,
            'tables': {},
            'round': round_num,
            'error': f'Round {round_num} not available. Please randomize groups first to generate all rounds.'
        })

@app.route('/setup_round/<int:round_num>')
def setup_round(round_num):
    """Get pre-generated tables for a specific round with intelligent seating"""
    if round_num in tournament.tables and tournament.tables[round_num]:
        # Apply intelligent seating dynamically based on current scores
        tables_with_seating = tournament.apply_intelligent_seating_to_round(round_num)

        validation_issues = tournament.validate_swiss_pairings(round_num)

        return jsonify({
            'success': True,
            'round': round_num,
            'tables': tables_with_seating,
            'validation_issues': validation_issues,
            'message': f'Round {round_num} pairings with intelligent seating'
        })
    else:
        return jsonify({
            'success': False,
            'round': round_num,
            'tables': {},
            'validation_issues': [f'Round {round_num} not available'],
            'error': f'Round {round_num} not generated. Please randomize groups first.'
        })

@app.route('/validate_round/<int:round_num>')
def validate_round(round_num):
    """Validate Swiss pairings for a round with group separation checks"""
    # Original validation
    issues = tournament.validate_swiss_pairings(round_num)
    
    # Group separation validation
    group_issues = tournament.validate_group_separation(round_num)
    
    # Swiss repeat validation (check through this round)
    repeat_issues = tournament.validate_swiss_no_repeats(round_num)
    
    all_issues = issues + group_issues + repeat_issues
    
    return jsonify({
        'success': len(all_issues) == 0,
        'round': round_num,
        'issues': all_issues,
        'group_separation_issues': group_issues,
        'repeat_matchup_issues': repeat_issues,
        'original_issues': issues
    })

@app.route('/validate_full_swiss')
def validate_full_swiss():
    """Validate the complete Swiss tournament (all 4 rounds)"""
    full_validation = {
        'overall_success': True,
        'rounds': {},
        'summary': {
            'total_issues': 0,
            'group_violations': 0,
            'repeat_matchups': 0
        }
    }
    
    for round_num in range(1, 5):  # Validate rounds 1-4
        if round_num in tournament.tables:
            group_issues = tournament.validate_group_separation(round_num)
            repeat_issues = tournament.validate_swiss_no_repeats(round_num)
            
            round_issues = group_issues + repeat_issues
            
            full_validation['rounds'][f'Round {round_num}'] = {
                'success': len(round_issues) == 0,
                'issues': round_issues,
                'group_violations': len(group_issues),
                'repeat_matchups': len(repeat_issues)
            }
            
            full_validation['summary']['total_issues'] += len(round_issues)
            full_validation['summary']['group_violations'] += len(group_issues)
            full_validation['summary']['repeat_matchups'] += len(repeat_issues)
            
            if len(round_issues) > 0:
                full_validation['overall_success'] = False
    
    return jsonify(full_validation)

@app.route('/verify_pattern')
def verify_pattern():
    """Verify if our implementation matches the systematic pattern"""
    verification = {}
    
    # Check if we have the expected structure
    if not tournament.group_a or not tournament.group_b:
        return jsonify({'error': 'Groups not set up'})
    
    # For each round, show the expected vs actual pattern
    for round_num in [1, 2, 3, 4]:
        if round_num in tournament.tables:
            round_info = {}
            
            # Group A analysis
            group_a_tables = {}
            for pod in range(4):
                table_name = f'Table {pod + 1}'
                if table_name in tournament.tables[round_num]:
                    players = tournament.tables[round_num][table_name]
                    pattern = []
                    for player in players:
                        # Find team index in group A
                        team_idx = None
                        if player['Team Name'] in tournament.group_a:
                            team_idx = tournament.group_a.index(player['Team Name'])
                        
                        # Find member index
                        team_players = tournament.teams[player['Team Name']]
                        member_idx = None
                        for i, team_player in enumerate(team_players):
                            if team_player['Player ID'] == player['Player ID']:
                                member_idx = i
                                break
                        
                        pattern.append(f"T{team_idx+1}M{member_idx+1}")
                    
                    group_a_tables[f'Pod {pod + 1}'] = pattern
            
            round_info['Group A'] = group_a_tables
            verification[f'Round {round_num}'] = round_info
    
    return jsonify(verification)

@app.route('/validate_systematic_pattern')
def validate_systematic_pattern():
    """Simple validation to check if the systematic pattern prevents repeat matchups"""
    
    # Define the exact patterns from user's example
    patterns = {
        1: [
            ["T1M1", "T2M2", "T3M3", "T4M4"],  # Pod 1
            ["T1M2", "T2M3", "T3M4", "T4M1"],  # Pod 2
            ["T1M3", "T2M4", "T3M1", "T4M2"],  # Pod 3
            ["T1M4", "T2M1", "T3M2", "T4M3"]   # Pod 4
        ],
        2: [
            ["T1M1", "T2M3", "T3M4", "T4M2"],  # Pod 1
            ["T1M2", "T2M4", "T3M1", "T4M3"],  # Pod 2
            ["T1M3", "T2M1", "T3M2", "T4M4"],  # Pod 3
            ["T1M4", "T2M2", "T3M3", "T4M1"]   # Pod 4
        ],
        3: [
            ["T1M1", "T2M4", "T3M2", "T4M3"],  # Pod 1
            ["T1M2", "T2M1", "T3M3", "T4M4"],  # Pod 2
            ["T1M3", "T2M2", "T3M4", "T4M1"],  # Pod 3
            ["T1M4", "T2M3", "T3M1", "T4M2"]   # Pod 4
        ],
        4: [
            ["T1M1", "T2M1", "T3M1", "T4M1"],  # Pod 1
            ["T1M2", "T2M2", "T3M2", "T4M2"],  # Pod 2
            ["T1M3", "T2M3", "T3M3", "T4M3"],  # Pod 3
            ["T1M4", "T2M4", "T3M4", "T4M4"]   # Pod 4
        ]
    }
    
    # Check for duplicate pairings across rounds
    all_pairs = set()
    duplicates = []
    
    for round_num in [1, 2, 3, 4]:
        for pod in patterns[round_num]:
            # Generate all unique pairs in this pod
            for i in range(len(pod)):
                for j in range(i + 1, len(pod)):
                    pair = tuple(sorted([pod[i], pod[j]]))
                    if pair in all_pairs:
                        duplicates.append(f"Round {round_num}: {pair[0]} vs {pair[1]} (repeat)")
                    else:
                        all_pairs.add(pair)
    
    return jsonify({
        "systematic_pattern_valid": len(duplicates) == 0,
        "total_unique_pairings": len(all_pairs),
        "expected_total": 96,  # 4 rounds * 4 pods * 6 pairs per pod = 96
        "duplicate_pairings": duplicates,
        "summary": f"Pattern is {'VALID' if len(duplicates) == 0 else 'INVALID'} - {len(duplicates)} duplicates found"
    })

@app.route('/validate_exact_user_pattern')
def validate_exact_user_pattern():
    """Validate the exact pattern from user's example with Teams 1, 3, 7, 8"""
    
    # Define the EXACT patterns from user's example
    # Group A: Teams 1, 3, 7, 8
    patterns = {
        1: [
            ["T1M1", "T3M2", "T7M3", "T8M4"],  # Pod 1
            ["T1M2", "T3M3", "T7M4", "T8M1"],  # Pod 2
            ["T1M3", "T3M4", "T7M1", "T8M2"],  # Pod 3
            ["T1M4", "T3M1", "T7M2", "T8M3"]   # Pod 4
        ],
        2: [
            ["T1M1", "T3M3", "T7M4", "T8M2"],  # Pod 1
            ["T1M2", "T3M4", "T7M1", "T8M3"],  # Pod 2
            ["T1M3", "T3M1", "T7M2", "T8M4"],  # Pod 3
            ["T1M4", "T3M2", "T7M3", "T8M1"]   # Pod 4
        ],
        3: [
            ["T1M1", "T3M4", "T7M2", "T8M3"],  # Pod 1
            ["T1M2", "T3M1", "T7M3", "T8M4"],  # Pod 2
            ["T1M3", "T3M2", "T7M4", "T8M1"],  # Pod 3
            ["T1M4", "T3M3", "T7M1", "T8M2"]   # Pod 4
        ],
        4: [
            ["T1M1", "T3M1", "T7M1", "T8M1"],  # Pod 1
            ["T1M2", "T3M2", "T7M2", "T8M2"],  # Pod 2
            ["T1M3", "T3M3", "T7M3", "T8M3"],  # Pod 3
            ["T1M4", "T3M4", "T7M4", "T8M4"]   # Pod 4
        ]
    }
    
    # Check for duplicate pairings across rounds
    all_pairs = set()
    duplicates = []
    round_pairs = {}
    
    for round_num in [1, 2, 3, 4]:
        round_pairs[round_num] = []
        for pod_idx, pod in enumerate(patterns[round_num]):
            # Generate all unique pairs in this pod
            for i in range(len(pod)):
                for j in range(i + 1, len(pod)):
                    pair = tuple(sorted([pod[i], pod[j]]))
                    round_pairs[round_num].append(pair)
                    
                    if pair in all_pairs:
                        duplicates.append(f"Round {round_num}: {pair[0]} vs {pair[1]} (repeat)")
                    else:
                        all_pairs.add(pair)
    
    return jsonify({
        "pattern_type": "Exact user example with Teams 1, 3, 7, 8",
        "systematic_pattern_valid": len(duplicates) == 0,
        "total_unique_pairings": len(all_pairs),
        "expected_total": 96,  # 4 rounds * 4 pods * 6 pairs per pod = 96
        "duplicate_count": len(duplicates),
        "duplicate_pairings": duplicates[:10],  # Show first 10 duplicates
        "summary": f"Pattern is {'VALID' if len(duplicates) == 0 else 'INVALID'} - {len(duplicates)} duplicates found",
        "round_pair_counts": {f"Round {r}": len(pairs) for r, pairs in round_pairs.items()}
    })

@app.route('/test_perfect_swiss')
def test_perfect_swiss():
    """Test the perfect Swiss pairing algorithm"""
    if not tournament.group_a or not tournament.group_b:
        return jsonify({'error': 'Groups not set up. Please randomize groups first.'})
    
    # Generate all 4 rounds
    tournament.setup_tables(1)  # This will generate all rounds and cache them
    
    # Validate all rounds
    validation_results = {}
    total_issues = 0
    
    for round_num in range(1, 5):
        if round_num in tournament.tables:
            # Use the new comprehensive validation
            repeat_issues = tournament.validate_swiss_no_repeats(round_num)
            group_issues = tournament.validate_group_separation(round_num)
            
            validation_results[f'Round {round_num}'] = {
                'repeat_matchups': len(repeat_issues),
                'group_violations': len(group_issues),
                'issues': repeat_issues + group_issues
            }
            total_issues += len(repeat_issues) + len(group_issues)
    
    return jsonify({
        'algorithm': 'Perfect Swiss Pairing with Zero Repeats',
        'total_issues': total_issues,
        'perfect_tournament': total_issues == 0,
        'rounds': validation_results,
        'group_a': tournament.group_a,
        'group_b': tournament.group_b,
        'summary': f"Generated 4 Swiss rounds with {total_issues} total issues"
    })

@app.route('/clear_pairings_cache')
def clear_pairings_cache():
    """Clear the cached pairings to regenerate them"""
    if hasattr(tournament, '_perfect_pairings_cache'):
        delattr(tournament, '_perfect_pairings_cache')
        
    # Clear existing tables
    tournament.tables = {}
    
    return jsonify({
        'success': True,
        'message': 'Pairings cache cleared. Next round setup will regenerate all pairings.'
    })

@app.route('/regenerate_round/<int:round_num>', methods=['POST'])
def regenerate_round(round_num):
    """Force regeneration of a specific round's pairings"""
    print(f"Force regenerating Round {round_num} pairings")
    
    # Clear the specific round's tables
    if round_num in tournament.tables:
        del tournament.tables[round_num]
    
    # Force regeneration
    tournament.setup_tables(round_num)
    validation_issues = tournament.validate_swiss_pairings(round_num)
    
    return jsonify({
        'success': True,
        'round': round_num,
        'tables': tournament.tables.get(round_num, {}),
        'validation_issues': validation_issues,
        'message': f'Round {round_num} pairings regenerated successfully'
    })

@app.route('/get_all_swiss_rounds')
def get_all_swiss_rounds():
    """Get all Swiss rounds at once for tournament overview"""
    if not tournament.tables or len(tournament.tables) < tournament.swiss_rounds_count:
        return jsonify({
            'success': False,
            'error': 'Complete Swiss rounds not available. Please setup tournament first.',
            'rounds': {}
        })
    
    # Compile all rounds
    all_rounds = {}
    for round_num in range(1, tournament.swiss_rounds_count + 1):
        if round_num in tournament.tables:
            all_rounds[f'Round {round_num}'] = {
                'tables': tournament.tables[round_num],
                'validation_issues': tournament.validate_swiss_pairings(round_num)
            }
    
    # Calculate total validation summary
    total_issues = 0
    for round_data in all_rounds.values():
        total_issues += len(round_data['validation_issues'])
    
    return jsonify({
        'success': True,
        'message': 'Complete Swiss tournament (locked pairings)',
        'group_a': getattr(tournament, 'tournament_teams', list(tournament.teams.keys())),
        'group_b': [],  # Empty for single-group tournaments
        'rounds': all_rounds,
        'summary': {
            'total_rounds': len(all_rounds),
            'total_issues': total_issues,
            'tournament_status': 'Perfect' if total_issues == 0 else f'{total_issues} issues'
        }
    })

@app.route('/get_semifinals')
def get_semifinals():
    """Get semifinals data if generated"""
    # Check for semifinals_data (new) or semifinals (legacy)
    semifinals_data = None
    if hasattr(tournament, 'semifinals_data') and tournament.semifinals_data:
        semifinals_data = tournament.semifinals_data
    elif hasattr(tournament, 'semifinals') and tournament.semifinals:
        semifinals_data = tournament.semifinals

    if semifinals_data:
        # Determine the semifinals round number
        semifinals_round = tournament.swiss_rounds_count + 1 if tournament.has_semifinals else None

        return jsonify({
            'success': True,
            'semifinals': semifinals_data,
            'round_5_tables': tournament.tables.get(semifinals_round, {}),
            'message': 'Semifinals data retrieved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Semifinals not generated yet. Complete Swiss rounds first.'
        })

@app.route('/get_final_standings')
def get_final_standings():
    """Get final round standings with Swiss round tiebreaker info"""
    standings = tournament.calculate_final_round_standings()
    
    if standings:
        return jsonify({
            'success': True,
            'final_standings': standings,
            'final_round_scores': tournament.final_round_scores,
            'swiss_round_scores': tournament.swiss_round_scores,
            'message': 'Final standings calculated successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Finals not available yet'
        })

@app.route('/tournament_statistics')
def tournament_statistics():
    """Get detailed tournament statistics and validation report"""
    try:
        # Check if tournament has been set up
        if not hasattr(tournament, 'tournament_teams') or not tournament.tournament_teams:
            return jsonify({
                'success': False,
                'message': 'No tournament has been set up yet'
            })
        
        # Check if we have the unified algorithm solution
        if not hasattr(tournament, '_tournament_rounds') or not tournament._tournament_rounds:
            return jsonify({
                'success': False,
                'message': 'Tournament pairings not available'
            })
        
        # Create unified pairing instance for validation
        from unified_swiss_pairing import UnifiedSwissPairing

        unified_pairing = UnifiedSwissPairing(
            tournament.teams,
            tournament.tournament_teams,
            tournament.swiss_rounds_count,
            tournament.scores
        )
        
        # Set the solution and update constraint tracking
        unified_pairing.round_solutions = tournament._tournament_rounds
        
        # Update constraint tracking based on the solution
        for round_solution in tournament._tournament_rounds:
            unified_pairing._update_constraints_after_round(round_solution)
        
        # Generate validation report
        validation_report = unified_pairing.validate_solution(tournament._tournament_rounds)
        
        # Get detailed statistics
        stats = unified_pairing.get_detailed_statistics()
        
        # Calculate additional tournament info
        tournament_info = {
            'total_teams': len(tournament.tournament_teams),
            'total_players': len(tournament.participants),
            'swiss_rounds': tournament.swiss_rounds_count,
            'total_rounds_generated': len(tournament.tables),
            'pods_per_round': len(tournament.tables.get(1, {})) if tournament.tables else 0
        }
        
        # Player journey summary
        player_journey_summary = {}
        if tournament.tables:
            for participant in tournament.participants:
                player_id = participant['Player ID']
                opponents_faced = set()
                
                for round_num in range(1, tournament.swiss_rounds_count + 1):
                    if round_num in tournament.tables:
                        for table_name, players in tournament.tables[round_num].items():
                            if participant in players:
                                for other_player in players:
                                    if other_player['Player ID'] != player_id:
                                        opponents_faced.add(other_player['Player ID'])
                                break
                
                player_journey_summary[player_id] = {
                    'name': participant['Player Name'],
                    'team': participant['Team Name'],
                    'total_opponents': len(opponents_faced),
                    'expected_opponents': tournament.swiss_rounds_count * 3
                }
        
        return jsonify({
            'success': True,
            'tournament_info': tournament_info,
            'validation_report': {
                'is_perfect': validation_report.is_perfect,
                'total_violations': validation_report.total_violations,
                'repeat_opponent_violations': len(validation_report.repeat_opponent_violations),
                'teammate_violations': len(validation_report.teammate_violations),
                'structural_violations': len(validation_report.structural_violations),
                'violation_details': validation_report.repeat_opponent_violations[:10]  # First 10 violations
            },
            'statistics': {
                'total_pairings': stats.total_pairings,
                'expected_pairings': stats.expected_pairings,
                'pairing_efficiency': stats.pairing_efficiency,
                'min_opponents_per_player': stats.min_opponents_per_player,
                'max_opponents_per_player': stats.max_opponents_per_player,
                'perfect_tournament': stats.perfect_tournament,
                'generation_time': stats.generation_time,
                'algorithm_used': stats.algorithm_used
            },
            'player_journey_summary': player_journey_summary
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate tournament statistics'
        })

# ==========================================
# NEW API ENDPOINTS FOR GAP 7 TESTING
# ==========================================

@app.route('/get_teams')
def get_teams():
    """Get all teams and their players"""
    if not tournament.teams:
        return jsonify({
            'success': False,
            'error': 'No teams loaded yet'
        })

    return jsonify({
        'success': True,
        'teams': tournament.teams,
        'team_count': len(tournament.teams),
        'tournament_teams': tournament.tournament_teams
    })

@app.route('/get_scores')
def get_scores():
    """Get current team scores"""
    return jsonify({
        'success': True,
        'scores': tournament.scores,
        'swiss_round_scores': tournament.swiss_round_scores if hasattr(tournament, 'swiss_round_scores') else {},
        'top8_cut_scores': tournament.top8_cut_scores if hasattr(tournament, 'top8_cut_scores') else {},
        'final_round_scores': tournament.final_round_scores if hasattr(tournament, 'final_round_scores') else {}
    })

@app.route('/get_player_scores')
def get_player_scores():
    """Get individual player scores"""
    return jsonify({
        'success': True,
        'player_scores': tournament.player_scores
    })

@app.route('/standings')
def standings():
    """Get current standings (sorted by score)"""
    # Get Swiss round scores for reference (if available)
    swiss_scores = getattr(tournament, 'swiss_round_scores', {})

    # Check if we're in finals phase - use proper finals calculation
    if tournament.state.value in ['finals_in_progress', 'finals_complete']:
        # Use the proper finals calculation which sorts by: Finals pts -> Top8/Swiss tiebreaker
        final_standings = tournament.calculate_final_round_standings()

        if final_standings:
            # Convert final_standings to the format expected by the frontend
            standings_list = [
                {
                    'rank': idx + 1,
                    'team': standing['team'],
                    'score': standing['total_points'],
                    'total_points': standing['total_points'],
                    'swiss_points': standing['swiss_points'],
                    'top8_cut_points': standing.get('top8_cut_points', 0),
                    'final_points': standing['final_points'],
                    'current_phase_points': standing['final_points'],  # Finals points only
                    'players': tournament.teams.get(standing['team'], [])
                }
                for idx, standing in enumerate(final_standings)
            ]

            return jsonify({
                'success': True,
                'standings': standings_list,
                'total_teams': len(standings_list),
                'current_state': tournament.state.value
            })

    # Check if we're in playoff phase (Top Cut)
    is_playoff = tournament.state.value in ['top8_in_progress', 'top8_complete', 'swiss_complete']

    if is_playoff and swiss_scores:
        # During Top 8 playoffs: Sort by current phase score (total - swiss), then Swiss as tiebreaker
        sorted_standings = sorted(
            tournament.scores.items(),
            key=lambda x: (x[1] - swiss_scores.get(x[0], 0), swiss_scores.get(x[0], 0)),
            reverse=True
        )
    else:
        # During Swiss: Sort by total score
        sorted_standings = sorted(
            tournament.scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

    standings_list = [
        {
            'rank': idx + 1,
            'team': team_name,
            'score': score,
            'total_points': score,  # Accumulated total
            'swiss_points': swiss_scores.get(team_name, 0),  # Points from Swiss rounds
            'current_phase_points': score - swiss_scores.get(team_name, 0),  # Current phase only
            'players': tournament.teams.get(team_name, [])
        }
        for idx, (team_name, score) in enumerate(sorted_standings)
    ]

    return jsonify({
        'success': True,
        'standings': standings_list,
        'total_teams': len(standings_list),
        'current_state': tournament.state.value  # Include state for phase detection
    })

@app.route('/bracket_groups/<int:round_num>')
def bracket_groups(round_num):
    """Get team groupings for bracket display based on actual table assignments

    For Top 8 Cut: Returns which teams are in Pod 1 vs Pod 2
    For Finals: Returns all 4 teams in single pod
    """
    swiss_rounds = tournament.swiss_rounds_count
    has_semifinals = hasattr(tournament, 'has_semifinals') and tournament.has_semifinals

    if has_semifinals and round_num == swiss_rounds + 1:
        # Top 8 Cut: Determine pods from actual table assignments
        if round_num in tournament.tables:
            tables = tournament.tables[round_num]

            # Group teams by which tables they appear in
            # Tables 1-4 = Pod 1, Tables 5-8 = Pod 2
            pod1_teams = set()
            pod2_teams = set()

            for table_name, players in tables.items():
                # Extract table number
                table_num_str = table_name.replace('Semifinals Table ', '')
                try:
                    table_num = int(table_num_str)
                    # Get unique teams from this table
                    for player in players:
                        team_name = None
                        # Find which team this player belongs to
                        for t_name, t_players in tournament.teams.items():
                            for t_player in t_players:
                                if t_player['Player ID'] == player['Player ID']:
                                    team_name = t_name
                                    break
                            if team_name:
                                break

                        if team_name:
                            if table_num <= 4:
                                pod1_teams.add(team_name)
                            else:
                                pod2_teams.add(team_name)
                except:
                    pass

            return jsonify({
                'success': True,
                'pod1': sorted(list(pod1_teams)),
                'pod2': sorted(list(pod2_teams)),
                'round_type': 'top8cut'
            })
        else:
            return jsonify({'success': False, 'error': 'Tables not generated yet'})

    elif round_num == tournament.max_rounds:
        # Finals: Single pod with top 4 teams
        if hasattr(tournament, 'finals_data') and tournament.finals_data:
            advancing_teams = tournament.finals_data.get('advancing_teams', [])
            return jsonify({
                'success': True,
                'pod1': advancing_teams,
                'pod2': [],
                'round_type': 'finals'
            })
        else:
            return jsonify({'success': False, 'error': 'Finals not generated yet'})
    else:
        return jsonify({'success': False, 'error': 'Not a playoff round'})

@app.route('/bracket_standings/<int:round_num>')
def bracket_standings(round_num):
    """Get standings for bracket visualization with current round scores only

    Args:
        round_num: The current round number

    Returns:
        Standings with current_round_points (scores earned in this round only)
        Sorted by the appropriate criteria for the round type
    """
    # Determine round type
    swiss_rounds = tournament.swiss_rounds_count
    has_semifinals = hasattr(tournament, 'has_semifinals') and tournament.has_semifinals

    # Determine what scores to use for this round
    if round_num <= swiss_rounds:
        # Swiss rounds: show accumulated Swiss scores
        current_round_scores = tournament.scores
        score_type = 'swiss'
    elif has_semifinals and round_num == swiss_rounds + 1:
        # Top 8 Cut round: show ONLY Top 8 Cut scores
        # Get top 8 teams from Swiss scores, but show their Top 8 Cut scores (or 0 if not yet scored)
        swiss_scores = tournament.swiss_round_scores if hasattr(tournament, 'swiss_round_scores') else tournament.scores
        top8_teams_by_swiss = sorted(swiss_scores.items(), key=lambda x: x[1], reverse=True)[:8]

        current_round_scores = {}
        for team_name, _ in top8_teams_by_swiss:
            # Use Top 8 Cut score if available, otherwise 0
            top8_score = tournament.top8_cut_scores.get(team_name, 0) if hasattr(tournament, 'top8_cut_scores') else 0
            current_round_scores[team_name] = top8_score
        score_type = 'top8cut'

    elif round_num == tournament.max_rounds:
        # Finals round: show ONLY Finals scores
        # Get top 4 teams from previous round, show their Finals scores (or 0 if not yet scored)
        if has_semifinals:
            # 16-team: Get top 4 from Top 8 Cut
            top8_scores = tournament.top8_cut_scores if hasattr(tournament, 'top8_cut_scores') else {}
            swiss_scores = tournament.swiss_round_scores if hasattr(tournament, 'swiss_round_scores') else {}

            # Sort by Top 8 Cut scores (primary) with Swiss (tiebreaker)
            def get_top8_ranking(item):
                team_name, _ = item
                return (top8_scores.get(team_name, 0), swiss_scores.get(team_name, 0))

            top4_teams = sorted(tournament.scores.items(), key=get_top8_ranking, reverse=True)[:4]
        else:
            # 8-team/12-team: Get top 4 from Swiss
            top4_teams = sorted(tournament.scores.items(), key=lambda x: x[1], reverse=True)[:4]

        current_round_scores = {}
        for team_name, _ in top4_teams:
            # Use Finals score if available, otherwise 0
            finals_score = tournament.final_round_scores.get(team_name, 0) if hasattr(tournament, 'final_round_scores') else 0
            current_round_scores[team_name] = finals_score
        score_type = 'finals'
    else:
        # Fallback to total scores
        current_round_scores = tournament.scores
        score_type = 'total'

    # Sort teams by current round scores (with Swiss as tiebreaker for Top 8 Cut / Finals)
    if score_type == 'top8cut' or score_type == 'finals':
        # Sort with Swiss scores as tiebreaker
        swiss_scores = tournament.swiss_round_scores if hasattr(tournament, 'swiss_round_scores') else {}
        def get_ranking_with_tiebreaker(item):
            team_name, current_score = item
            return (current_score, swiss_scores.get(team_name, 0))
        sorted_standings = sorted(current_round_scores.items(), key=get_ranking_with_tiebreaker, reverse=True)
    else:
        sorted_standings = sorted(current_round_scores.items(), key=lambda x: x[1], reverse=True)

    standings_list = []
    for idx, (team_name, current_score) in enumerate(sorted_standings):
        standings_list.append({
            'rank': idx + 1,
            'team': team_name,
            'current_round_points': current_score,  # Scores earned in THIS round only
            'total_points': current_score,  # For bracket display compatibility
            'swiss_points': tournament.swiss_round_scores.get(team_name, 0) if hasattr(tournament, 'swiss_round_scores') else 0,
            'score_type': score_type
        })

    return jsonify({
        'success': True,
        'standings': standings_list,
        'total_teams': len(standings_list),
        'round_num': round_num,
        'score_type': score_type
    })

@app.route('/final_standings')
def final_standings():
    """Get final standings after tournament completion"""
    # Check if tournament is complete
    if not hasattr(tournament, 'finals_data') or not tournament.finals_data:
        return jsonify({
            'success': False,
            'error': 'Tournament not complete yet. Finals must be played first.'
        })

    # Get final standings
    final_standings_data = tournament.calculate_final_round_standings()

    if not final_standings_data:
        return jsonify({
            'success': False,
            'error': 'Unable to calculate final standings'
        })

    return jsonify({
        'success': True,
        'final_standings': final_standings_data,
        'champion': final_standings_data[0] if final_standings_data else None,
        'mvp': tournament.get_mvp() if hasattr(tournament, 'get_mvp') else None
    })

@app.route('/generate_finals')
@require_state(TournamentState.SWISS_COMPLETE, TournamentState.TOP8_COMPLETE)
def generate_finals():
    """Generate finals round (top 4 teams)"""
    try:
        # Check if Swiss rounds are complete
        if len(tournament.submitted_rounds) < tournament.swiss_rounds_count:
            return jsonify({
                'success': False,
                'error': f'Swiss rounds not complete. {tournament.swiss_rounds_count - len(tournament.submitted_rounds)} rounds remaining.'
            })

        # Generate finals based on tournament structure
        if tournament.has_semifinals:
            # 16 teams: Check if semifinals are complete
            semifinals_round = tournament.swiss_rounds_count + 1
            if semifinals_round not in tournament.submitted_rounds:
                return jsonify({
                    'success': False,
                    'error': 'Semifinals not complete yet'
                })
            finals_data = tournament.generate_unified_finals(after_semifinals=True)
        else:
            # 8 teams: Generate finals directly from Swiss
            finals_data = tournament.generate_unified_finals(after_semifinals=False)

        if finals_data:
            # State transition: Finals started (Phase 3.4)
            tournament.transition_to(
                TournamentState.FINALS_IN_PROGRESS,
                "Finals round started"
            )

            return jsonify({
                'success': True,
                'finals_data': finals_data,
                'message': 'Finals generated successfully',
                'finals_round': tournament.max_rounds
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate finals'
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error generating finals'
        })

@app.route('/get_finals')
def get_finals():
    """Get finals data if generated"""
    if hasattr(tournament, 'finals_data') and tournament.finals_data:
        return jsonify({
            'success': True,
            'finals_data': tournament.finals_data,
            'finals_round': tournament.max_rounds,
            'message': 'Finals data retrieved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Finals not generated yet'
        })

@app.route('/get_state_info')
def get_state_info():
    """Get current tournament state and valid next actions (Phase 3.4)."""
    try:
        # Determine valid actions based on current state
        valid_actions = []

        if tournament.state == TournamentState.INITIAL:
            valid_actions = ['load_data']
        elif tournament.state == TournamentState.PARTICIPANTS_LOADED:
            valid_actions = ['setup_tournament', 'load_data']  # Can reload
        elif tournament.state == TournamentState.TOURNAMENT_SETUP:
            valid_actions = ['submit_table_results']
        elif tournament.state == TournamentState.SWISS_IN_PROGRESS:
            valid_actions = ['submit_table_results']
        elif tournament.state == TournamentState.SWISS_COMPLETE:
            if tournament.has_semifinals:
                valid_actions = ['setup_round']  # Auto-generated, but allow manual trigger
            else:
                valid_actions = ['generate_finals']
        elif tournament.state == TournamentState.TOP8_IN_PROGRESS:
            valid_actions = ['submit_table_results']
        elif tournament.state == TournamentState.TOP8_COMPLETE:
            valid_actions = ['generate_finals']
        elif tournament.state == TournamentState.FINALS_IN_PROGRESS:
            valid_actions = ['submit_table_results']
        elif tournament.state == TournamentState.FINALS_COMPLETE:
            valid_actions = []  # Tournament is over

        return jsonify({
            'success': True,
            'current_state': tournament.state.value,
            'valid_actions': valid_actions,
            'state_history': tournament.state_history[-10:],  # Last 10 transitions
            'tournament_info': {
                'swiss_rounds_count': tournament.swiss_rounds_count,
                'current_round': tournament.current_round,
                'max_rounds': tournament.max_rounds,
                'has_semifinals': tournament.has_semifinals,
                'team_count': len(tournament.teams)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'user_message': 'Failed to retrieve state information'
        }), 500

@app.route('/validate_integrity')
def validate_integrity():
    """Validate tournament data integrity"""
    checks_performed = []
    issues = []

    # Check 1: Teams loaded
    if not tournament.teams:
        issues.append('No teams loaded')
    checks_performed.append('Teams loaded')

    # Check 2: Scores initialized
    if not tournament.scores:
        issues.append('Scores not initialized')
    checks_performed.append('Scores initialized')

    # Check 3: Player scores initialized
    if not tournament.player_scores:
        issues.append('Player scores not initialized')
    checks_performed.append('Player scores initialized')

    # Check 4: Team count validation
    team_count = len(tournament.teams)
    if team_count not in [8, 12, 16]:
        issues.append(f'Invalid team count: {team_count} (must be 8, 12, or 16)')
    checks_performed.append('Team count validation')

    # Check 5: Player count validation
    expected_players = team_count * 4
    actual_players = len(tournament.participants)
    if actual_players != expected_players:
        issues.append(f'Player count mismatch: {actual_players} (expected {expected_players})')
    checks_performed.append('Player count validation')

    # Check 6: Tables generated
    if tournament.tables:
        checks_performed.append('Tables generated')
    else:
        issues.append('No tables generated')

    # Check 7: Swiss rounds configuration
    if tournament.swiss_rounds_count not in [4, 5]:
        issues.append(f'Invalid Swiss rounds: {tournament.swiss_rounds_count}')
    checks_performed.append('Swiss rounds configuration')

    return jsonify({
        'valid': len(issues) == 0,
        'checks_performed': checks_performed,
        'issues': issues,
        'total_checks': len(checks_performed),
        'passed_checks': len(checks_performed) - len(issues)
    })

@app.route('/save_backup', methods=['POST'])
def save_backup_endpoint():
    """Manually trigger backup save"""
    try:
        success = tournament.save_backup()
        return jsonify({
            'success': success,
            'message': 'Tournament state saved successfully' if success else 'Failed to save backup'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving backup: {str(e)}'
        }), 500

@app.route('/backup_health', methods=['GET'])
def backup_health():
    """Get backup health status for monitoring"""
    try:
        return jsonify({
            'success': True,
            'last_success': tournament.last_backup_success.isoformat() if tournament.last_backup_success else None,
            'last_failure': tournament.last_backup_failure.isoformat() if tournament.last_backup_failure else None,
            'consecutive_failures': tournament.consecutive_backup_failures,
            'backup_file_exists': os.path.exists(tournament.backup_file),
            'backup_file_size': os.path.getsize(tournament.backup_file) if os.path.exists(tournament.backup_file) else 0,
            'backup_file_path': tournament.backup_file
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reset_tournament', methods=['POST'])
def reset_tournament():
    """Reset tournament to initial state"""
    try:
        # Reset all tournament state
        tournament.participants = []
        tournament.teams = {}
        tournament.tournament_teams = []
        tournament.scores = {}
        tournament.player_scores = {}
        tournament.current_round = 1
        tournament.swiss_rounds_count = 4
        tournament.swiss_rounds_configured = False
        tournament.max_rounds = 6
        tournament.round_results = {}
        tournament.tables = {}
        tournament.final_round_scores = {}
        tournament.semifinal_round_scores = {}
        tournament.swiss_round_scores = {}
        tournament.has_semifinals = False
        tournament.state = TournamentState.INITIAL  # Reset state machine
        tournament.finals_data = None
        tournament.semifinals_data = None

        if hasattr(tournament, 'submitted_rounds'):
            tournament.submitted_rounds = set()

        if hasattr(tournament, 'finalized_rounds'):
            tournament.finalized_rounds = set()

        # Delete backup file on reset
        if os.path.exists(tournament.backup_file):
            os.remove(tournament.backup_file)
            print("[CLEANUP] Backup file deleted")

        return jsonify({
            'success': True,
            'message': 'Tournament reset successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to reset tournament'
        })

# ==========================================
# TIMER ENDPOINTS
# ==========================================

@app.route('/get_timer')
@with_lock
def get_timer():
    """Get current timer state"""
    elapsed = tournament.timer_paused_at
    if tournament.timer_running and tournament.timer_start_time:
        elapsed += (datetime.now() - tournament.timer_start_time).total_seconds()

    return jsonify({
        'running': tournament.timer_running,
        'elapsed': int(elapsed),
        'duration': tournament.timer_duration
    })

@app.route('/control_timer', methods=['POST'])
@with_lock
def control_timer():
    """Control the tournament timer"""
    action = request.json.get('action')
    
    if action == 'start':
        if not tournament.timer_running:
            tournament.timer_start_time = datetime.now()
            tournament.timer_running = True
            
    elif action == 'stop':
        if tournament.timer_running:
            # Add elapsed time to paused_at
            elapsed_since_start = (datetime.now() - tournament.timer_start_time).total_seconds()
            tournament.timer_paused_at += elapsed_since_start
            tournament.timer_running = False
            tournament.timer_start_time = None
            
    elif action == 'reset':
        tournament.timer_running = False
        tournament.timer_start_time = None
        tournament.timer_paused_at = 0
        
    return jsonify({'success': True})

if __name__ == '__main__':
    # Attempt to restore state from backup on startup
    if os.path.exists(tournament.backup_file):
        print("[RESTORE] Restoring tournament state from backup...")
        tournament.load_backup(tournament.backup_file)
    
    
    # Start periodic backup thread (every 5 minutes)
    backup_thread = threading.Thread(
        target=periodic_backup_thread,
        args=(tournament,),
        daemon=True  # Daemon thread will stop when main program exits
    )
    backup_thread.start()
    print("[AUTO-BACKUP] Periodic backup thread started (interval: 5 minutes)")
    import os
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=5001,
        threaded=True,  # Enable concurrent requests (safe with locks)
        use_reloader=False  # Prevent double initialization
    )
