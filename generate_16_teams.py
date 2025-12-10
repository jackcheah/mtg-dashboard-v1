import openpyxl
from openpyxl import Workbook
import os

def generate_16_teams_file():
    # Create directory if it doesn't exist
    if not os.path.exists('participants'):
        os.makedirs('participants')
        
    wb = Workbook()
    ws = wb.active
    ws.title = "Teams"
    
    # Headers
    headers = ["Player ID", "Player Name", "Team Name"]
    ws.append(headers)
    
    # Generate 16 teams with 4 players each
    teams = [f"Team {chr(65+i)}" for i in range(16)] # Team A to Team P
    
    player_id = 1
    for team in teams:
        for i in range(4):
            player_name = f"Player {player_id} ({team})"
            ws.append([player_id, player_name, team])
            player_id += 1
            
    # Save the file
    filepath = 'participants/participant_team.xlsx'
    wb.save(filepath)
    print(f"Successfully created {filepath} with {len(teams)} teams and {player_id-1} players.")

if __name__ == "__main__":
    generate_16_teams_file()
