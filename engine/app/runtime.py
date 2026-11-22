"""Small deterministic application loop primitives (no window toolkit required)."""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Callable


@dataclass(frozen=True)
class GameConfig:
    title: str = "Minecraft Python Edition"
    target_fps: int = 60
    tick_rate: int = 20
    max_frame_time: float = 0.25
    max_catch_up_ticks: int = 5

    def __post_init__(self):
        if not self.title:
            raise ValueError("title must not be empty")
        if isinstance(self.target_fps, bool) or self.target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if isinstance(self.tick_rate, bool) or self.tick_rate <= 0:
            raise ValueError("tick_rate must be positive")
        if not math.isfinite(self.max_frame_time) or self.max_frame_time <= 0:
            raise ValueError("max_frame_time must be finite and positive")
        if isinstance(self.max_catch_up_ticks, bool) or self.max_catch_up_ticks <= 0:
            raise ValueError("max_catch_up_ticks must be positive")


class FixedTimestepLoop:
    """Fixed-rate simulation with bounded catch-up and render interpolation."""

    def __init__(self, tick_rate: int = 20, max_frame_time: float = 0.25,
                 max_catch_up_ticks: int = 5):
        if tick_rate <= 0 or max_frame_time <= 0 or max_catch_up_ticks <= 0:
            raise ValueError("loop limits must be positive")
        self.step = 1.0 / tick_rate
        self.max_frame_time = float(max_frame_time)
        self.max_catch_up_ticks = int(max_catch_up_ticks)
        self.accumulator = 0.0
        self.total_ticks = 0
        self.dropped_time = 0.0

    def advance(self, elapsed: float, tick: Callable[[float], None]) -> tuple[int, float]:
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("elapsed must be finite and non-negative")
        if not callable(tick):
            raise TypeError("tick must be callable")
        accepted = min(elapsed, self.max_frame_time)
        self.dropped_time += elapsed - accepted
        self.accumulator += accepted
        count = 0
        while self.accumulator >= self.step and count < self.max_catch_up_ticks:
            tick(self.step)
            self.accumulator -= self.step
            count += 1
            self.total_ticks += 1
        if self.accumulator >= self.step:
            retained = self.accumulator % self.step
            self.dropped_time += self.accumulator - retained
            self.accumulator = retained
        return count, self.accumulator / self.step


class GameApplication:
    """Toolkit-neutral application shell; window/input/render backends are injected."""

    def __init__(self, config: GameConfig, update: Callable[[float], None],
                 render: Callable[[float], None], poll_events: Callable[[], bool] | None = None,
                 network_session=None):
        if not callable(update) or not callable(render):
            raise TypeError("update and render callbacks are required")
        self.config = config
        self.update = update
        self.render = render
        self.poll_events = poll_events or (lambda: True)
        if network_session is not None and not all(
            callable(getattr(network_session, name, None))
            for name in ("start_receiver", "poll_received", "tick", "close")
        ):
            raise TypeError("network_session must provide start_receiver, poll_received, tick, and close")
        self.network_session = network_session
        self.loop = FixedTimestepLoop(config.tick_rate, config.max_frame_time,
                                      config.max_catch_up_ticks)
        self.running = False

    def stop(self) -> None:
        self.running = False

    def run(self, *, max_frames: int | None = None,
            clock: Callable[[], float] = time.perf_counter,
            sleep: Callable[[float], None] = time.sleep) -> None:
        if max_frames is not None and max_frames < 0:
            raise ValueError("max_frames must be non-negative")
        self.running = True
        previous = clock()
        frames = 0
        frame_budget = 1.0 / self.config.target_fps
        try:
            if self.network_session is not None:
                self.network_session.start_receiver()

            def fixed_update(dt: float) -> None:
                if self.network_session is not None:
                    self.network_session.poll_received()
                self.update(dt)
                if self.network_session is not None:
                    self.network_session.tick()

            while self.running and (max_frames is None or frames < max_frames):
                frame_start = clock()
                if not self.poll_events():
                    break
                elapsed = max(0.0, frame_start - previous)
                previous = frame_start
                _, alpha = self.loop.advance(elapsed, fixed_update)
                self.render(alpha)
                frames += 1
                remaining = frame_budget - (clock() - frame_start)
                if remaining > 0:
                    sleep(remaining)
        finally:
            self.running = False
            if self.network_session is not None:
                self.network_session.close()


__all__ = ["GameConfig", "FixedTimestepLoop", "GameApplication"]
