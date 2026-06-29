"""AI-Generated Validation Prompt Suite — domain-specific test prompts."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class PromptSuite:
    model_id: str
    domain: str
    prompts: list[str]
    generated_by: str = "builtin"
    cached_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "domain": self.domain,
            "prompts": self.prompts,
            "generated_by": self.generated_by,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> PromptSuite:
        data = json.loads(path.read_text())
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


BUILTIN_PROMPTS = [
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
    "What is the difference between TCP and UDP?",
    "How does a CPU work?",
    "What is Docker?",
    "Explain REST API in simple terms.",
    "What is the time complexity of quicksort?",
]


DOMAIN_PROMPTS: dict[str, list[str]] = {
    "code": [
        "Write a Python function to find the longest substring without repeating characters.",
        "Explain the difference between TCP and UDP.",
        "What is the CAP theorem in distributed systems?",
        "How does garbage collection work in Java?",
        "Explain the Observer design pattern.",
    ],
    "math": [
        "What is the derivative of x^3 + 2x?",
        "Explain the pigeonhole principle.",
        "What is a prime number? List the first 10.",
        "Solve: 3x + 7 = 22",
        "What is the area of a circle with radius 5?",
    ],
    "science": [
        "What is DNA?",
        "Explain how photosynthesis works.",
        "What are the laws of thermodynamics?",
        "How does electricity work?",
        "What is evolution?",
    ],
    "creative": [
        "Write a short poem about the ocean.",
        "Create a character profile for a space explorer.",
        "Write a opening paragraph for a mystery novel.",
        "Describe a futuristic city in 100 words.",
        "Write a dialogue between two robots.",
    ],
}


class PromptSuiteGenerator:
    """Generate validation prompt suites for accuracy testing."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".tpt-crucible" / "prompt-suites"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_suite(self, model_id: str, domain: str = "general") -> PromptSuite:
        cache_path = self.cache_dir / f"{model_id.replace('/', '_')}_{domain}.json"
        if cache_path.exists():
            return PromptSuite.load(cache_path)

        prompts = list(BUILTIN_PROMPTS)
        if domain in DOMAIN_PROMPTS:
            prompts.extend(DOMAIN_PROMPTS[domain])

        suite = PromptSuite(
            model_id=model_id,
            domain=domain,
            prompts=prompts,
            generated_by="builtin",
        )
        suite.save(cache_path)
        return suite

    def generate_llm_prompts(self, model_id: str, domain: str) -> str:
        return (
            f"Given a model trained for {domain}, generate 50 diverse test prompts "
            f"that stress-test domain-specific vocabulary and edge cases. "
            f"Return JSON array of strings."
        )

    def combine_suites(self, *suites: PromptSuite) -> list[str]:
        seen = set()
        combined = []
        for suite in suites:
            for prompt in suite.prompts:
                if prompt not in seen:
                    seen.add(prompt)
                    combined.append(prompt)
        return combined
