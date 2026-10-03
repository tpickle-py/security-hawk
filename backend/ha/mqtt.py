"""Lightweight asyncio MQTT 3.1.1 client for publishing state & discovery packets.

Zero external dependencies; speaks standard MQTT 3.1.1 binary framing.
Supports username/password authentication, QoS 0 publishing, and Home Assistant
MQTT discovery topics.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _encode_remaining_length(length: int) -> bytes:
    """Encode variable byte integer per MQTT 3.1.1 spec."""
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 0x80
        encoded.append(digit)
        if length == 0:
            break
    return bytes(encoded)


def _encode_utf8_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return len(b).to_bytes(2, "big") + b


class LightweightMqttClient:
    """Async MQTT publisher for publishing state updates and HA discovery payloads."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        username: str = "",
        password: str = "",
        client_id: str = "security_hawk",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id

    async def publish(
        self,
        topic: str,
        payload: str | bytes | dict[str, Any],
        retain: bool = False,
        timeout: float = 3.0,
    ) -> bool:
        """Connect, publish a message with QoS 0, and cleanly disconnect."""
        if isinstance(payload, dict):
            payload_bytes = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = payload

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout,
            )

            # Build CONNECT packet
            protocol_name = _encode_utf8_str("MQTT")
            protocol_level = bytes([0x04])  # MQTT 3.1.1
            connect_flags = 0x02  # Clean session

            variable_header = protocol_name + protocol_level

            # Payload: Client ID
            payload_data = bytearray(_encode_utf8_str(self.client_id))

            if self.username:
                connect_flags |= 0x80
                payload_data += _encode_utf8_str(self.username)
                if self.password:
                    connect_flags |= 0x40
                    payload_data += _encode_utf8_str(self.password)

            variable_header += bytes([connect_flags]) + (60).to_bytes(2, "big")  # 60s keepalive

            connect_body = variable_header + bytes(payload_data)
            connect_packet = (
                bytes([0x10]) + _encode_remaining_length(len(connect_body)) + connect_body
            )
            writer.write(connect_packet)
            await writer.drain()

            # Read CONNACK (fixed 4 bytes: 0x20, 0x02, session_present, return_code)
            connack = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
            if len(connack) < 4 or connack[0] != 0x20 or connack[3] != 0x00:
                logger.warning(
                    "MQTT connection rejected with code %s",
                    connack[3] if len(connack) >= 4 else "unknown",
                )
                writer.close()
                await writer.wait_closed()
                return False

            # Build PUBLISH packet (QoS 0)
            fixed_header_byte = 0x30
            if retain:
                fixed_header_byte |= 0x01

            topic_bytes = _encode_utf8_str(topic)
            publish_body = topic_bytes + payload_bytes
            publish_packet = (
                bytes([fixed_header_byte])
                + _encode_remaining_length(len(publish_body))
                + publish_body
            )

            writer.write(publish_packet)
            await writer.drain()

            # DISCONNECT packet
            writer.write(bytes([0xE0, 0x00]))
            await writer.drain()

            writer.close()
            await writer.wait_closed()
            return True

        except Exception as e:
            logger.debug(
                "MQTT publish failed to %s:%s for topic %s: %s", self.host, self.port, topic, e
            )
            return False

    async def publish_ha_discovery(
        self,
        rule_id: str,
        rule_name: str,
        state_topic: str,
        device_class: str = "safety",
    ) -> bool:
        """Publish an MQTT discovery packet so HA automatically registers the entity."""
        discovery_topic = f"homeassistant/binary_sensor/security_hawk_{rule_id}/config"
        discovery_payload = {
            "name": f"Security Hawk {rule_name}",
            "unique_id": f"security_hawk_{rule_id}",
            "state_topic": state_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": device_class,
            "device": {
                "identifiers": ["security_hawk"],
                "name": "Security Hawk",
                "model": "Floor Plan Automation",
                "manufacturer": "Security Hawk",
            },
        }
        return await self.publish(discovery_topic, discovery_payload, retain=True)
