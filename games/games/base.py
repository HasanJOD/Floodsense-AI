from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from models.game_state import GameSession


class GameService(ABC):
    """Base class for all flood-management mini-game services."""

    @property
    @abstractmethod
    def game_id(self) -> str:
        pass

    @abstractmethod
    def create_session(self, session_id: str) -> GameSession:
        pass

    @abstractmethod
    def get_state(self, session_id: str) -> dict:
        pass

    @abstractmethod
    def handle_action(self, session_id: str, action: str, payload: dict) -> dict:
        pass

    def extra_endpoints(self) -> dict[str, Any]:
        return {}