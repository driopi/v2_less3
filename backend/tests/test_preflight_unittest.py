import os
import unittest
import base64

from fastapi.testclient import TestClient

os.environ["WHISPER_MODE"] = "mock"
os.environ["PRELOAD_WHISPER_ON_STARTUP"] = "false"
os.environ["TTS_PROVIDER"] = "mock"
os.environ["TTS_MODEL"] = "facebook/mms-tts-rus"
os.environ["LLM_PROVIDER"] = "mock"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("HUGGINGFACE_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

from app.main import app  # noqa: E402


def fake_webm_b64() -> str:
    return base64.b64encode(b"RIFF....FAKEAUDIO").decode("utf-8")


class PreflightFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._client_cm = TestClient(app)
        self.client = self._client_cm.__enter__()

    def tearDown(self) -> None:
        self._client_cm.__exit__(None, None, None)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertTrue(payload["whisper_loaded"])

    def test_9_question_journey(self):
        start = self.client.post(
            "/api/session/start",
            json={
                "goal": "Заполнить чеклист для пресейл звонка",
                "topic": "CRM интеграция",
            },
        )
        self.assertEqual(start.status_code, 200)
        session = start.json()
        session_id = session["session_id"]
        questions = session["questions"]
        previous_question_sets = {tuple(q["text"] for q in questions)}

        self.assertEqual(session["round"], 1)
        self.assertEqual(len(questions), 3)

        for expected_round in [1, 2, 3]:
            q_ids = [q["id"] for q in questions]
            payload = {
                "question_ids": ",".join(q_ids),
                "audio_base64_files": [fake_webm_b64(), fake_webm_b64(), fake_webm_b64()],
            }
            submit = self.client.post(f"/api/session/{session_id}/submit", json=payload)

            self.assertEqual(submit.status_code, 200)
            payload = submit.json()
            self.assertTrue(payload["round_summary"])

            if expected_round < 3:
                self.assertFalse(payload["is_complete"])
                self.assertEqual(payload["round"], expected_round + 1)
                self.assertEqual(len(payload["questions"]), 3)
                questions = payload["questions"]
                question_set = tuple(q["text"] for q in questions)
                self.assertNotIn(question_set, previous_question_sets)
                previous_question_sets.add(question_set)
            else:
                self.assertTrue(payload["is_complete"])
                self.assertTrue(payload["checklist_preview"])

        results = self.client.get(f"/api/session/{session_id}/results")
        self.assertEqual(results.status_code, 200)
        results_payload = results.json()
        self.assertTrue(results_payload["is_complete"])
        self.assertGreaterEqual(len(results_payload["checklist"]), 1)
        self.assertIn("Чеклист созвона", results_payload["markdown"])
        self.assertIsNotNone(results_payload["portrait"])
        self.assertGreaterEqual(results_payload["portrait"]["emotional_stability"], 1)
        self.assertLessEqual(results_payload["portrait"]["emotional_stability"], 10)
        self.assertIsInstance(results_payload["portrait"]["trigger_questions"], list)

        download = self.client.get(f"/api/session/{session_id}/download")
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment; filename=checklist-", download.headers["content-disposition"])
        self.assertIn("Чеклист созвона", download.text)

        summary_audio = self.client.get(f"/api/session/{session_id}/summary-audio")
        self.assertEqual(summary_audio.status_code, 200)
        self.assertTrue(summary_audio.headers["content-type"].startswith("audio/"))
        self.assertGreater(len(summary_audio.content), 2048)


if __name__ == "__main__":
    unittest.main()
