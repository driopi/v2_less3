import base64


def _fake_webm_b64() -> str:
    return base64.b64encode(b"RIFF....FAKEAUDIO").decode("utf-8")


def _complete_session(client):
    start = client.post(
        "/api/session/start",
        json={
            "goal": "Заполнить чеклист для пресейл звонка",
            "topic": "CRM интеграция",
        },
    )
    assert start.status_code == 200
    session = start.json()
    session_id = session["session_id"]
    questions = session["questions"]
    previous_question_sets = {tuple(q["text"] for q in questions)}

    for expected_round in [1, 2, 3]:
        q_ids = [q["id"] for q in questions]
        payload = {
            "question_ids": ",".join(q_ids),
            "audio_base64_files": [_fake_webm_b64(), _fake_webm_b64(), _fake_webm_b64()],
        }
        submit = client.post(f"/api/session/{session_id}/submit", json=payload)
        assert submit.status_code == 200
        payload = submit.json()
        assert payload["round_summary"]

        if expected_round < 3:
            assert payload["is_complete"] is False
            assert payload["round"] == expected_round + 1
            assert len(payload["questions"]) == 3
            questions = payload["questions"]
            question_set = tuple(q["text"] for q in questions)
            assert question_set not in previous_question_sets
            previous_question_sets.add(question_set)
        else:
            assert payload["is_complete"] is True
            assert payload["checklist_preview"]

    return session_id


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "healthy"
    assert payload["whisper_loaded"] is True


def test_full_9_question_flow_and_results(client):
    session_id = _complete_session(client)

    results = client.get(f"/api/session/{session_id}/results")
    assert results.status_code == 200
    results_payload = results.json()
    assert results_payload["is_complete"] is True
    assert len(results_payload["checklist"]) >= 1
    assert "Чеклист созвона" in results_payload["markdown"]
    assert results_payload["portrait"] is not None
    assert 1 <= results_payload["portrait"]["emotional_stability"] <= 10
    assert 1 <= results_payload["portrait"]["hidden_tension"] <= 10
    assert isinstance(results_payload["portrait"]["trigger_questions"], list)
    assert isinstance(results_payload["portrait"]["triggers"], list)

    download = client.get(f"/api/session/{session_id}/download")
    assert download.status_code == 200
    assert "attachment; filename=checklist-" in download.headers["content-disposition"]
    assert "Чеклист созвона" in download.text


def test_summary_audio_after_completion(client):
    session_id = _complete_session(client)
    res = client.get(f"/api/session/{session_id}/summary-audio")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("audio/")
    assert len(res.content) > 2048


def test_transcribe_preview(client):
    res = client.post(
        "/api/session/transcribe",
        json={"audio_base64": _fake_webm_b64(), "filename": "preview.webm"},
    )
    assert res.status_code == 200
    assert "mock transcript" in res.json()["transcript"]
