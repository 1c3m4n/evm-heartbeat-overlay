import json

from evm_overlay.config import MqttConfig
from evm_overlay.mqtt import MqttPublisher, connect_publisher


class RecordingClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


def test_mqtt_publisher_emits_home_assistant_discovery_and_state():
    client = RecordingClient()
    publisher = MqttPublisher(
        client=client,
        discovery_prefix="homeassistant",
        topic_prefix="nursery_evm",
        device_name="Nursery EVM",
    )

    publisher.publish_discovery()
    publisher.publish_state(
        {
            "pulse_bpm": 120.0,
            "pulse_confidence": 0.8,
            "breathing_bpm": 30.0,
            "breathing_confidence": 0.6,
            "signal_quality": 0.8,
        }
    )

    topics = [topic for topic, _, _ in client.published]
    assert "homeassistant/sensor/nursery_evm_pulse_bpm/config" in topics
    assert "homeassistant/sensor/nursery_evm_breathing_bpm/config" in topics
    assert topics[-1] == "nursery_evm/state"
    assert client.published[-1][2] is False
    state = json.loads(client.published[-1][1])
    assert state["pulse_bpm"] == 120.0

    pulse_config = next(json.loads(payload) for topic, payload, _ in client.published if topic.endswith("pulse_bpm/config"))
    assert pulse_config["state_topic"] == "nursery_evm/state"
    assert pulse_config["value_template"] == "{{ value_json.pulse_bpm }}"


def test_connect_publisher_configures_client_and_publishes_discovery():
    client = RecordingClient()
    client.connected = None
    client.loop_started = False
    client.username = None
    client.username_pw_set = lambda username, password: setattr(client, "username", (username, password))
    client.connect = lambda host, port, keepalive: setattr(client, "connected", (host, port, keepalive))
    client.loop_start = lambda: setattr(client, "loop_started", True)
    config = MqttConfig(enabled=True, host="mqtt.local", username="user", password="secret", topic_prefix="test_evm")

    publisher = connect_publisher(config, client_factory=lambda client_id: client)

    assert publisher.state_topic == "test_evm/state"
    assert client.username == ("user", "secret")
    assert client.connected == ("mqtt.local", 1883, 60)
    assert client.loop_started is True
    assert any(topic.endswith("/config") for topic, _, _ in client.published)
