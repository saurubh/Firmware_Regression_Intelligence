"""TTY progress so long BIOS investigations look alive."""

from __future__ import annotations

import sys
import time


class ProgressBar:
    def __init__(self, label: str, total: int) -> None:
        self.label = label
        self.total = max(total, 0)
        self.started = time.perf_counter()
        self._last = ""
        self._tty = sys.stderr.isatty()

    def update(self, current: int, detail: str = "") -> None:
        elapsed = max(time.perf_counter() - self.started, 0.001)
        total = self.total or 1
        current = min(max(current, 0), total)
        fraction = current / total if self.total else 1.0
        filled = int(28 * fraction)
        bar = "#" * filled + "-" * (28 - filled)
        rate = current / elapsed
        remaining = (self.total - current) / rate if rate and self.total else 0.0
        line = (
            f"FRI {self.label}  [{bar}] {current}/{self.total or current}  "
            f"{int(fraction * 100):3d}%  {elapsed:5.0f}s  eta {remaining:5.0f}s  {detail}"
        )
        if self._tty:
            pad = max(len(self._last) - len(line), 0)
            print("\r" + line + (" " * pad), end="", file=sys.stderr, flush=True)
            self._last = line
        elif current == 1 or current == self.total or current % 10 == 0:
            print(line, file=sys.stderr, flush=True)

    def close(self) -> None:
        if self._tty and self._last:
            print(file=sys.stderr, flush=True)
