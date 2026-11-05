"""
PS5 Monitoring Service - Live State Tests.

Verify console power, monitored player activity, observation
freshness, disconnection handling, and recovery.

Tests use a simulated monotonic clock and do not access
production SQLite storage or an MQTT broker.
"""

import unittest

from datetime import datetime, timezone

from models import ActivityType, ConsolePower, PS5State
from ps5_live_state import PS5LiveState


PLAYER_NAME = "PlayerOne"


class FakeClock:
    """Provide deterministic monotonic time for testing."""

    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        """Return the current simulated monotonic time."""

        return self.value

    def advance(self, seconds):
        """Advance simulated time without sleeping."""

        self.value += seconds


def make_state(
    power=ConsolePower.AWAKE,
    device_status="online",
    activity=ActivityType.PLAYING,
    players=(PLAYER_NAME,),
):
    """Create a validated simulated PS5 observation."""

    return PS5State(
        power=power,
        device_status=device_status,
        activity=activity,
        players=players,
        title_id="PPSA17221_00",
        title_name="Minecraft",
        title_image="https://example.com/minecraft.png",
        observed_at=datetime(
            2026, 11, 4, 12, 0,
            tzinfo=timezone.utc,
        ),
    )


class PS5LiveStateTests(unittest.TestCase):
    """Test live console state and observation freshness."""

    def setUp(self):
        """Initialize an isolated live-state tracker."""

        self.clock = FakeClock()

        self.tracker = PS5LiveState(
            player_name=PLAYER_NAME,
            timeout_seconds=30.0,
            monotonic_clock=self.clock,
        )

    def test_initial_state_unknown(self):
        """No observation must produce an unavailable state."""

        snapshot = self.tracker.snapshot()

        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.power, "UNKNOWN")
        self.assertFalse(snapshot.player_gaming)

    def test_console_awake_and_player_playing(self):
        """Confirm active gaming only for the monitored player."""

        self.tracker.observe(make_state())

        snapshot = self.tracker.snapshot()

        self.assertTrue(snapshot.available)
        self.assertEqual(snapshot.power, "AWAKE")
        self.assertTrue(snapshot.console_active)
        self.assertTrue(snapshot.player_gaming)
        self.assertEqual(snapshot.title_name, "Minecraft")

    def test_console_awake_but_idle(self):
        """An awake console does not imply active gaming."""

        self.tracker.observe(
            make_state(activity=ActivityType.IDLE)
        )

        snapshot = self.tracker.snapshot()

        self.assertTrue(snapshot.console_active)
        self.assertFalse(snapshot.player_gaming)

    def test_other_player_not_attributed_to_player(self):
        """Another player must not count as Player gaming."""

        self.tracker.observe(
            make_state(players=("AnotherPlayer",))
        )

        snapshot = self.tracker.snapshot()

        self.assertTrue(snapshot.console_active)
        self.assertFalse(snapshot.player_gaming)

    def test_standby_and_off(self):
        """Standby and off must not be reported as active."""

        for power in (
            ConsolePower.STANDBY,
            ConsolePower.OFF,
        ):
            with self.subTest(power=power):
                self.tracker.observe(
                    make_state(power=power)
                )

                snapshot = self.tracker.snapshot()

                self.assertEqual(snapshot.power, power.value)
                self.assertFalse(snapshot.console_active)
                self.assertFalse(snapshot.player_gaming)

    def test_observation_expires_at_timeout(self):
        """Observations expire at exactly thirty seconds."""

        self.tracker.observe(make_state())

        self.clock.advance(29.9)

        self.assertTrue(self.tracker.snapshot().available)

        self.clock.advance(0.1)

        snapshot = self.tracker.snapshot()

        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.power, "UNKNOWN")
        self.assertFalse(snapshot.player_gaming)

    def test_recovery_after_timeout(self):
        """A fresh observation restores live availability."""

        self.tracker.observe(make_state())

        self.clock.advance(31)

        self.assertFalse(self.tracker.snapshot().available)

        self.tracker.observe(make_state())

        snapshot = self.tracker.snapshot()

        self.assertTrue(snapshot.available)
        self.assertTrue(snapshot.player_gaming)

    def test_immediate_invalidation(self):
        """Connection loss invalidates the observation immediately."""

        self.tracker.observe(make_state())

        self.tracker.invalidate()

        snapshot = self.tracker.snapshot()

        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.power, "UNKNOWN")
        self.assertFalse(snapshot.player_gaming)

    def test_generation_increments(self):
        """Every observation or invalidation advances generation."""

        self.assertEqual(self.tracker.snapshot().generation, 0)

        self.tracker.observe(make_state())

        self.assertEqual(self.tracker.snapshot().generation, 1)

        self.tracker.invalidate()

        self.assertEqual(self.tracker.snapshot().generation, 2)

        self.tracker.observe(make_state())

        self.assertEqual(self.tracker.snapshot().generation, 3)

    def test_invalid_observation_rejected(self):
        """Only validated PS5State objects may be accepted."""

        with self.assertRaises(TypeError):
            self.tracker.observe({"power": "AWAKE"})


if __name__ == "__main__":
    unittest.main(verbosity=2)


class PS5LiveStateFreezeTests(unittest.TestCase):
    """Verify irreversible shutdown freezing."""

    def setUp(self):
        """Create an isolated live-state tracker."""

        self.clock = FakeClock()

        self.tracker = PS5LiveState(
            player_name=PLAYER_NAME,
            timeout_seconds=30.0,
            monotonic_clock=self.clock,
        )

    def test_freeze_invalidates_confirmed_state(self):
        """Freezing must invalidate an active observation."""

        self.tracker.observe(make_state())

        self.assertTrue(self.tracker.snapshot().available)

        self.tracker.freeze()

        snapshot = self.tracker.snapshot()

        self.assertTrue(self.tracker.frozen)
        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.power, "UNKNOWN")
        self.assertFalse(snapshot.player_gaming)

    def test_freeze_rejects_new_observations(self):
        """New observations must be rejected after freezing."""

        self.tracker.freeze()

        with self.assertRaises(RuntimeError):
            self.tracker.observe(make_state())

        self.assertFalse(self.tracker.snapshot().available)

    def test_repeated_freeze_is_idempotent(self):
        """Repeated freezing must not increment generation."""

        self.tracker.freeze()

        generation = self.tracker.snapshot().generation

        self.tracker.freeze()

        self.assertEqual(
            self.tracker.snapshot().generation,
            generation,
        )

    def test_invalidation_cannot_reactivate_frozen_state(self):
        """Invalidation must not restore availability."""

        self.tracker.observe(make_state())
        self.tracker.freeze()
        self.tracker.invalidate()

        snapshot = self.tracker.snapshot()

        self.assertTrue(self.tracker.frozen)
        self.assertFalse(snapshot.available)
        self.assertEqual(snapshot.power, "UNKNOWN")
