
import os
import openpyxl

def generate_teams():
    # Target path required by the backend
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../participants"))
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, "participant_team.xlsx")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Teams"
    
    # Headers suitable for "Standard column format"
    headers = ["Team Name", "Player Name", "Player ID"]
    ws.append(headers)
    
    # Generate 16 teams with 4 players each
    player_id = 1
    for i in range(16):
        team_name = f"Team {chr(65+i)}" # Team A, Team B...
        for p in range(1, 5):
            player_name = f"P{p}_{chr(65+i)}"
            ws.append([team_name, player_name, player_id])
            player_id += 1
            
    wb.save(filepath)
    print(f"Generated {filepath}")

if __name__ == "__main__":
    generate_teams()
