"""HuggingFace model search — find and download models for Crucible compilation."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json


@dataclass
class HfModel:
    model_id: str
    name: str
    author: str
    downloads: int = 0
    likes: int = 0
    tags: list[str] = field(default_factory=list)
    pipeline_tag: str = ""
    library_name: str = ""
    model_size: str = ""
    quant_type: str = ""
    license: str = ""
    gguf_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "author": self.author,
            "downloads": self.downloads,
            "likes": self.likes,
            "tags": self.tags,
            "pipeline_tag": self.pipeline_tag,
            "library_name": self.library_name,
            "model_size": self.model_size,
            "quant_type": self.quant_type,
            "license": self.license,
            "gguf_url": self.gguf_url,
        }


class HuggingFaceSearch:
    """Search HuggingFace for models suitable for Crucible compilation."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "tpt-crucible" / "hf"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        cache_file = self.cache_dir / "search_cache.json"
        if cache_file.exists():
            try:
                self._cache = json.loads(cache_file.read_text())
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def _save_cache(self) -> None:
        cache_file = self.cache_dir / "search_cache.json"
        cache_file.write_text(json.dumps(self._cache, indent=2))

    def search(
        self,
        query: str,
        limit: int = 10,
        model_size: str | None = None,
        quant_type: str | None = None,
    ) -> list[HfModel]:
        cache_key = f"{query}:{limit}:{model_size}:{quant_type}"
        if cache_key in self._cache:
            return [HfModel(**m) for m in self._cache[cache_key]]

        try:
            from huggingface_hub import HfApi
            api = HfApi()
            results = api.list_models(
                search=query,
                limit=limit,
                sort="downloads",
                direction=-1,
            )

            models = []
            for r in results:
                tags = r.tags or []
                model = HfModel(
                    model_id=r.id,
                    name=r.id.split("/")[-1],
                    author=r.id.split("/")[0] if "/" in r.id else "",
                    downloads=r.downloads or 0,
                    likes=r.likes or 0,
                    tags=tags,
                    pipeline_tag=r.pipeline_tag or "",
                    library_name=r.library_name or "",
                    model_size=self._extract_size(tags),
                    quant_type=self._extract_quant(tags),
                    license=r.license or "",
                )
                models.append(model)

            self._cache[cache_key] = [m.to_dict() for m in models]
            self._save_cache()
            return models

        except ImportError:
            return self._fallback_search(query, limit)

    def _fallback_search(self, query: str, limit: int) -> list[HfModel]:
        known_models = [
            HfModel(model_id="TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF", name="TinyLlama-1.1B-Chat-v1.0-GGUF",
                    author="TheBloke", downloads=500000, quant_type="Q4_K_M", tags=["gguf", "llama"]),
            HfModel(model_id="TheBloke/Llama-2-7B-Chat-GGUF", name="Llama-2-7B-Chat-GGUF",
                    author="TheBloke", downloads=1000000, quant_type="Q4_K_M", tags=["gguf", "llama"]),
            HfModel(model_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF", name="Mistral-7B-Instruct-v0.2-GGUF",
                    author="TheBloke", downloads=800000, quant_type="Q4_K_M", tags=["gguf", "mistral"]),
            HfModel(model_id="bartowski/Qwen2.5-3B-Instruct-GGUF", name="Qwen2.5-3B-Instruct-GGUF",
                    author="bartowski", downloads=200000, quant_type="Q4_K_M", tags=["gguf", "qwen"]),
        ]
        q = query.lower()
        return [m for m in known_models if q in m.model_id.lower() or q in m.name.lower()][:limit]

    def _extract_size(self, tags: list[str]) -> str:
        for tag in tags:
            if any(s in tag for s in ["7b", "13b", "70b", "1b", "3b", "1.1b"]):
                return tag
        return ""

    def _extract_quant(self, tags: list[str]) -> str:
        for tag in tags:
            if "gguf" in tag:
                continue
            if any(q in tag.upper() for q in ["Q4_K", "Q5_K", "Q8_0", "Q2_K", "Q3_K", "Q6_K"]):
                return tag.upper()
        return ""

    def get_popular(self, limit: int = 5) -> list[HfModel]:
        return self.search("GGUF LLM", limit=limit)
