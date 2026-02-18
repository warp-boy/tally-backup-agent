from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

import psutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .logging_config import setup_logging

logger = setup_logging()


class DebounceHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[], None], debounce_seconds: int = 120):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._timer: Optional[threading.Timer] = None

    def _reset_timer(self):
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
        self._timer = threading.Timer(self.debounce_seconds, self.callback)
        self._timer.daemon = True
        self._timer.start()

    def on_any_event(self, event):
        logger.debug("Filesystem event: %s", event)
        self._reset_timer()


class Watcher:
    def __init__(self, data_path: Path, backup_callback: Callable[[Path], None], debounce_seconds: int = 120):
        self.data_path = data_path
        self.backup_callback = backup_callback
        self.debounce_seconds = debounce_seconds
        self.observer = Observer()
        self._stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self):
        handler = DebounceHandler(lambda: self._on_debounced(), debounce_seconds=self.debounce_seconds)
        self.observer.schedule(handler, str(self.data_path), recursive=True)
        self.observer.start()
        logger.info("Started filesystem watcher on %s", self.data_path)

        # Start process monitor thread
        self._monitor_thread = threading.Thread(target=self._process_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _on_debounced(self):
        logger.info("Debounce period elapsed; triggering backup scan")
        # Walk companies and call backup_callback on each
        for d in self.data_path.iterdir():
            if d.is_dir():
                self.backup_callback(d)

    def _process_monitor_loop(self):
        # If Tally process stops, trigger immediate backup
        while not self._stop.is_set():
            found = False
            for p in psutil.process_iter(attrs=["name"]):
                try:
                    name = p.info.get("name", "")
                    if name and name.lower().startswith("tally"):
                        found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if not found:
                logger.info("Tally process not found; triggering immediate backup")
                self._on_debounced()
                # wait a bit to avoid tight loop
                time.sleep(10)
            time.sleep(5)

    def stop(self):
        self._stop.set()
        self.observer.stop()
        self.observer.join()
        logger.info("Watcher stopped")
