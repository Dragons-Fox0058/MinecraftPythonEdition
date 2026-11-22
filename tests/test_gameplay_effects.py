"""Tests for status effect registration and living-entity ticking."""
import unittest

from engine.gameplay.effects import EffectType, StatusEffect, StatusEffectManager
from engine.entities.living import EntityLivingBase
from engine.world import World


class TestStatusEffects(unittest.TestCase):
    def setUp(self):
        self.entity = EntityLivingBase(World())

    def test_effect_duration_ticks_and_expires(self):
        effect = StatusEffect(EffectType.SPEED, 3, amplifier=1)
        self.entity.status_effects.add(effect)
        self.entity.on_update()
        self.assertEqual(self.entity.status_effects.get(EffectType.SPEED).duration, 2)
        self.entity.on_update()
        self.entity.on_update()
        self.assertIsNone(self.entity.status_effects.get(EffectType.SPEED))

    def test_stronger_effect_replaces_weaker_and_shorter_effect_does_not(self):
        manager = StatusEffectManager()
        manager.add(StatusEffect(EffectType.STRENGTH, 100, 0))
        manager.add(StatusEffect(EffectType.STRENGTH, 20, 1))
        self.assertEqual(manager.get(EffectType.STRENGTH).amplifier, 1)
        manager.add(StatusEffect(EffectType.STRENGTH, 10, 0))
        self.assertEqual(manager.get(EffectType.STRENGTH).duration, 20)

    def test_regeneration_heals_on_vanilla_interval(self):
        self.entity.health = 10.0
        self.entity.status_effects.add(StatusEffect(EffectType.REGENERATION, 50))
        for _ in range(50):
            self.entity.on_update()
        self.assertEqual(self.entity.health, 11.0)

    def test_poison_does_not_reduce_health_below_one(self):
        self.entity.health = 3.0
        self.entity.status_effects.add(StatusEffect(EffectType.POISON, 50))
        for _ in range(50):
            self.entity.on_update()
        self.assertEqual(self.entity.health, 1.0)

    def test_wither_damage_and_instant_effects(self):
        self.entity.health = 10.0
        self.entity.status_effects.add(StatusEffect(EffectType.INSTANT_DAMAGE, 1))
        self.entity.on_update()
        self.assertEqual(self.entity.health, 4.0)
        self.assertIsNone(self.entity.status_effects.get(EffectType.INSTANT_DAMAGE))
        self.entity.status_effects.add(StatusEffect(EffectType.INSTANT_HEALTH, 1))
        self.entity.on_update()
        self.assertEqual(self.entity.health, 8.0)

    def test_invalid_effect_data_is_rejected(self):
        with self.assertRaises(ValueError):
            StatusEffect(EffectType.POISON, 0)
        with self.assertRaises(ValueError):
            StatusEffect(EffectType.POISON, 10, amplifier=256)


if __name__ == "__main__":
    unittest.main()
