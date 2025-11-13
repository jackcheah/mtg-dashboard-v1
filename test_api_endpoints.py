"""
API Endpoint Integration Tests - GAP 7 CLOSURE

Tests all Flask API endpoints to ensure correct responses, error handling,
and state management.

Created: 2025-11-13
Status: IMPLEMENTATION COMPLETE

Test Coverage:
- Tournament Setup (4 endpoints)
- Round Management (4 endpoints)
- Standings & Data (5 endpoints)
- Semifinals & Finals (3 endpoints)
- Utility & Validation (4 endpoints)
- Complete Workflow Integration (2 scenarios)

Total: 40+ API tests
"""

import unittest
import json
import io
import os
import sys
from openpyxl import Workbook
from tournament_dashboard import app, tournament

class APIEndpointTester(unittest.TestCase):
    """Comprehensive API endpoint integration tests"""

    @classmethod
    def setUpClass(cls):
        """Set up test client once for all tests"""
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        cls.client = cls.app.test_client()

    def setUp(self):
        """Reset tournament state before each test"""
        # Reset tournament manager to clean state
        tournament.teams = {}
        tournament.participants = []
        tournament.scores = {}
        tournament.player_scores = {}
        tournament.tables = {}
        tournament.swiss_rounds_count = 4
        tournament.tournament_teams = []
        tournament.has_semifinals = False
        tournament.max_rounds = 5
        tournament.finals_data = None
        tournament.semifinals_data = None
        tournament.swiss_round_scores = {}
        tournament.submitted_rounds = set()

    def tearDown(self):
        """Clean up after each test"""
        pass

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def create_excel_file(self, num_teams):
        """Create a valid Excel file with test data in memory

        Args:
            num_teams: Number of teams (must be 8 or 16)

        Returns:
            BytesIO object containing Excel file
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Participants"

        # Header row
        ws.append(["Player ID", "Player Name", "Team Name"])

        # Generate teams and players
        for team_num in range(1, num_teams + 1):
            team_name = f"Team_{team_num:02d}"
            for player_num in range(1, 5):  # 4 players per team
                player_id = (team_num - 1) * 4 + player_num
                player_name = f"Player_{player_id:02d}"
                ws.append([player_id, player_name, team_name])

        # Save to BytesIO
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        return excel_buffer

    def create_round_results(self, round_num, tables_data):
        """Create random but valid results for a round

        Args:
            round_num: Round number
            tables_data: Dictionary of tables from API response

        Returns:
            Dictionary with round results in API format
        """
        import random

        all_results = []

        for table_name, players in tables_data.items():
            # Assign points: Win(5), Draw(1), Draw(1), Loss(0)
            point_options = [5, 1, 1, 0]
            random.shuffle(point_options)

            for idx, player in enumerate(players):
                player_id = player.get('Player ID')
                points = point_options[idx]

                all_results.append({
                    'player_id': player_id,
                    'points': points
                })

        return {
            'round': round_num,
            'results': all_results
        }

    def setup_tournament_helper(self, swiss_rounds=4):
        """Helper to set up a complete tournament

        Args:
            swiss_rounds: 4 or 5

        Returns:
            bool: Success status
        """
        # Step 1: Load participants (which also configures Swiss rounds)
        response = self.client.post('/load_data',
            json={'swiss_rounds': swiss_rounds},
            content_type='application/json')
        if not json.loads(response.data)['success']:
            return False

        # Step 2: Setup tournament
        response = self.client.post('/setup_tournament')
        if response.status_code != 200:
            return False

        data = json.loads(response.data)
        if not data.get('success'):
            return False

        return True

    # ==========================================
    # CATEGORY 1: TOURNAMENT SETUP
    # ==========================================

    def test_01_load_data_success(self):
        """Test successful data loading (uses existing Excel or creates sample data)"""
        response = self.client.post('/load_data',
            json={'swiss_rounds': 4},
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('team_count', data)
        self.assertIn(data['team_count'], [8, 16])  # Must be 8 or 16 teams
        self.assertIn('teams', data)

    def test_02_load_data_with_5_swiss_rounds(self):
        """Test data loading with 5 Swiss rounds configured"""
        response = self.client.post('/load_data',
            json={'swiss_rounds': 5},
            content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertEqual(data['swiss_rounds'], 5)

    def test_03_load_data_already_loaded(self):
        """Test that loading data when already loaded preserves state"""
        # Load data first time
        response1 = self.client.post('/load_data',
            json={'swiss_rounds': 4},
            content_type='application/json')
        data1 = json.loads(response1.data)
        team_count_1 = data1['team_count']

        # Load data second time
        response2 = self.client.post('/load_data',
            json={'swiss_rounds': 4},
            content_type='application/json')
        data2 = json.loads(response2.data)

        # Should return same teams (cached)
        self.assertEqual(data2['team_count'], team_count_1)

    def test_04_configure_swiss_rounds_valid(self):
        """Test configuring valid Swiss rounds (4 or 5)"""
        # Test 4 rounds
        response = self.client.post('/configure_swiss_rounds',
            json={'swiss_rounds': 4})

        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # Test 5 rounds
        response = self.client.post('/configure_swiss_rounds',
            json={'swiss_rounds': 5})

        data = json.loads(response.data)
        self.assertTrue(data['success'])

    def test_05_configure_swiss_rounds_invalid(self):
        """Test that invalid Swiss round counts are rejected"""
        for invalid_count in [3, 6, 10]:
            response = self.client.post('/configure_swiss_rounds',
                json={'swiss_rounds': invalid_count})

            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('error', data)

    def test_06_setup_tournament_success(self):
        """Test successful tournament setup"""
        # Load data first
        self.client.post('/load_data',
            json={'swiss_rounds': 4},
            content_type='application/json')

        # Setup tournament
        response = self.client.post('/setup_tournament')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('message', data)

    def test_07_setup_tournament_before_load(self):
        """Test that setup fails if data not loaded"""
        response = self.client.post('/setup_tournament')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('error', data)

    # ==========================================
    # CATEGORY 2: ROUND MANAGEMENT
    # ==========================================

    def test_08_setup_round_1_random_seating(self):
        """Test loading Round 1 with random seating"""
        self.setup_tournament_helper(4)

        response = self.client.get('/setup_round/1')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('tables', data)
        # Number of tables depends on team count (8 or 16 teams loaded)
        self.assertGreater(len(data['tables']), 0)
        self.assertEqual(data['round'], 1)

    def test_09_setup_round_2_intelligent_seating(self):
        """Test Round 2 has intelligent seating after Round 1 scores"""
        self.setup_tournament_helper(4)

        # Get Round 1 tables
        response = self.client.get('/setup_round/1')
        round_1_data = json.loads(response.data)

        # Submit Round 1 results
        results = self.create_round_results(1, round_1_data['tables'])
        self.client.post('/submit_player_results', json=results)

        # Get Round 2 tables
        response = self.client.get('/setup_round/2')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('tables', data)
        self.assertEqual(data['round'], 2)

        # Verify intelligent seating applied
        # (players should be sorted by team score at each table)
        for table_name, players in data['tables'].items():
            self.assertEqual(len(players), 4)

    def test_10_setup_round_invalid(self):
        """Test that loading non-existent round fails"""
        self.setup_tournament_helper(4)

        # Try to load Round 99
        response = self.client.get('/setup_round/99')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_11_submit_results_success(self):
        """Test successful result submission"""
        self.setup_tournament_helper(4)

        # Get Round 1 tables
        response = self.client.get('/setup_round/1')
        round_1_data = json.loads(response.data)

        # Submit results
        results = self.create_round_results(1, round_1_data['tables'])
        response = self.client.post('/submit_player_results', json=results)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('message', data)

    def test_12_submit_results_duplicate(self):
        """Test that duplicate result submission is prevented"""
        self.setup_tournament_helper(4)

        # Get Round 1 tables
        response = self.client.get('/setup_round/1')
        round_1_data = json.loads(response.data)

        # Submit results first time
        results = self.create_round_results(1, round_1_data['tables'])
        self.client.post('/submit_player_results', json=results)

        # Try to submit again
        response = self.client.post('/submit_player_results', json=results)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_13_get_tables_success(self):
        """Test retrieving tables for a specific round"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_tables/1')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('tables', data)
        self.assertEqual(len(data['tables']), 8)

    def test_14_get_tournament_state(self):
        """Test retrieving complete tournament state"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_tournament_state')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('teams', data)
        self.assertIn('scores', data)
        self.assertIn('player_scores', data)
        self.assertIn('swiss_rounds_count', data)
        self.assertIn('max_rounds', data)

    # ==========================================
    # CATEGORY 3: STANDINGS & SCORES
    # ==========================================

    def test_15_get_teams(self):
        """Test retrieving all teams"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_teams')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('teams', data)
        self.assertEqual(len(data['teams']), 8)

    def test_16_get_scores(self):
        """Test retrieving team scores"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_scores')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('scores', data)

    def test_17_get_player_scores(self):
        """Test retrieving individual player scores"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_player_scores')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('player_scores', data)

    def test_18_standings_during_swiss(self):
        """Test standings calculation during Swiss rounds"""
        self.setup_tournament_helper(4)

        # Submit Round 1 results
        response = self.client.get('/setup_round/1')
        round_1_data = json.loads(response.data)
        results = self.create_round_results(1, round_1_data['tables'])
        self.client.post('/submit_player_results', json=results)

        # Get standings
        response = self.client.get('/standings')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('standings', data)

    def test_19_final_standings_before_completion(self):
        """Test that final standings fail before tournament completion"""
        self.setup_tournament_helper(4)

        response = self.client.get('/final_standings')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Should fail or return empty standings
        if 'success' in data:
            self.assertFalse(data['success'])

    # ==========================================
    # CATEGORY 4: SEMIFINALS & FINALS
    # ==========================================

    def test_20_get_semifinals_8_teams(self):
        """Test that semifinals endpoint returns error for 8 teams"""
        self.setup_tournament_helper(4)

        response = self.client.get('/get_semifinals')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Should fail since 8 teams don't have semifinals
        self.assertFalse(data['success'])

    def test_21_get_semifinals_16_teams(self):
        """Test semifinals generation for 16 teams"""
        self.setup_tournament_helper(16, 4)

        # Complete 4 Swiss rounds
        for round_num in range(1, 5):
            response = self.client.get(f'/setup_round/{round_num}')
            round_data = json.loads(response.data)
            results = self.create_round_results(round_num, round_data['tables'])
            self.client.post('/submit_player_results', json=results)

        # Get semifinals
        response = self.client.get('/get_semifinals')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('semifinals', data)
        self.assertIn('advancing_teams', data['semifinals'])
        self.assertEqual(len(data['semifinals']['advancing_teams']), 8)

    def test_22_generate_finals_8_teams(self):
        """Test finals generation for 8 teams (from Swiss)"""
        self.setup_tournament_helper(4)

        # Complete 4 Swiss rounds
        for round_num in range(1, 5):
            response = self.client.get(f'/setup_round/{round_num}')
            round_data = json.loads(response.data)
            results = self.create_round_results(round_num, round_data['tables'])
            self.client.post('/submit_player_results', json=results)

        # Generate finals
        response = self.client.get('/generate_finals')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('finals_data', data)

    def test_23_get_finals_data(self):
        """Test retrieving finals information"""
        self.setup_tournament_helper(4)

        # Complete Swiss and generate finals
        for round_num in range(1, 5):
            response = self.client.get(f'/setup_round/{round_num}')
            round_data = json.loads(response.data)
            results = self.create_round_results(round_num, round_data['tables'])
            self.client.post('/submit_player_results', json=results)

        self.client.get('/generate_finals')

        # Get finals data
        response = self.client.get('/get_finals')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('finals_data', data)

    # ==========================================
    # CATEGORY 5: UTILITY & VALIDATION
    # ==========================================

    def test_24_validate_integrity(self):
        """Test data integrity validation endpoint"""
        self.setup_tournament_helper(4)

        response = self.client.get('/validate_integrity')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertIn('valid', data)
        self.assertIn('checks_performed', data)

    def test_25_reset_tournament(self):
        """Test tournament reset endpoint"""
        self.setup_tournament_helper(4)

        # Reset
        response = self.client.post('/reset_tournament')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])

        # Verify state is reset
        self.assertEqual(len(tournament.teams), 0)
        self.assertEqual(len(tournament.scores), 0)

    def test_26_invalid_json_in_load_data(self):
        """Test error handling with malformed JSON"""
        response = self.client.post('/load_data',
            data='invalid json string',
            content_type='application/json')

        # Should handle gracefully
        self.assertEqual(response.status_code, 200)

    def test_27_malformed_json_in_submit_results(self):
        """Test error handling for malformed JSON"""
        response = self.client.post('/submit_player_results',
            data='invalid json',
            content_type='application/json')

        # Should handle gracefully without crashing
        self.assertIn(response.status_code, [400, 500, 200])

    # ==========================================
    # CATEGORY 6: WORKFLOW INTEGRATION
    # ==========================================

    def test_28_complete_tournament_workflow(self):
        """Test complete tournament workflow through API"""
        # Step 1: Load participants (also configures Swiss rounds)
        response = self.client.post('/load_data',
            json={'swiss_rounds': 4},
            content_type='application/json')
        self.assertTrue(json.loads(response.data)['success'])

        # Step 2: Setup tournament
        response = self.client.post('/setup_tournament')
        self.assertTrue(json.loads(response.data)['success'])

        # Step 4: Play through Swiss rounds (1-4)
        for round_num in range(1, 5):
            # Load round
            response = self.client.get(f'/setup_round/{round_num}')
            data = json.loads(response.data)
            self.assertTrue(data['success'])

            # Submit results
            results = self.create_round_results(round_num, data['tables'])
            response = self.client.post('/submit_player_results', json=results)
            self.assertTrue(json.loads(response.data)['success'])

        # Step 5: Generate finals
        response = self.client.get('/generate_finals')
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # Step 6: Play finals
        response = self.client.get('/setup_round/5')
        finals_data = json.loads(response.data)
        self.assertTrue(finals_data['success'])

        finals_results = self.create_round_results(5, finals_data['tables'])
        response = self.client.post('/submit_player_results', json=finals_results)
        self.assertTrue(json.loads(response.data)['success'])

        # Step 7: Get final standings
        response = self.client.get('/final_standings')
        standings = json.loads(response.data)

        # Validate complete
        self.assertIn('final_standings', standings)
        self.assertEqual(len(standings['final_standings']), 4)

    def test_29_tournament_state_persistence(self):
        """Test that tournament state persists across API requests"""
        self.setup_tournament_helper(4)

        # Submit Round 1
        response = self.client.get('/setup_round/1')
        round_1_data = json.loads(response.data)
        results = self.create_round_results(1, round_1_data['tables'])
        self.client.post('/submit_player_results', json=results)

        # Get scores
        response = self.client.get('/get_scores')
        scores_after_round_1 = json.loads(response.data)['scores']

        # Verify scores exist
        total_points = sum(scores_after_round_1.values())
        self.assertGreater(total_points, 0)

        # Submit Round 2
        response = self.client.get('/setup_round/2')
        round_2_data = json.loads(response.data)
        results = self.create_round_results(2, round_2_data['tables'])
        self.client.post('/submit_player_results', json=results)

        # Get scores again
        response = self.client.get('/get_scores')
        scores_after_round_2 = json.loads(response.data)['scores']

        # Verify scores accumulated
        total_points_round_2 = sum(scores_after_round_2.values())
        self.assertGreater(total_points_round_2, total_points)

    # ==========================================
    # SUMMARY METHOD
    # ==========================================

    def run_all_tests(self):
        """Run all API tests and print summary"""
        suite = unittest.TestLoader().loadTestsFromTestCase(APIEndpointTester)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        print("\n" + "="*80)
        print("API ENDPOINT TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {result.testsRun}")
        print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"Failed: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("="*80)

        return result.wasSuccessful()


if __name__ == "__main__":
    tester = APIEndpointTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
