"""
Navronis Example 09: Flight Engine Reference Benchmarks & Historical Verification (Day 6)
========================================================================================
Demonstrates community validation of Navronis first-principles models against published
NASA, AIAA, and manufacturer test-stand datasets for 7 iconic flight rocket engines:

1. SpaceX Merlin 1D (Gas Generator, Kerolox)
2. SpaceX Raptor 2 (Full-Flow Staged Combustion, Methalox)
3. Aerojet Rocketdyne RS-25 SSME (Fuel-Rich Staged Combustion, Hydrolox)
4. NPO Energomash RD-180 (Oxidizer-Rich Staged Combustion, Kerolox)
5. Pratt & Whitney RL10A-4-2 (Closed Expander, Hydrolox)
6. Rocket Lab Rutherford (Electric Pump BLDC Battery, Kerolox)
7. Apollo Lunar Module Descent Engine LMDE (Deep Throttling Pressure-Fed, Hypergolic)

Run this script directly:
    python examples/09_flight_engine_benchmarks.py
"""

from __future__ import annotations

import sys
from kryptonis.propulsion_equations.engine_deck import (
    LIST_ENGINES,
    EngineBenchmark,
    benchmark_all_engines,
)


def main() -> int:
    print("=" * 82)
    print("     NAVRONIS FLIGHT ENGINE VERIFICATION BENCHMARK SUITE (DAY 6)")
    print("=" * 82)
    print("Benchmarking 7 flight engines against authoritative test-stand datasets...\n")

    results = benchmark_all_engines(error_tolerance_percent=15.0)

    for key in LIST_ENGINES:
        res = results[key]
        print(res.summary_table())
        print()

    # Summary scoreboard
    print("=" * 82)
    print("                      OVERALL BENCHMARK VERDICT SCOREBOARD")
    print("=" * 82)
    print(f"  {'ENGINE':<34} | {'MEAN ERROR':<12} | {'MAX ERROR':<12} | {'STATUS'}")
    print("-" * 82)
    all_passed = True
    for key in LIST_ENGINES:
        res = results[key]
        status_str = "PASS" if res.passed else "WARN"
        if not res.passed:
            all_passed = False
        print(f"  {res.engine_name:<34} | {res.mean_absolute_error_percent:<10.2f}% | {res.max_error_percent:<10.2f}% | {status_str}")
    print("=" * 82)

    grand_mean = sum(r.mean_absolute_error_percent for r in results.values()) / len(results)
    print(f"  Grand Mean Absolute Error Across All 7 Engines: {grand_mean:.2f}%")
    print(f"  Overall Verification Status: {'ALL BENCHMARKS PASSED (100%)' if all_passed else 'DISCREPANCY DETECTED'}")
    print("=" * 82)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
