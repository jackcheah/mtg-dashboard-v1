
import unittest
import os
import shutil
from tournament_dashboard import TournamentManager
from unified_swiss_pairing import UnifiedSwissPairing

class TestBackupRestore(unittest.TestCase):
    def setUp(self):
        self.backup_file = 'test_tournament_state.json.bak'
        # Clean up any existing backup
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)
            
    def tearDown(self):
        # Clean up after test
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def test_full_backup_restore_cycle(self):
        print("\n=== Testing Backup/Restore Cycle ===")
        
        # 1. Setup Initial Tournament
        print("1. Setting up initial tournament...")
        tm_original = TournamentManager()
        tm_original.create_sample_data(8)
        tm_original.setup_tournament(swiss_rounds=4)
        
        # Verify initial state
        self.assertEqual(len(tm_original.teams), 8)
        self.assertEqual(tm_original.current_round, 1)
        self.assertTrue(len(tm_original._tournament_rounds) > 0)
        
        # 2. Save State
        print("2. Saving state...")
        success = tm_original.save_state(self.backup_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.backup_file))
        
        original_tables_r1 = tm_original.tables[1]
        
        # 3. Create Fresh Instance (Simulate Restart)
        print("3. Creating fresh manager instance...")
        tm_restored = TournamentManager()
        
        # 3b. Verify Fresh Instance is Empty (No Auto-Load)
        print("3b. Verifying fresh instance is empty (no auto-load)...")
        self.assertEqual(len(tm_restored.teams), 0)
        self.assertEqual(tm_restored.current_round, 1)        
        self.assertEqual(len(tm_restored.tables), 0)
        
        # 4. Load State
        print("4. Loading state...")
        success = tm_restored.load_state(self.backup_file)
        self.assertTrue(success)
        
        # 5. Verify State Restoration
        print("5. Verifying restored state...")
        self.assertEqual(len(tm_restored.teams), 8)
        self.assertEqual(tm_restored.swiss_rounds_count, 4)
        
        # Check tables match
        # Note: keys might be strings in JSON but converted back to int in load_state
        self.assertEqual(len(tm_restored.tables[1]), 8) 
        
        # Check specific table assignment to ensure determinism
        # (Assuming tables order is preserved)
        table1_orig = original_tables_r1['Table 1']
        table1_rest = tm_restored.tables[1]['Table 1']
        
        # Extract player IDs for comparison
        ids_orig = sorted([p['Player ID'] for p in table1_orig])
        ids_rest = sorted([p['Player ID'] for p in table1_rest])
        self.assertEqual(ids_orig, ids_rest)
        
        # 6. Verify Logic Engine Rehydration
        print("6. Verifying logic engine rehydration...")
        self.assertIsNotNone(tm_restored._unified_pairing)
        self.assertTrue(hasattr(tm_restored._unified_pairing, 'used_pairings'))
        
        # Engine should know about Round 1 pairings
        # Check if used_pairings is populated
        self.assertTrue(len(tm_restored._unified_pairing.used_pairings) > 0)
        
        # 7. Verify Forward Logic (Generate Round 2)
        print("7. Testing generation of Round 2 from restored state...")
        # Submit some dummy results for Round 1 to allow Round 2 generation
        results = []
        for pid in tm_restored.player_scores:
            results.append({'player_id': pid, 'points': 3}) # Everyone draws/wins
        
        tm_restored.submit_player_results(1, results)
        
        # Generate Round 2
        success = tm_restored.generate_swiss_round(2)
        self.assertTrue(success)
        self.assertIn(2, tm_restored.tables)
        
        print("   [SUCCESS] Round 2 generated successfully from restored state!")

if __name__ == '__main__':
    unittest.main()
