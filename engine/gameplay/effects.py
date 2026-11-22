"""Living-entity status effects and their 1.12.2 tick behavior."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable


class EffectType(IntEnum):
    SPEED = 1
    SLOWNESS = 2
    HASTE = 3
    MINING_FATIGUE = 4
    STRENGTH = 5
    INSTANT_HEALTH = 6
    INSTANT_DAMAGE = 7
    JUMP_BOOST = 8
    NAUSEA = 9
    REGENERATION = 10
    RESISTANCE = 11
    FIRE_RESISTANCE = 12
    WATER_BREATHING = 13
    INVISIBILITY = 14
    BLINDNESS = 15
    NIGHT_VISION = 16
    HUNGER = 17
    WEAKNESS = 18
    POISON = 19
    WITHER = 20
    HEALTH_BOOST = 21
    ABSORPTION = 22
    SATURATION = 23
    GLOWING = 24
    LEVITATION = 25
    LUCK = 26
    UNLUCK = 27


@dataclass(frozen=True)
class StatusEffect:
    effect: EffectType
    duration: int
    amplifier: int = 0
    ambient: bool = False
    show_particles: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.effect, EffectType):
            raise TypeError("effect must be an EffectType")
        if isinstance(self.duration, bool) or not isinstance(self.duration, int) or self.duration <= 0:
            raise ValueError("duration must be a positive integer")
        if isinstance(self.amplifier, bool) or not isinstance(self.amplifier, int) or not 0 <= self.amplifier <= 255:
            raise ValueError("amplifier must be from 0 to 255")
        if not isinstance(self.ambient, bool) or not isinstance(self.show_particles, bool):
            raise TypeError("ambient and show_particles must be bools")


class StatusEffectManager:
    """Maintains active effects, merging stronger/longer applications."""

    def __init__(self) -> None:
        self._active: dict[EffectType, StatusEffect] = {}

    def add(self, effect: StatusEffect) -> StatusEffect:
        if not isinstance(effect, StatusEffect):
            raise TypeError("effect must be a StatusEffect")
        current = self._active.get(effect.effect)
        if current is None or effect.amplifier > current.amplifier or (
            effect.amplifier == current.amplifier and effect.duration > current.duration
        ):
            self._active[effect.effect] = effect
        elif effect.amplifier == current.amplifier and effect.duration == current.duration:
            self._active[effect.effect] = StatusEffect(
                effect.effect, effect.duration, effect.amplifier,
                current.ambient and effect.ambient,
                current.show_particles or effect.show_particles,
            )
        return self._active[effect.effect]

    def remove(self, effect: EffectType) -> bool:
        return self._active.pop(effect, None) is not None

    def get(self, effect: EffectType) -> StatusEffect | None:
        return self._active.get(effect)

    def active(self) -> tuple[StatusEffect, ...]:
        return tuple(self._active.values())

    def tick(self, entity) -> None:
        """Tick durations and the periodic effects with vanilla intervals."""
        for kind, current in tuple(self._active.items()):
            duration = current.duration
            amplifier = current.amplifier
            if kind == EffectType.REGENERATION:
                interval = max(1, 50 >> amplifier)
                if duration % interval == 0 and entity.health < entity.max_health:
                    entity.heal(1.0)
            elif kind == EffectType.POISON:
                interval = max(1, 25 >> amplifier)
                if duration % interval == 0 and entity.health > 1.0:
                    entity.damage(1.0)
            elif kind == EffectType.WITHER:
                interval = max(1, 40 >> amplifier)
                if duration % interval == 0:
                    entity.damage(1.0)
            elif kind == EffectType.INSTANT_HEALTH:
                entity.heal(float(4 << amplifier))
                self.remove(kind)
                continue
            elif kind == EffectType.INSTANT_DAMAGE:
                entity.damage(float(6 << amplifier))
                self.remove(kind)
                continue

            if duration <= 1:
                self.remove(kind)
            else:
                self._active[kind] = StatusEffect(
                    kind, duration - 1, amplifier,
                    current.ambient, current.show_particles,
                )


__all__ = ["EffectType", "StatusEffect", "StatusEffectManager"]
