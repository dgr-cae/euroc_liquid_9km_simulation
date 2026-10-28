# -*- coding: utf-8 -*-
"""
Symulacja bazowa (nominalna) lotu rakiety L9 + wykresy + raport zgodnosci.
Uzycie:  python simulate_baseline.py
"""
import os
import time

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


def main(save_plots=True, verbose=True):
    t0 = time.time()
    motor, minfo = MM.build_motor()
    rocket = RM.build_rocket(motor)
    env = EM.make_environment()
    flight = RM.run_flight(rocket, env)
    dt = time.time() - t0

    checks, metrics = CP.check_compliance(flight, minfo, rocket, env)
    if verbose:
        print(CP.format_report(checks, metrics))
        print(f"\nCzas symulacji: {dt:.1f} s | czas lotu: {flight.solution_array[-1,0]:.1f} s")

    if save_plots:
        _plots(flight, minfo, metrics)
        arr = flight.solution_array[:, :7].copy()
        arr[:, 3] -= flight.env.elevation
        np.savetxt(os.path.join(OUT, "baseline_trajectory.csv"), arr,
                   delimiter=",", header="t,x,y,z_agl,vx,vy,vz", comments="")
        with open(os.path.join(OUT, "baseline_compliance.txt"), "w") as f:
            f.write(CP.format_report(checks, metrics))
    return flight, minfo, checks, metrics


def _plots(flight, minfo, metrics):
    sol = flight.solution_array
    t, x, y, z, vx, vy, vz = (sol[:, 0], sol[:, 1], sol[:, 2],
                            sol[:, 3] - flight.env.elevation,
                            sol[:, 4], sol[:, 5], sol[:, 6])

    # 1) wysokosc i predkosc
    fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    ax[0].plot(t, z, "b", label="wysokosc AGL [m]")
    ax[0].axhline(C.TARGET_APOGEE_AGL, color="g", ls="--", label="cel 9000 m")
    ax[0].axvline(flight.out_of_rail_time, color="gray", ls=":", label="zejscie z szyny")
    ax[0].axvline(metrics["t_drogue"], color="orange", ls=":", label="drogue")
    ax[0].axvline(metrics["t_main"], color="red", ls=":", label="main")
    ax[0].set_ylabel("z [m AGL]"); ax[0].legend(loc="center right"); ax[0].grid(alpha=.3)
    v = np.sqrt(vx**2 + vy**2 + vz**2)
    ax[1].plot(t, v, "r", label="predkosc calkowita")
    ax[1].plot(t, vz, "b", alpha=.6, label="v_z")
    ax[1].axhline(0, color="k", lw=.5)
    ax[1].set_xlabel("t [s]"); ax[1].set_ylabel("v [m/s]"); ax[1].legend(); ax[1].grid(alpha=.3)
    fig.suptitle("Lot nominalny L9: profil pionowy")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_altitude_velocity.png"), dpi=130)
    plt.close(fig)

    # 2) krzywa ciagu i hold-down
    fig, ax = plt.subplots(figsize=(9, 4.5))
    cf, cd = minfo["curve_full"], minfo["curve_dyn"]
    ax.plot(cf[:, 0], cf[:, 1] / 1000, "b", label="krzywa pelna (silnik)")
    ax.plot(cd[:, 0], cd[:, 1] / 1000, "r--", label="krzywa po hold-down (dynamika)")
    ax.axhline(minfo["f_release"] / 1000, color="g", ls="--",
               label=f"prog zwolnienia {minfo['f_release']/1000:.2f} kN")
    ax.axhline(minfo["w_rail"] / 1000, color="orange", ls=":",
               label=f"skladowa ciezaru wzdluz szyny {minfo['w_rail']/1000:.2f} kN")
    ax.axvline(minfo["t_release"], color="k", ls=":", label=f"t_release={minfo['t_release']:.2f} s")
    ax.set_xlabel("t [s]"); ax.set_ylabel("F [kN]"); ax.legend(); ax.grid(alpha=.3)
    ax.set_title(f"Napęd LOX/EtOH: Isp={minfo['isp']:.0f} s, impuls={minfo['total_impulse']/1000:.1f} kNs")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_thrust_hold_down.png"), dpi=130)
    plt.close(fig)

    # 3) stabilnosc w czasie
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sm = flight.static_margin
    tt = np.linspace(flight.out_of_rail_time, min(flight.apogee_time, 60), 300)
    ax.plot(tt, [sm(v) for v in tt], "b", label="margines statyczny [cal]")
    ax.axhline(C.LIMIT_MARGIN_MIN, color="r", ls="--", label="min 1.5 cal")
    ax.axhline(C.LIMIT_MARGIN_MAX, color="orange", ls="--", label="max 6 cal")
    ax.axvline(flight.rocket.motor.burn_out_time, color="gray", ls=":", label="MECO")
    ax.set_xlabel("t [s]"); ax.set_ylabel("SM [cal]"); ax.legend(); ax.grid(alpha=.3)
    ax.set_title("Margines stabilnosci statycznej w locie (wedrowka CG/CP)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_stability.png"), dpi=130)
    plt.close(fig)

    # 4) profil opadania
    fig, ax = plt.subplots(figsize=(9, 5))
    mask = t > metrics["t_drogue"]
    ax.plot(np.abs(vz[mask]), z[mask], "b", label="|v_z| podczas opadania")
    ax.axhspan(0, C.LIMIT_MAIN_ALT, color="red", alpha=.12, label="strefa main <=450 m")
    ax.axvline(C.LIMIT_DROGUE_V_MIN, color="orange", ls="--")
    ax.axvline(C.LIMIT_DROGUE_V_MAX, color="orange", ls="--", label="pasmo drogue 23-46 m/s")
    ax.axvline(C.LIMIT_TOUCHDOWN_V, color="red", ls="--", label="limit przyziemienia 9 m/s")
    ax.set_ylim(0, 9500); ax.set_xlim(0, 55)
    ax.set_xlabel("|v_z| [m/s]"); ax.set_ylabel("z [m AGL]"); ax.legend(loc="upper right"); ax.grid(alpha=.3)
    ax.set_title("Profil opadania: dual deployment")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_descent.png"), dpi=130)
    plt.close(fig)

    # 5) rzut poziomy
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.plot(x, y, "b", label="tor (rzut poziomy)")
    ax.plot([0], [0], "g^", label="wyrzutnia")
    ax.plot([x[-1]], [y[-1]], "rx", ms=10, label="miejsce ladowania")
    ax.set_xlabel("E [m]"); ax.set_ylabel("N [m]"); ax.legend(); ax.grid(alpha=.3)
    ax.set_title(f"Dryf wiatrowy: {metrics['drift']:.0f} m")
    ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "05_ground_track.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
