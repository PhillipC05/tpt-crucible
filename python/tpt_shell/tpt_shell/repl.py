"""Hardware REPL — interactive prompt_toolkit-based shell for TPT deployments."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .session import ShellSession


HELP_TEXT = """
TPT Shell — Hardware REPL

Commands:
  run_layer <id> [input_json]   Execute a single layer and show output tensor
  inspect <tensor_id>           Show last output tensor for a layer
  telemetry                     Snapshot current hardware telemetry
  diff <id> <input_a> <input_b> Compare layer output for two inputs
  layers                        List all layer IDs in the loaded package
  help                          Show this help
  exit / quit                   Exit the shell
"""


def _fmt_diff(d: dict[str, Any]) -> str:
    if "error" in d:
        return f"Error: {d['error']}"
    return (
        f"Layer diff:\n"
        f"  max_abs_diff  = {d['max_abs_diff']:.6f}\n"
        f"  mean_abs_diff = {d['mean_abs_diff']:.6f}\n"
        f"  l2_norm       = {d['l2_norm']:.6f}"
    )


async def run_repl(session: ShellSession) -> None:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.styles import Style

        style = Style.from_dict({"prompt": "ansigreen bold"})
        completer = WordCompleter(
            ["run_layer", "inspect", "telemetry", "diff", "layers", "help", "exit", "quit"]
            + session.layer_ids,
            ignore_case=True,
        )
        prompt_session: Any = PromptSession(completer=completer, style=style)
    except ImportError:
        prompt_session = None

    print("TPT Shell connected. Type 'help' for commands.\n")

    while True:
        try:
            if prompt_session:
                line: str = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: prompt_session.prompt("tpt> ")
                )
            else:
                line = input("tpt> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        parts = line.strip().split(None, 3)
        if not parts:
            continue
        cmd, *args = parts

        if cmd in ("exit", "quit"):
            print("Goodbye.")
            break

        elif cmd == "help":
            print(HELP_TEXT)

        elif cmd == "layers":
            ids = session.layer_ids
            if ids:
                for lid in ids:
                    print(f"  {lid}")
            else:
                print("  (no layers — is the .tptpkg loaded correctly?)")

        elif cmd == "telemetry":
            try:
                snap = await session.telemetry_snapshot()
                print(snap.pretty())
            except Exception as e:
                print(f"Error: {e}")

        elif cmd == "run_layer":
            if not args:
                print("Usage: run_layer <layer_id> [input_json]")
                continue
            layer_id = args[0]
            input_json = args[1] if len(args) > 1 else None
            try:
                tensor = await session.run_layer(layer_id, input_json)
                print(tensor.pretty())
            except Exception as e:
                print(f"Error: {e}")

        elif cmd == "inspect":
            if not args:
                print("Usage: inspect <tensor_id>")
                continue
            try:
                tensor = await session.inspect(args[0])
                print(tensor.pretty())
            except Exception as e:
                print(f"Error: {e}")

        elif cmd == "diff":
            if len(args) < 3:
                print("Usage: diff <layer_id> <input_a_json> <input_b_json>")
                continue
            try:
                result = await session.diff(args[0], args[1], args[2])
                print(_fmt_diff(result))
            except Exception as e:
                print(f"Error: {e}")

        else:
            print(f"Unknown command: {cmd!r}. Type 'help' for a list of commands.")
