# -*- coding: utf-8 -*-
"""
Pelny potok analiz rakiety L9 (EuRoC, kategoria Liquid 9 km).
Uzycie:  python run_all.py          (calosc, ~5-10 min)
         python run_all.py quick    (bez Monte Carlo)
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    "simulate_baseline.py",
    "analysis_stability.py",
    "analysis_recovery.py",
    "analysis_flutter.py",
    "analysis_sensitivity.py",
]


def main():
    quick = "quick" in sys.argv
    for step in STEPS:
        if quick and step == "analysis_sensitivity.py":
            args = [sys.executable, step, "24"]
        else:
            args = [sys.executable, step]
        print("\n" + "=" * 70 + f"\n>>> {step}\n" + "=" * 70)
        r = subprocess.run(args, cwd=HERE)
        if r.returncode != 0:
            print(f"BLAD w {step}")
            sys.exit(1)
    print("\nWszystko wykonane. Wyniki w katalogu results/")


if __name__ == "__main__":
    main()
