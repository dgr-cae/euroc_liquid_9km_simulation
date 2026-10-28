# -*- coding: utf-8 -*-
"""
Analiza wrazliwosci osiagow na parametry startu i konstrukcji:
  (a) sweep deterministyczny: elewacja szyny (70-85 deg), wiatr przyziemny,
      odchylenie temperatury/cisnienia od ISA, masa sucha, Isp, masa paliwa;
  (b) Monte Carlo (N prob) z jednoczesnym rozrzutem wszystkich parametrow.

Mierzone: apogeum AGL, predkosc zejscia z szyny [SRD RQT-1100], minimalny
margines stabilnosci [SRD RQT-1030], predkosc przyziemienia [SRD RQT-0380],
dryf wiatrowy.

Uzycie: python analysis_sensitivity.py [N_mc]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

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


def _metrics(flight, minfo):
    sol = flight.solution_array
    z = sol[:, 3] - C.SITE_ELEVATION
    ev = flight.parachute_events
    t_m = ev[1][0] if len(ev) > 1 else np.nan
    return {
        "apogee": float(flight.apogee_state[2]) - C.SITE_ELEVATION,
        "v_rail": float(flight.out_of_rail_velocity),
        "sm_min": float(flight.min_stability_margin),
        "touchdown": abs(float(flight.impact_velocity)),
        "alt_main": float(np.interp(t_m, sol[:, 0], z)) if len(ev) > 1 else np.nan,
        "drift": float(np.hypot(sol[-1, 1], sol[-1, 2])),
        "impulse": minfo["total_impulse"],
    }


def _run_case(args):
    (incl, wind10, temp_off, pres_f, mass_scale, isp_f, prop_f,
     drogue_f, main_alt) = args
    C.RAIL_INCLINATION = incl
    C.TEMP_OFFSET_ISA = temp_off
    C.PRESSURE_FACTOR = pres_f
    C.ISP_EFFECTIVE = C.ISP_BASE * isp_f
    C.PROPELLANT_MASS = C.PROP_BASE * prop_f
    motor, minfo = MM.build_motor(
        m_wet=C.ROCKET_MASS * mass_scale + C.MOTOR_DRY_MASS + C.PROPELLANT_MASS,
        inclination_deg=incl,
    )
    rocket = RM.build_rocket(motor, mass_scale=mass_scale,
                             drogue_cd_s=C.DROGUE_CD_S * drogue_f,
                             main_alt=main_alt)
    env = EM.make_environment(wind10=wind10, temp_offset=temp_off,
                              pressure_factor=pres_f)
    flight = RM.run_flight(rocket, env, inclination=incl)
    return _metrics(flight, minfo)


def _init_worker():
    # kazdy proces dostaje wlasna kopie configu
    import importlib
    importlib.reload(C)
    C.ISP_BASE = C.ISP_EFFECTIVE
    C.PROP_BASE = C.PROPELLANT_MASS


def deterministic_sweep():
    C.ISP_BASE = C.ISP_EFFECTIVE
    C.PROP_BASE = C.PROPELLANT_MASS
    base = dict(incl=C.RAIL_INCLINATION, wind10=C.WIND_SPEED_10M, temp_off=0.0,
                pres_f=1.0, mass_scale=1.0, isp_f=1.0, prop_f=1.0,
                drogue_f=1.0, main_alt=C.MAIN_DEPLOY_ALT)
    cases = []
    for incl in (70, 75, 80, 83, 84, 85):
        cases.append(("elewacja %d deg" % incl, dict(base, incl=incl)))
    for w in (0.0, 2.5, 5.0, 10.0, 15.0):
        cases.append(("wiatr %.1f m/s" % w, dict(base, wind10=w)))
    for dt in (-15.0, 0.0, 15.0):
        cases.append(("T ISA %+d K" % dt, dict(base, temp_off=dt)))
    for dp in (0.95, 1.0, 1.05):
        cases.append(("p %.2f x ISA" % dp, dict(base, pres_f=dp)))
    for dm in (0.95, 1.0, 1.05):
        cases.append(("masa sucha %.2f x" % dm, dict(base, mass_scale=dm)))
    for di in (0.98, 1.0, 1.02):
        cases.append(("Isp %.2f x" % di, dict(base, isp_f=di)))
    for dpr in (0.985, 1.0, 1.015):
        cases.append(("paliwo %.3f x" % dpr, dict(base, prop_f=dpr)))

    rows = []
    for name, kw in cases:
        args = (kw["incl"], kw["wind10"], kw["temp_off"], kw["pres_f"],
                kw["mass_scale"], kw["isp_f"], kw["prop_f"], kw["drogue_f"],
                kw["main_alt"])
        m = _run_case(args)
        rows.append((name, m))
        print(f"{name:22s} apogeum={m['apogee']:7.0f} m  v_rail={m['v_rail']:5.1f}  "
              f"SMmin={m['sm_min']:4.2f}  touchdown={m['touchdown']:4.1f}  "
              f"drift={m['drift']:5.0f}")
    return rows


def monte_carlo(n=48, seed=42):
    rng = np.random.default_rng(seed)
    C.ISP_BASE = C.ISP_EFFECTIVE
    C.PROP_BASE = C.PROPELLANT_MASS
    jobs = []
    for _ in range(n):
        jobs.append((
            float(rng.normal(84.0, 0.5)),            # elewacja (tolerancja operatora)
            float(rng.uniform(0.0, 10.0)),           # wiatr 10 m
            float(rng.normal(0.0, 7.0)),             # dT od ISA
            float(rng.normal(1.0, 0.015)),           # dp od ISA
            float(rng.normal(1.0, 0.025)),           # masa sucha
            float(rng.normal(1.0, 0.015)),           # Isp
            float(rng.normal(1.0, 0.010)),           # masa paliwa
            float(rng.normal(1.0, 0.05)),            # CdS drogue
            float(rng.uniform(350.0, 450.0)),        # wysokosc main
        ))
    with ProcessPoolExecutor(max_workers=2, initializer=_init_worker) as ex:
        res = list(ex.map(_run_case, jobs))
    return res, jobs


def main():
    n_mc = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    rows = deterministic_sweep()
    with open(os.path.join(OUT, "sensitivity_deterministic.csv"), "w") as f:
        f.write("case,apogee_m,v_rail_m_s,sm_min_cal,touchdown_m_s,drift_m\n")
        for name, m in rows:
            f.write(f"{name},{m['apogee']:.0f},{m['v_rail']:.2f},{m['sm_min']:.2f},"
                    f"{m['touchdown']:.2f},{m['drift']:.0f}\n")

    # tornado: wplyw na apogeum
    base_ap = [m["apogee"] for name, m in rows if name == "elewacja 84 deg"][0]
    fig, ax = plt.subplots(figsize=(9, 6))
    names, dvals = [], []
    for name, m in rows:
        names.append(name)
        dvals.append(m["apogee"] - base_ap)
    order = np.argsort(np.abs(dvals))
    ax.barh([names[i] for i in order], [dvals[i] for i in order], color="steelblue")
    ax.set_xlabel("delta apogeum wzgledem przypadku bazowego [m]")
    ax.grid(alpha=0.3, axis="x")
    ax.set_title("Wrazliwosc apogeum na parametry (sweep deterministyczny)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "09_sensitivity_tornado.png"), dpi=130)
    plt.close(fig)

    print(f"\nMonte Carlo N={n_mc} ...")
    res, jobs = monte_carlo(n_mc)
    ap = np.array([r["apogee"] for r in res])
    vr = np.array([r["v_rail"] for r in res])
    sm = np.array([r["sm_min"] for r in res])
    td = np.array([r["touchdown"] for r in res])
    am = np.array([r["alt_main"] for r in res])
    dr = np.array([r["drift"] for r in res])

    def stat(x, label):
        print(f"{label:26s} mean={np.mean(x):8.1f}  p5={np.percentile(x,5):8.1f}  "
              f"p95={np.percentile(x,95):8.1f}  min={np.min(x):8.1f}  max={np.max(x):8.1f}")

    stat(ap, "apogeum AGL [m]")
    stat(vr, "v zejscia z szyny [m/s]")
    stat(sm, "SM min [cal]")
    stat(td, "przyziemienie [m/s]")
    stat(am, "wysokosc main [m]")
    stat(dr, "dryf [m]")
    n_fail_ap = int(np.sum(np.abs(ap - C.TARGET_APOGEE_AGL) > 0.05 * C.TARGET_APOGEE_AGL))
    n_fail_vr = int(np.sum(vr <= C.LIMIT_RAIL_EXIT_V))
    n_fail_sm = int(np.sum(sm < C.LIMIT_MARGIN_MIN))
    n_fail_td = int(np.sum(td >= C.LIMIT_TOUCHDOWN_V))
    n_fail_am = int(np.sum(am > C.LIMIT_MAIN_ALT))
    print(f"FAIL: apogeum poza ±5%: {n_fail_ap}/{n_mc} | v_rail<=30: {n_fail_vr} | "
          f"SM<1.5: {n_fail_sm} | touchdown>=9: {n_fail_td} | main>450: {n_fail_am}")

    arr = np.column_stack([ap, vr, sm, td, am, dr])
    np.savetxt(os.path.join(OUT, "monte_carlo_results.csv"), arr, delimiter=",",
               header="apogee_m,v_rail_m_s,sm_min_cal,touchdown_m_s,alt_main_m,drift_m",
               comments="")

    fig, axs = plt.subplots(2, 2, figsize=(11, 8))
    axs[0, 0].hist(ap, bins=15, color="steelblue")
    axs[0, 0].axvline(C.TARGET_APOGEE_AGL, color="g", ls="--", label="cel 9000 m")
    axs[0, 0].set_title(f"apogeum AGL (mean {np.mean(ap):.0f} m)")
    axs[0, 0].set_xlabel("apogeum AGL [m]")
    axs[0, 0].set_ylabel("liczba realizacji")
    axs[0, 0].legend(loc="upper right")
    axs[0, 1].hist(vr, bins=15, color="orange")
    axs[0, 1].axvline(C.LIMIT_RAIL_EXIT_V, color="r", ls="--", label="limit 30 m/s")
    axs[0, 1].set_title("predkosc zejscia z szyny")
    axs[0, 1].set_xlabel("v_rail [m/s]")
    axs[0, 1].set_ylabel("liczba realizacji")
    axs[0, 1].legend(loc="upper left")
    axs[1, 0].hist(td, bins=15, color="green")
    axs[1, 0].axvline(C.LIMIT_TOUCHDOWN_V, color="r", ls="--", label="limit 9 m/s")
    axs[1, 0].set_title("predkosc przyziemienia")
    axs[1, 0].set_xlabel("v_przyziemienia [m/s]")
    axs[1, 0].set_ylabel("liczba realizacji")
    axs[1, 0].legend(loc="upper right")
    axs[1, 1].scatter([j[1] for j in jobs], ap, s=12)
    axs[1, 1].set_xlabel("wiatr 10 m [m/s]")
    axs[1, 1].set_ylabel("apogeum [m]")
    for a in axs.flat:
        a.grid(alpha=0.3)
    fig.suptitle(f"Monte Carlo N={n_mc}")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "10_monte_carlo.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
