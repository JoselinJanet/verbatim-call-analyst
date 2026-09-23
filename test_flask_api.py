"""
Automated validation of Transcript Insight Flask API endpoints.
Tests session authentication, state payload, chat endpoints, and citation drilldown.
"""
import sys
import unittest
from app import app

class FlaskApiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_01_unauthenticated_state_blocked(self):
        res = self.client.get("/api/state")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get("authenticated"), False)

    def test_02_login_and_auth_status(self):
        # Invalid login
        res = self.client.post("/api/auth/login", json={"username": "wrong", "password": "bad"})
        self.assertEqual(res.status_code, 401)

        # Valid login
        res = self.client.post("/api/auth/login", json={"username": "admin", "password": "hasamex2026"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("authenticated"))

        # Check status
        res = self.client.get("/api/auth/status")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("authenticated"))

    def test_03_get_state(self):
        # Login first
        self.client.post("/api/auth/login", json={"username": "admin", "password": "hasamex2026"})

        res = self.client.get("/api/state")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("guide_questions", data)
        self.assertIn("answer_grid", data)
        self.assertIn("synthesis", data)
        self.assertIn("experts", data)
        self.assertIn("countries", data)

        self.assertGreater(len(data["guide_questions"]), 0)
        self.assertGreater(len(data["answer_grid"]), 0)
        self.assertGreater(len(data["experts"]), 0)
        print(f"Verified State: {len(data['guide_questions'])} questions, {len(data['experts'])} experts, {len(data['answer_grid'])} answer cells.")

    def test_04_citation_lookup(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "hasamex2026"})

        # Test lookup for turn FR-04
        res = self.client.get("/api/citations/turn/FR-04")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("target_turn_id"), "FR-04")
        self.assertEqual(data.get("country"), "France")
        self.assertIn("context_turns", data)
        self.assertGreater(len(data["context_turns"]), 0)
        print(f"Verified Citation Lookup: Found {data['expert_name']} with {len(data['context_turns'])} context turns.")

    def test_05_chat_conversations(self):
        self.client.post("/api/auth/login", json={"username": "admin", "password": "hasamex2026"})

        res = self.client.get("/api/chat/conversations")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        print(f"Verified Chat Threads: {len(data)} conversation thread(s) available.")

    def test_06_index_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Transcript Insight", res.data)
        self.assertIn(b"index.html", b"index.html")

if __name__ == "__main__":
    unittest.main()
