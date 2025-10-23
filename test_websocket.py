#!/usr/bin/env python3
"""
Test WebSocket connection to the dashboard server.
"""

import asyncio
import json
import sys

import websockets


async def test_websocket():
    uri = "ws://localhost:8000/ws"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully!")

            # Receive initial message
            print("\nWaiting for initial message...")
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)

            print(f"✓ Received message type: {data.get('type')}")
            print(f"  Timestamp: {data.get('timestamp')}")

            if data.get("type") == "initial":
                print("\n✓ Initial data received!")
                if "data" in data:
                    data_keys = list(data["data"].keys())
                    print(f"  Data keys: {data_keys}")

                    if "status" in data["data"]:
                        servers = data["data"]["status"]["servers"]
                        print(
                            f"  Servers: {servers['running']}/{servers['total']} running"
                        )

                    if "servers" in data["data"]:
                        server_count = len(data["data"]["servers"]["servers"])
                        print(f"  Server details: {server_count} servers")

            # Send a refresh request
            print("\n→ Sending refresh request...")
            await websocket.send(json.dumps({"type": "refresh"}))

            # Wait for response
            print("Waiting for refresh response...")
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"✓ Received message type: {data.get('type')}")

            # Wait for a broadcast update (or ping)
            print("\nWaiting for broadcast update (timeout 5s)...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"✓ Received message type: {data.get('type')}")
            except asyncio.TimeoutError:
                print(
                    "  (No broadcast within 5 seconds - this is normal if data hasn't changed)"
                )

            print("\n✓ All WebSocket tests passed!")
            return True

    except asyncio.TimeoutError:
        print("✗ Timeout waiting for message")
        return False
    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Dashboard Test")
    print("=" * 60)
    print()

    result = asyncio.run(test_websocket())

    print()
    print("=" * 60)
    if result:
        print("✓ TEST PASSED")
        sys.exit(0)
    else:
        print("✗ TEST FAILED")
        sys.exit(1)
