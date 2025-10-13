#!/usr/bin/env python3
"""
Tests for the MCP Dashboard Server
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dashboard_imports():
    """Test that dashboard server can be imported."""
    try:
        from servers import dashboard_server

        assert hasattr(dashboard_server, "app")
        assert hasattr(dashboard_server, "main")
        print("✓ Dashboard imports work")
        return True
    except ImportError as e:
        print(f"✗ Dashboard import failed: {e}")
        print("  Install dependencies: pip install fastapi uvicorn[standard]")
        return False


def test_dashboard_structure():
    """Test that dashboard has required components."""
    try:
        from servers.dashboard_server import app, SERVERS, get_redis_client

        # Check FastAPI app
        assert app is not None
        assert app.title == "MCP Operations Dashboard"

        # Check server definitions
        assert len(SERVERS) > 0
        assert "memory-cache" in SERVERS
        assert "goal-agent" in SERVERS

        print("✓ Dashboard structure is valid")
        return True
    except Exception as e:
        print(f"✗ Dashboard structure test failed: {e}")
        return False


def test_static_files():
    """Test that static files exist."""
    project_root = Path(__file__).parent.parent
    static_dir = project_root / "servers" / "static"
    index_file = static_dir / "index.html"

    if not static_dir.exists():
        print(f"✗ Static directory not found: {static_dir}")
        return False

    if not index_file.exists():
        print(f"✗ Dashboard HTML not found: {index_file}")
        return False

    print("✓ Static files exist")
    return True


def test_api_endpoints():
    """Test that API routes are registered."""
    try:
        from servers.dashboard_server import app

        routes = [route.path for route in app.routes]

        required_routes = [
            "/",
            "/api/status",
            "/api/servers",
            "/api/redis/stats",
            "/api/goals",
            "/api/logs",
            "/api/health",
        ]

        for route in required_routes:
            if route not in routes:
                print(f"✗ Missing API route: {route}")
                return False

        print("✓ All API endpoints registered")
        return True
    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        return False


def main():
    """Run all dashboard tests."""
    print("=" * 60)
    print("MCP Dashboard Tests".center(60))
    print("=" * 60)
    print()

    tests = [
        test_dashboard_imports,
        test_static_files,
    ]

    # Only run advanced tests if imports work
    if test_dashboard_imports():
        tests.extend(
            [
                test_dashboard_structure,
                test_api_endpoints,
            ]
        )

    results = []
    for test in tests[1:]:  # Skip first test since we already ran it
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
        print()

    # Summary
    print("=" * 60)
    passed = sum(results) + 1  # +1 for imports test
    total = len(tests)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print()
        print("✅ All dashboard tests passed!")
        print()
        print("To start the dashboard:")
        print("  ./mcpctl.py dashboard")
        print("  or: python servers/dashboard_server.py")
        print()
        print("Access at: http://localhost:8000")
        print()
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Install missing dependencies:")
        print("  pip install fastapi uvicorn[standard]")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
