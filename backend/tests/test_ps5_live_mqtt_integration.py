"""
PS5 Monitoring Service - Live MQTT Integration Tests.

Validate live-state dependency injection, observation handling,
connection transitions, and persistence failure recovery.

All tests are isolated from production SQLite and MQTT.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from models import ActivityType, ConsolePower, PS5State
from mqtt_client import PS5MQTTClient
from ps5_live_state import PS5LiveState
from ps5_live_publisher import PS5LivePublisher


PLAYER_NAME = "PlayerOne"


def make_state():
    """Create a valid simulated console observation."""

    return PS5State(
        power=ConsolePower.AWAKE,
        device_status="online",
        activity=ActivityType.PLAYING,
        players=(PLAYER_NAME,),
        title_id="PPSA17221_00",
        title_name="Minecraft",
        title_image="https://example.com/minecraft.png",
        observed_at=datetime.now(timezone.utc),
    )


class PS5LiveMQTTIntegrationTests(unittest.TestCase):
    """Verify live monitoring integration without network access."""

    def setUp(self):
        """Initialize isolated client and monitoring dependencies."""

        self.config = Mock()
        self.config.mqtt_topic = "ps5-mqtt/test"

        self.tracker = Mock()
        self.tracker.process_state.return_value = True

        self.client = PS5MQTTClient(
            config=self.config,
            tracker=self.tracker,
            timeout_seconds=30.0,
        )

        self.live_state = PS5LiveState(
            player_name=PLAYER_NAME,
        )

        self.publisher = PS5LivePublisher(
            publisher=self.client,
            live_state=self.live_state,
            transport_available=lambda: self.client.connected,
        )

        self.client.set_live_monitoring(
            self.live_state,
            self.publisher,
        )

        # The publisher worker is deliberately not started.
        # Notification methods are observed without network I/O.
        self.notify_patch = patch.object(
            self.publisher,
            "notify",
        )

        self.republish_patch = patch.object(
            self.publisher,
            "request_republish",
        )

        self.notify = self.notify_patch.start()
        self.republish = self.republish_patch.start()

    def tearDown(self):
        """Restore mocked publisher methods."""

        self.notify_patch.stop()
        self.republish_patch.stop()

    def test_accepted_observation_updates_live_state(self):
        """Accepted observations must update live monitoring."""

        state = make_state()

        with patch(
            "mqtt_client.parse_ps5_payload",
            return_value=state,
        ):
            accepted = self.client.handle_message(
                payload=b"test",
            )

        self.assertTrue(accepted)
        self.assertTrue(self.live_state.snapshot().available)
        self.assertTrue(self.live_state.snapshot().player_gaming)
        self.notify.assert_called_once()

    def test_rejected_observation_does_not_update_live_state(self):
        """Rejected observations must not update live monitoring."""

        self.tracker.process_state.return_value = False

        with patch(
            "mqtt_client.parse_ps5_payload",
            return_value=make_state(),
        ):
            accepted = self.client.handle_message(
                payload=b"test",
            )

        self.assertFalse(accepted)
        self.assertFalse(self.live_state.snapshot().available)
        self.notify.assert_not_called()

    def test_retained_observation_is_ignored(self):
        """Retained console observations must never be accepted."""

        accepted = self.client.handle_message(
            payload=b"test",
            retained=True,
        )

        self.assertFalse(accepted)
        self.tracker.process_state.assert_not_called()
        self.notify.assert_not_called()

    def test_disconnect_invalidates_live_state(self):
        """MQTT disconnection must invalidate confirmed state."""

        self.live_state.observe(make_state())

        self.client._on_disconnect(
            client=Mock(),
            userdata=None,
            disconnect_flags=None,
            reason_code=0,
            properties=None,
        )

        self.assertFalse(self.live_state.snapshot().available)
        self.notify.assert_called_once()

    def test_reconnection_invalidates_and_republishes(self):
        """A new connection must invalidate previous observations."""

        self.live_state.observe(make_state())

        mqtt = Mock()
        mqtt.subscribe.return_value = (0, 1)

        self.client._on_connect(
            client=mqtt,
            userdata=None,
            flags=None,
            reason_code=0,
            properties=None,
        )

        self.assertFalse(self.live_state.snapshot().available)
        self.assertEqual(self.client.connection_generation, 1)

        self.republish.assert_called_once()

    def test_persistence_failure_propagates(self):
        """Persistence failures must not produce confirmed states."""

        self.tracker.process_state.side_effect = RuntimeError(
            "Simulated database failure."
        )

        with patch(
            "mqtt_client.parse_ps5_payload",
            return_value=make_state(),
        ):
            with self.assertRaises(RuntimeError):
                self.client.handle_message(
                    payload=b"test",
                )

        self.assertFalse(self.live_state.snapshot().available)
        self.notify.assert_not_called()

    def test_duplicate_injection_rejected(self):
        """Live dependencies cannot be replaced after configuration."""

        with self.assertRaises(RuntimeError):
            self.client.set_live_monitoring(
                self.live_state,
                self.publisher,
            )




class PS5LiveMQTTFailureRecoveryTests(unittest.TestCase):
    """Verify MQTT failure recovery using shared test fixtures."""

    setUp = PS5LiveMQTTIntegrationTests.setUp
    tearDown = PS5LiveMQTTIntegrationTests.tearDown
    """
    Verify recovery through the real MQTT message callback.

    These tests exercise failure handling without establishing
    a broker connection or accessing production SQLite.
    """

    def test_message_failure_invalidates_previous_state(self):
        """
        A persistence failure must invalidate a previously
        confirmed live observation.
        """

        self.live_state.observe(make_state())

        self.tracker.process_state.side_effect = RuntimeError(
            "Simulated persistence failure."
        )

        message = Mock()
        message.topic = self.config.mqtt_topic
        message.payload = b"test"
        message.retain = False

        with patch(
            "mqtt_client.parse_ps5_payload",
            return_value=make_state(),
        ):
            with patch(
                "mqtt_client.LOGGER.exception"
            ):
                self.client._on_message(
                    client=Mock(),
                    userdata=None,
                    message=message,
                )

        self.assertFalse(
            self.live_state.snapshot().available
        )

        self.tracker.connection_lost.assert_called_once()
        self.notify.assert_called_once()

    def test_failed_recovery_still_invalidates_live_state(self):
        """
        Live state must be invalidated even when session
        recovery itself raises an exception.
        """

        self.live_state.observe(make_state())

        self.tracker.connection_lost.side_effect = RuntimeError(
            "Simulated recovery failure."
        )

        with self.assertRaises(RuntimeError):
            self.client._on_disconnect(
                client=Mock(),
                userdata=None,
                disconnect_flags=None,
                reason_code=0,
                properties=None,
            )

        self.assertFalse(
            self.live_state.snapshot().available
        )

        self.notify.assert_called_once()

if __name__ == "__main__":
    unittest.main(verbosity=2)
