"""Model Accuracy Validator — compare hardware outputs against reference."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class PromptResult:
    prompt: str
    reference_output: str
    hardware_output: str
    similarity: float
    token_match: bool = False


@dataclass
class ValidationResult:
    overall_similarity: float
    perplexity_delta: float
    prompts_tested: int
    results: list[PromptResult]
    per_layer_scores: dict[str, float] = field(default_factory=dict)

    @property
    def grade(self) -> str:
        if self.overall_similarity >= 0.95:
            return "A"
        elif self.overall_similarity >= 0.90:
            return "B"
        elif self.overall_similarity >= 0.80:
            return "C"
        elif self.overall_similarity >= 0.70:
            return "D"
        return "F"

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_similarity": round(self.overall_similarity, 4),
            "perplexity_delta": round(self.perplexity_delta, 4),
            "prompts_tested": self.prompts_tested,
            "grade": self.grade,
            "per_layer_scores": self.per_layer_scores,
        }


STANDARD_PROMPTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms.",
    "Write a haiku about machines.",
    "What is 137 * 42?",
    "Summarize the theory of relativity.",
    "Translate 'hello world' to Spanish.",
    "What are the primary colors?",
    "Explain what a neural network is.",
    "Write a short story about a robot.",
    "What is the square root of 144?",
    "Describe the process of photosynthesis.",
    "What is machine learning?",
    "Write code to reverse a string in Python.",
    "What are the planets in our solar system?",
    "Explain the concept of recursion.",
]


class AccuracyValidator:
    """Validate hardware inference accuracy against a reference backend."""

    def __init__(self):
        self.prompts = list(STANDARD_PROMPTS)

    def set_prompts(self, prompts: list[str]) -> None:
        self.prompts = prompts

    def validate(
        self,
        reference_outputs: list[str],
        hardware_outputs: list[str],
    ) -> ValidationResult:
        if len(reference_outputs) != len(hardware_outputs):
            raise ValueError("Reference and hardware output counts must match")

        results = []
        total_similarity = 0.0

        for ref, hw in zip(reference_outputs, hardware_outputs):
            similarity = self._compute_similarity(ref, hw)
            results.append(PromptResult(
                prompt="",
                reference_output=ref,
                hardware_output=hw,
                similarity=similarity,
                token_match=ref == hw,
            ))
            total_similarity += similarity

        overall = total_similarity / len(results) if results else 0.0
        perplexity_delta = self._estimate_perplexity_delta(reference_outputs, hardware_outputs)

        return ValidationResult(
            overall_similarity=overall,
            perplexity_delta=perplexity_delta,
            prompts_tested=len(results),
            results=results,
        )

    def _compute_similarity(self, ref: str, hw: str) -> float:
        if not ref or not hw:
            return 0.0
        ref_tokens = set(ref.lower().split())
        hw_tokens = set(hw.lower().split())
        if not ref_tokens:
            return 0.0
        intersection = ref_tokens & hw_tokens
        return len(intersection) / len(ref_tokens)

    def _estimate_perplexity_delta(self, refs: list[str], hws: list[str]) -> float:
        total_diff = 0.0
        for ref, hw in zip(refs, hws):
            ref_len = len(ref.split())
            hw_len = len(hw.split())
            if ref_len > 0:
                total_diff += abs(ref_len - hw_len) / ref_len
        return total_diff / len(refs) if refs else 0.0
