# -*- coding: utf-8 -*-
"""
Analiza stabilnosci statycznej: dobor statecznikow i wedrowka CG/CP w locie.
Wymagania: [SRD EuRoC-LV-RQT-1030] margines >= 1.5 kalibra przez caly lot
(od chwili zejscia z szyny), z unikaniem nadstatecznosci > 6 kalibrow
(przesuniecie CP od oporu falowego moze byc istotne juz od ~0.5 Ma).

Uzycie: python analysis_stability.py
"""
import os
import itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import config as C
import environment_model as EM
import motor_model as MM
import rocket_model as RM

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)


def margin_table():
    """Sweep geometrii statecznikow: margines na starcie i na MECO."""
    motor, _ = MM.build_motor()
    rows = []
    for span, root, n in itertools.product(
        [0.08, 0.09, 0.10, 0.11, 0.12, 0.14, 0.16],
        [0.40, 0.50, 0.60],
        [3, 4],
    ):
        rocket = RM.build_rocket(motor, fin_span=span, fin_root=root, fin_n=n)
        sm = rocket.evaluate_static_margin()
        s0, sb = float(sm(0.0)), float(sm(C.BURN_TIME))
        rows.append((n, span, root, round(s0, 2), round(sb, 2)))
    return rows


def cg_cp_flight(flight):
    """CG(t) i CP(t) z symulacji (CP = CG +/- margines * kaliber)."""
    tt = np.linspace(flight.out_of_rail_time, flight.apogee_time, 200)
    cg = [float(flight.rocket.center_of_mass(t)) for t in tt]
    sm = [float(flight.static_margin(t)) for t in tt]
    # w ukladzie tail_to_nose CP lezy ZA CG: CP = CG - SM * kaliber
    cp = [cg[i] - sm[i] * 2 * C.BODY_RADIUS for i in range(len(tt))]
    return tt, np.array(cg), np.array(cp), np.array(sm)


def main():
    motor, minfo = MM.build_motor()
    rocket = RM.build_rocket(motor)
    flight = RM.run_flight(rocket, EM.make_environment(), terminate_on_apogee=True)

    rows = margin_table()
    with open(os.path.join(OUT, "stability_fin_sweep.csv"), "w") as f:
        f.write("n_fin,span_m,root_chord_m,SM_launch_cal,SM_MECO_cal\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    # wykres 1: sweep statecznikow
    fig, ax = plt.subplots(figsize=(9, 5))
    for n in (3, 4):
        for root in (0.40, 0.50, 0.60):
            xs = [r[1] for r in rows if r[0] == n and r[2] == root]
            ys = [r[3] for r in rows if r[0] == n and r[2] == root]
            ax.plot(xs, ys, "-o", ms=3, label=f"n={n}, root={root:.2f} m")
    ax.axhline(C.LIMIT_MARGIN_MIN, color="r", ls="--", label="min 1.5 cal [SRD]")
    ax.axhline(C.LIMIT_MARGIN_MAX, color="orange", ls="--", label="max 6 cal [SRD]")
    ax.axvline(C.FIN_SPAN, color="k", ls=":", label="konfiguracja bazowa")
    ax.set_xlabel("rozpietosc statecznika [m]")
    ax.set_ylabel("margines statyczny na starcie [cal]")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    ax.set_title("Dobor statecznikow: margines vs geometria")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "06_fin_sweep.png"), dpi=130)
    plt.close(fig)

    # wykres 2: CG/CP/margines w locie bazowym
    tt, cg, cp, sm = cg_cp_flight(flight)
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True,
                           gridspec_kw={"height_ratios": [1, 1]})
    ax[0].plot(tt, cg, "b", label="CG [m od ogona]")
    ax[0].plot(tt, cp, "r", label="CP [m od ogona]")
    ax[0].axvline(C.BURN_TIME, color="gray", ls=":", label="MECO")
    ax[0].set_ylabel("pozycja [m]")
    ax[0].legend()
    ax[0].grid(alpha=0.3)
    ax[0].set_title("Wedrowka CG (spalanie paliwa) i CP (opór falowy) w locie")
    ax[1].plot(tt, sm, "g", label="margines statyczny [cal]")
    ax[1].axhline(C.LIMIT_MARGIN_MIN, color="r", ls="--")
    ax[1].axhline(C.LIMIT_MARGIN_MAX, color="orange", ls="--")
    ax[1].set_xlabel("t [s]")
    ax[1].set_ylabel("SM [cal]")
    ax[1].grid(alpha=0.3)
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "07_cg_cp_margin.png"), dpi=130)
    plt.close(fig)

    print("Sweep statecznikow (n, span, root, SM_start, SM_MECO):")
    for r in rows:
        mark = "  <-- baza" if (r[1] == C.FIN_SPAN and r[2] == C.FIN_ROOT_CHORD
                                and r[0] == C.FIN_COUNT) else ""
        print("  ", r, mark)
    print(f"\nLot bazowy: SM min={flight.min_stability_margin:.2f}, "
          f"max={flight.max_stability_margin:.2f}, "
          f"rail={flight.out_of_rail_stability_margin:.2f} cal")


if __name__ == "__main__":
    main()
