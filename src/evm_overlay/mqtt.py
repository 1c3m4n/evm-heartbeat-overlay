from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from evm_overlay.config import MqttConfig


class PublishClient(Protocol):
    def publish(self, topic: str, payload: str, retain: bool = False) -> object: ...
    def username_pw_set(self, username: str, password: str | None = None) -> object: ...
    def connect(self, host: str, port: int, keepalive: int) -> object: ...
    def loop_start(self) -> object: ...


def connect_publisher(config: MqttConfig, client_factory: Callable[[str], PublishClient] | None = None) -> "MqttPublisher":
    if client_factory is None:
        from paho.mqtt.client import Client

        client_factory = Client
    client = client_factory(config.topic_prefix)
    if config.username:
        client.username_pw_set(config.username, config.password)
    client.connect(config.host, config.port, 60)
    client.loop_start()
    publisher = MqttPublisher(
        client=client,
        discovery_prefix=config.discovery_prefix,
        topic_prefix=config.topic_prefix,
        device_name=config.device_name,
    )
    publisher.publish_discovery()
    return publisher


class MqttPublisher:
    """Publish Home Assistant MQTT discovery plus the latest telemetry state."""

    def __init__(self, *, client: PublishClient, discovery_prefix: str, topic_prefix: str, device_name: str) -> None:
        self.client = client
        self.discovery_prefix = discovery_prefix.rstrip("/")
        self.topic_prefix = topic_prefix.rstrip("/")
        self.device_name = device_name

    @property
    def state_topic(self) -> str:
        return f"{self.topic_prefix}/state"

    def publish_discovery(self) -> None:
        metrics = {
            "pulse_bpm": ("Pulse", "bpm", "measurement"),
            "pulse_confidence": ("Pulse confidence", None, "measurement"),
            "breathing_bpm": ("Breathing", "br/min", "measurement"),
            "breathing_confidence": ("Breathing confidence", None, "measurement"),
            "signal_quality": ("Signal quality", None, "measurement"),
        }
        for metric, (name, unit, state_class) in metrics.items():
            payload = {
                "name": name,
                "unique_id": f"{self.topic_prefix.replace('/', '_')}_{metric}",
                "state_topic": self.state_topic,
                "value_template": f"{{{{ value_json.{metric} }}}}",
                "state_class": state_class,
                "device": {"identifiers": [self.topic_prefix], "name": self.device_name, "manufacturer": "EVM Heartbeat Overlay"},
            }
            if unit is not None:
                payload["unit_of_measurement"] = unit
            topic = f"{self.discovery_prefix}/sensor/{self.topic_prefix.replace('/', '_')}_{metric}/config"
            self.client.publish(topic, json.dumps(payload), retain=True)

    def publish_state(self, telemetry: dict[str, object]) -> None:
        self.client.publish(self.state_topic, json.dumps(telemetry), retain=False)
