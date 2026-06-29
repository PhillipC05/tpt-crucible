"""Spark Conversation Replay — accept Spark conversation JSON for regression benchmarking."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class ConversationTurn:
    role: str
    content: str
    tokens_per_second: float = 0.0
    hardware: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content[:200],
            "tokens_per_second": round(self.tokens_per_second, 2),
            "hardware": self.hardware,
        }


@dataclass
class SparkConversation:
    model_name: str
    turns: list[ConversationTurn]
    total_tokens: int = 0
    avg_tps: float = 0.0

    def __post_init__(self):
        if self.turns:
            tps_values = [t.tokens_per_second for t in self.turns if t.tokens_per_second > 0]
            self.avg_tps = sum(tps_values) / len(tps_values) if tps_values else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "turn_count": len(self.turns),
            "avg_tps": round(self.avg_tps, 2),
            "turns": [t.to_dict() for t in self.turns[:5]],
        }


class SparkReplayLoader:
    """Load and replay Spark conversation JSON files."""

    def __init__(self):
        self.conversations: list[SparkConversation] = []

    def load_conversation(self, path: Path) -> SparkConversation | None:
        try:
            data = json.loads(path.read_text())
            turns = []
            for turn_data in data.get("conversations", data.get("messages", [])):
                turns.append(ConversationTurn(
                    role=turn_data.get("role", "user"),
                    content=turn_data.get("content", turn_data.get("message", "")),
                    tokens_per_second=turn_data.get("tokens_per_second", turn_data.get("tps", 0)),
                    hardware=turn_data.get("hardware", ""),
                ))
            conv = SparkConversation(
                model_name=data.get("model", path.stem),
                turns=turns,
            )
            self.conversations.append(conv)
            return conv
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def get_baselines(self) -> dict[str, float]:
        baselines: dict[str, float] = {}
        for conv in self.conversations:
            if conv.avg_tps > 0:
                baselines[conv.model_name] = conv.avg_tps
        return baselines

    def compare_with_crucible(
        self,
        model_name: str,
        crucible_tps: float,
    ) -> dict[str, Any]:
        spark_tps = 0.0
        for conv in self.conversations:
            if conv.model_name == model_name:
                spark_tps = conv.avg_tps
                break

        if spark_tps <= 0:
            return {"error": "No Spark baseline found"}

        speedup = crucible_tps / spark_tps
        return {
            "model_name": model_name,
            "spark_tps": round(spark_tps, 2),
            "crucible_tps": round(crucible_tps, 2),
            "speedup": round(speedup, 2),
            "recommendation": "crucible" if speedup > 1.0 else "spark",
        }
