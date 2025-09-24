from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict

import yaml

from agents.polymarket.polymarket import Polymarket
from agents.polymarket.gamma import GammaMarketClient


class BaseBot:
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._setup_logging()
        self._setup_state_dir()

        # Shared clients (reuse existing implementations)
        self.polymarket = Polymarket()
        self.gamma = GammaMarketClient()

        # Control flags
        self._running = False
        self._thread: threading.Thread | None = None

    def _load_config(self) -> None:
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f) or {}
        # Minimal schema checks and defaults
        ops = self.config.get("ops", {})
        if not isinstance(ops, dict):
            raise ValueError("config.ops must be a mapping")
        ops.setdefault("dry_run", True)
        ops.setdefault("state_dir", "local_state/basebot")
        ops.setdefault("log_path", "logs/basebot.log")
        ops.setdefault("tick_seconds", 60)
        self.config["ops"] = ops

    def _setup_logging(self) -> None:
        log_path = self.config["ops"].get("log_path")
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._log_path = log_path

    def _log(self, message: str, payload: Dict[str, Any] | None = None) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line: Dict[str, Any] = {"ts": ts, "msg": message}
        if payload:
            line.update(payload)
        print(json.dumps(line))
        try:
            if self._log_path:
                with open(self._log_path, "a") as f:
                    f.write(json.dumps(line) + "\n")
        except Exception:
            # Logging failures should not crash the bot
            pass

    def _setup_state_dir(self) -> None:
        state_dir = self.config["ops"].get("state_dir", "local_state/basebot")
        os.makedirs(state_dir, exist_ok=True)
        self._state_dir = state_dir

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._log("bot_started", {"config": self.config_path})

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._log("bot_stopped")

    def _run_loop(self) -> None:
        tick_seconds = int(self.config["ops"].get("tick_seconds", 60))
        while self._running:
            try:
                self._tick()
            except Exception as err:
                self._log("tick_error", {"error": str(err)})
            time.sleep(tick_seconds)

    def _tick(self) -> None:
        # Placeholder for subclasses
        self._log("tick_noop")
