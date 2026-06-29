"""LLM Error Diagnosis — AI-powered error analysis and suggested fixes."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json


@dataclass
class DiagnosisRequest:
    error_type: str
    tool: str
    stderr: str
    model_info: dict[str, Any]
    target_board: str
    synthesis_flags: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "tool": self.tool,
            "stderr": self.stderr[:1000],
            "model_info": self.model_info,
            "target_board": self.target_board,
            "synthesis_flags": self.synthesis_flags,
        }

    def to_prompt(self) -> str:
        return (
            f"Analyze this synthesis error and suggest a fix:\n\n"
            f"Tool: {self.tool}\n"
            f"Error type: {self.error_type}\n"
            f"Target board: {self.target_board}\n"
            f"Model info: {json.dumps(self.model_info, indent=2)}\n"
            f"Error output:\n{self.stderr[:2000]}\n\n"
            f"Provide:\n1. Root cause analysis\n2. Suggested fix\n3. Alternative approach if fix fails"
        )


@dataclass
class DiagnosisResponse:
    root_cause: str
    suggested_fix: str
    alternative: str = ""
    confidence: float = 0.8
    actionable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "suggested_fix": self.suggested_fix,
            "alternative": self.alternative,
            "confidence": round(self.confidence, 2),
            "actionable": self.actionable,
        }


class LLMDiagnosisEngine:
    """AI-powered error diagnosis using LLM providers."""

    def __init__(self):
        self._provider = None
        self._diagnosis_cache: dict[str, DiagnosisResponse] = {}

    def configure_provider(self, provider_type: str, config: dict[str, Any]) -> None:
        self._provider = {"type": provider_type, **config}

    def is_configured(self) -> bool:
        return self._provider is not None

    def diagnose(self, request: DiagnosisRequest) -> DiagnosisResponse:
        cache_key = f"{request.tool}:{request.error_type}"
        if cache_key in self._diagnosis_cache:
            return self._diagnosis_cache[cache_key]

        if self.is_configured():
            response = self._call_llm(request)
        else:
            response = self._fallback_diagnosis(request)

        self._diagnosis_cache[cache_key] = response
        return response

    def _call_llm(self, request: DiagnosisRequest) -> DiagnosisResponse:
        prompt = request.to_prompt()
        try:
            if self._provider["type"] == "openrouter":
                return self._call_openrouter(prompt)
            elif self._provider["type"] == "ollama":
                return self._call_ollama(prompt)
        except Exception:
            pass
        return self._fallback_diagnosis(request)

    def _call_openrouter(self, prompt: str) -> DiagnosisResponse:
        import urllib.request
        data = json.dumps({
            "model": self._provider.get("model", "meta-llama/llama-3-8b"),
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            self._provider.get("endpoint", "https://openrouter.ai/api/v1/chat/completions"),
            data=data,
            headers={"Authorization": f"Bearer {self._provider.get('api_key', '')}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            return self._parse_response(content)

    def _call_ollama(self, prompt: str) -> DiagnosisResponse:
        import urllib.request
        data = json.dumps({
            "model": self._provider.get("model", "llama3"),
            "prompt": prompt,
        }).encode()
        req = urllib.request.Request(
            self._provider.get("endpoint", "http://localhost:11434/api/generate"),
            data=data,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return self._parse_response(result.get("response", ""))

    def _parse_response(self, content: str) -> DiagnosisResponse:
        try:
            data = json.loads(content)
            return DiagnosisResponse(
                root_cause=data.get("root_cause", "Unknown"),
                suggested_fix=data.get("suggested_fix", ""),
                alternative=data.get("alternative", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return DiagnosisResponse(
                root_cause=content[:200],
                suggested_fix="Review the error output manually",
            )

    def _fallback_diagnosis(self, request: DiagnosisRequest) -> DiagnosisResponse:
        error_hints = {
            "timing_failure": ("Timing closure failed", "Reduce clock frequency or add pipeline stages"),
            "resource_overflow": ("FPGA resources exceeded", "Use smaller MAC array or larger FPGA"),
            "missing_module": ("Required Verilog module not found", "Check source file paths"),
            "board_not_found": ("PlatformIO board not recognized", "Verify board name in platformio.ini"),
        }
        hint = error_hints.get(request.error_type, ("Unknown error", "Check raw output for details"))
        return DiagnosisResponse(root_cause=hint[0], suggested_fix=hint[1], confidence=0.5)
