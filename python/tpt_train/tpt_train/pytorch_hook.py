"""PyTorch training hook — TPTProbeCallback for PyTorch models."""

from __future__ import annotations
from typing import Any
from pathlib import Path

from .profile import TptProfileWriter, TptProfile


class TPTProbeCallback:
    """PyTorch training callback that records per-layer statistics.

    Usage:
        callback = TPTProbeCallback("my_model")
        callback.attach(model)
        for epoch in range(num_epochs):
            train(...)
            callback.step(epoch)
        callback.save(Path("model.tptprofile"))
    """

    def __init__(self, model_name: str):
        self.writer = TptProfileWriter(model_name)
        self.hooks: list[Any] = []
        self._attached = False
        self._model = None

    def attach(self, model: Any) -> None:
        """Attach hooks to all layers of a PyTorch model."""
        self._model = model
        for name, module in model.named_modules():
            if len(list(module.children())) == 0:
                hook = module.register_forward_hook(self._make_hook(name, type(module).__name__))
                self.hooks.append(hook)
        self._attached = True

    def _make_hook(self, name: str, layer_type: str):
        def hook_fn(module, input, output):
            input_tensor = input[0] if input and len(input) > 0 else None
            weight_tensor = None
            if hasattr(module, 'weight'):
                weight_tensor = module.weight.detach().cpu().numpy()

            self.writer.record_layer(
                name=name,
                layer_type=layer_type,
                input_tensor=input_tensor.detach().cpu().numpy() if input_tensor is not None else None,
                weight_tensor=weight_tensor,
            )
        return hook_fn

    def step(self, epoch: int) -> None:
        """Record the current epoch number."""
        self.writer.profile.epoch = epoch

    def detach(self) -> None:
        """Remove all hooks."""
        for h in self.hooks:
            h.remove()
        self.hooks.clear()
        self._attached = False

    def save(self, path: Path) -> None:
        """Save the profile to a file."""
        self.writer.save(path)

    def get_profile(self) -> TptProfile:
        return self.writer.get_profile()
