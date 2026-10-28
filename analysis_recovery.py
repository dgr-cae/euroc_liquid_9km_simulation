# -*- coding: utf-8 -*-
"""
Dobor systemu odzysku (dual deployment):
  * sweep Cd*S drogue -> predkosc opadania w pasmie 23-46 m/s [SRD RQT-0360],
  * sweep Cd*S main   -> predkosc przyziemienia < 9 m/s       [SRD RQT-0380],
  * analityczne oszacowanie v = sqrt(2 m g / (rho CdS)) jako sanity check.

Uzycie: python analysis_recovery.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import compliance as CP
import config as C
import environment_model as EM
import motor_model as MM
import rocket_model as RM

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)

G0 = 9.80665
M_DESCENT = C.ROCKET_MASS + C.MOTOR_DRY_MASS   # masa w fazie opadania (~sucha)


def analytic_v(cds, rho):
    return np.sqrt(2 * M_DESCENT * G0 / (rho * cds))


def run_descent(drogue_cd_s=None, main_cd_s=None):
    motor, _ = MM.build_motor()
    rocket = RM.build_rocket(motor, drogue_cd_s=drogue_cd_s, main_cd_s=main_cd_s)
    flight = RM.run_flight(rocket, EM.make_environment())
    sol = flight.solution_array
    t, z, vz = sol[:, 0], sol[:, 3] - C.SITE_ELEVATION, sol[:, 6]
    ev = flight.parachute_events
    t_d = ev[0][0]
    t_m = ev[1][0] if len(ev) > 1 else np.nan
    v_bands = CP.descent_speeds_at(flight, [7000, 5000, 3000, 1500, 600])
    return {
        "v_bands": v_bands,
        "touchdown": abs(float(flight.impact_velocity)),
        "t_ground": float(t[-1]),
        "alt_main": float(np.interp(t_m, t, z)) if len(ev) > 1 else np.nan,
        "drift": float(np.hypot(sol[-1, 1], sol[-1, 2])),
        "flight": flight,
    }


def main():
    print(f"Masa w fazie opadania: {M_DESCENT:.1f} kg")
    print("Analitycznie (rho=1.15 kg/m3, niska wysokosc):")
    for cds in (0.6, 0.8, 1.0, 1.2, 1.4):
        print(f"  drogue CdS={cds:.1f} -> v={analytic_v(cds, 1.15):.1f} m/s | "
              f"na 9 km (rho=0.47): {analytic_v(cds, 0.47):.1f} m/s")
    for cds in (8, 10, 11.4, 13, 15):
        print(f"  main   CdS={cds:.1f} -> v={analytic_v(cds, 1.18):.1f} m/s")

    # sweep symulacyjny drogue
    drogue_res = {}
    for cds in (0.7, 0.85, 1.0, 1.15, 1.3):
        r = run_descent(drogue_cd_s=cds)
        drogue_res[cds] = r
        ok = all(C.LIMIT_DROGUE_V_MIN <= v <= C.LIMIT_DROGUE_V_MAX
                 for v in r["v_bands"] if not np.isnan(v))
        print(f"SIM drogue CdS={cds:.2f}: v(pasma)={[round(v,1) for v in r['v_bands']]} "
              f"przyziemienie={r['touchdown']:.1f} t={r['t_ground']:.0f} s "
              f"drift={r['drift']:.0f} m  {'OK' if ok else 'POZA PASMEM'}")

    # sweep main
    main_res = {}
    for cds in (9.0, 10.5, 11.4, 12.5, 14.0):
        r = run_descent(main_cd_s=cds)
        main_res[cds] = r
        ok = r["touchdown"] < C.LIMIT_TOUCHDOWN_V
        print(f"SIM main   CdS={cds:.2f}: przyziemienie={r['touchdown']:.2f} m/s "
              f"{'OK' if ok else 'ZA SZYBKO'}")

    # wykres: profil opadania dla roznych drogue
    fig, ax = plt.subplots(figsize=(9, 5))
    for cds, r in drogue_res.items():
        sol = r["flight"].solution_array
        t, z, vz = sol[:, 0], sol[:, 3] - C.SITE_ELEVATION, sol[:, 6]
        ev = r["flight"].parachute_events
        mask = t > ev[0][0] + 1.0
        ax.plot(np.abs(vz[mask]), z[mask], label=f"drogue CdS={cds:.2f}")
    ax.axvline(C.LIMIT_DROGUE_V_MIN, color="k", ls="--")
    ax.axvline(C.LIMIT_DROGUE_V_MAX, color="k", ls="--")
    ax.axvline(C.LIMIT_TOUCHDOWN_V, color="r", ls="--")
    ax.set_ylim(0, 9500)
    ax.set_xlim(0, 50)
    ax.set_xlabel("|v_z| [m/s]")
    ax.set_ylabel("z [m AGL]")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_title("Wplyw CdS drogue na profil opadania (pasm 23-46 m/s i limit 9 m/s)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "08_recovery_sweep.png"), dpi=130)
    plt.close(fig)

    with open(os.path.join(OUT, "recovery_sweep.csv"), "w") as f:
        f.write("case,cd_s,v7000,v5000,v3000,v1500,v600,touchdown,t_ground_s,drift_m\n")
        for cds, r in drogue_res.items():
            f.write("drogue," + str(cds) + "," +
                    ",".join(f"{v:.2f}" for v in r["v_bands"]) +
                    f",{r['touchdown']:.2f},{r['t_ground']:.0f},{r['drift']:.0f}\n")
        for cds, r in main_res.items():
            f.write("main," + str(cds) + "," +
                    ",".join(f"{v:.2f}" for v in r["v_bands"]) +
                    f",{r['touchdown']:.2f},{r['t_ground']:.0f},{r['drift']:.0f}\n")


if __name__ == "__main__":
    main()
