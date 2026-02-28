from typing import Dict, Optional

from app.models.session import SessionData


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    def create(self, session: SessionData) -> None:
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)

    def update(self, session: SessionData) -> None:
        self._sessions[session.session_id] = session
