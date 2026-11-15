#!/usr/bin/env python3
"""
Test runner executing all protocol and daemon test suites.
"""

import sys
import traceback

import test_protocol
import test_daemon

def run_suite():
    tests = [
        ("test_protocol.test_packet_structure", test_protocol.test_packet_structure),
        ("test_protocol.test_dpi_serialization", test_protocol.test_dpi_serialization),
        ("test_protocol.test_active_dpi_selection", test_protocol.test_active_dpi_selection),
        ("test_protocol.test_lighting_serialization", test_protocol.test_lighting_serialization),
        ("test_protocol.test_battery_response_parsing", test_protocol.test_battery_response_parsing),
        ("test_protocol.test_polling_rate", test_protocol.test_polling_rate),
        ("test_protocol.test_tg_keyboard_protocol", test_protocol.test_tg_keyboard_protocol),
        ("test_daemon.test_daemon_profile_lifecycle", test_daemon.test_daemon_profile_lifecycle),
        ("test_daemon.test_daemon_request_dispatch", test_daemon.test_daemon_request_dispatch),
        ("test_daemon.test_tg_keyboard_rgb_dispatch", test_daemon.test_tg_keyboard_rgb_dispatch),
    ]

    passed = 0
    failed = 0

    print("=== Running DAREU Test Suite ===")
    for name, fn in tests:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)} tests.")
    if failed > 0:
        sys.exit(1)
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_suite()
