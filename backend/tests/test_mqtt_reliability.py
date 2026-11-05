"""
PS5 Monitoring Service - MQTT Reliability Tests.

These tests verify MQTT QoS 1 publication behavior and Last Will
registration without connecting to a real MQTT broker.

All credentials, network connections, and database operations
are simulated.
"""

import unittest

from pathlib import Path
from unittest.mock import Mock, patch

import paho.mqtt.client as mqtt

from config import AppConfig
from mqtt_client import PS5MQTTClient


class MQTTReliabilityTests(unittest.TestCase):
    """Validate MQTT publishing and Last Will configuration."""

    def setUp(self):
        """Create an isolated MQTT client for each test."""

        self.config = AppConfig(
            mqtt_host="localhost",
            mqtt_port=1883,
            mqtt_username="test",
            mqtt_password="test",
            mqtt_topic="ps5-mqtt/YOUR_DEVICE_ID",
            player_name="PlayerOne",
            database_path=Path("/data/test.db"),
        )

        self.tracker = Mock()

        self.client = PS5MQTTClient(
            config=self.config,
            tracker=self.tracker,
            timeout_seconds=30,
        )

        self.fake_client = Mock()
        self.fake_result = Mock()

        self.fake_result.rc = mqtt.MQTT_ERR_SUCCESS
        self.fake_result.is_published.return_value = True

        self.fake_client.publish.return_value = self.fake_result

        self.client._client = self.fake_client
        self.client._connected = True

    def test_qos1_acknowledgement(self):
        """QoS 1 publication must wait for broker confirmation."""

        self.client.publish(
            "ps5-monitor/test",
            "online",
            qos=1,
            retain=True,
        )

        self.fake_result.wait_for_publish.assert_called_once_with(
            timeout=10.0
        )

        self.assertTrue(
            self.fake_client.publish.call_args.kwargs["retain"]
        )

    def test_publication_timeout(self):
        """Unconfirmed publications must raise a timeout."""

        self.fake_result.is_published.return_value = False

        with self.assertRaises(TimeoutError):
            self.client.publish(
                "ps5-monitor/test",
                "timeout",
                qos=1,
            )

    def test_broker_publication_failure(self):
        """Immediate MQTT errors must not be ignored."""

        self.fake_result.rc = mqtt.MQTT_ERR_NO_CONN

        with self.assertRaises(RuntimeError):
            self.client.publish(
                "ps5-monitor/test",
                "failure",
                qos=1,
            )

    def test_last_will_registration(self):
        """The broker must receive the retained offline Last Will."""

        with patch("paho.mqtt.client.Client") as factory:
            fake_client = factory.return_value

            client = PS5MQTTClient(
                config=self.config,
                tracker=self.tracker,
            )

            try:
                client.start()

                fake_client.will_set.assert_called_once_with(
                    topic="ps5-monitor/availability",
                    payload="offline",
                    qos=1,
                    retain=True,
                )
            finally:
                client.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
