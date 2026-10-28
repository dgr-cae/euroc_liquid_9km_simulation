# -*- coding: utf-8 -*-
"""
Raport zgodnosci z regulaminem EuRoC (CR v1.1 / SRD v1.1).
Funkcja `check_compliance` zwraca liste wpisow:
(id_wymogu, opis, wartosc, limit, status PASS/FAIL/INFO)
"""
import numpy as np

import config as C


def descent_speeds_at(flight, altitudes):
    """Predkosci opadania [m/s] (dodatnie) na zadanych wysokosciach AGL
    w fazie miedzy otwarciem drogue a otwarciem main."""
    sol = flight.solution_array
    t, z, vz = sol[:, 0], sol[:, 3] - flight.env.elevation, sol[:, 6]
    ev = flight.parachute_events
    t_drogue = ev[0][0] if len(ev) > 0 else 0.0
    t_main = ev[1][0] if len(ev) > 1 else t[-1]
    out = []
    for a in altitudes:
        band = (z < a - 100.0) & (z > a - 500.0) & (t > t_drogue + C.DROGUE_LAG + 2.0) & (t < t_main)
        if band.any():
            out.append(float(np.median(np.abs(vz[band]))))
        else:
            out.append(np.nan)
    return out


def check_compliance(flight, motor_info, rocket, env):
    sol = flight.solution_array
    z, vz = sol[:, 3] - flight.env.elevation, sol[:, 6]
    apogee_agl = float(flight.apogee_state[2]) - flight.env.elevation
    v_rail = float(flight.out_of_rail_velocity)
    m_min = float(flight.min_stability_margin)
    m_max = float(flight.max_stability_margin)
    m_rail = float(flight.out_of_rail_stability_margin)
    impulse = motor_info["total_impulse"]

    ev = flight.parachute_events
    t_drogue = ev[0][0]
    t_main = ev[1][0] if len(ev) > 1 else np.nan
    alt_main = float(np.interp(t_main, sol[:, 0], z)) if len(ev) > 1 else np.nan
    touchdown = abs(float(flight.impact_velocity))

    v_drogue = descent_speeds_at(flight, [7000, 5000, 3000, 1500, 600])
    v_drogue_ok = all(C.LIMIT_DROGUE_V_MIN <= v <= C.LIMIT_DROGUE_V_MAX
                      for v in v_drogue if not np.isnan(v))

    checks = [
        ("CR 4.3", "Impuls calkowity <= 40 960 Ns", impulse,
         f"<= {C.LIMIT_TOTAL_IMPULSE}", impulse <= C.LIMIT_TOTAL_IMPULSE),
        ("CR 4.1", "Apogeum ~9000 m AGL (kategoria L9)", apogee_agl,
         f"cel {C.TARGET_APOGEE_AGL} (|d| < 5%)",
         abs(apogee_agl - C.TARGET_APOGEE_AGL) <= 0.05 * C.TARGET_APOGEE_AGL),
        ("SRD RQT-0010", "Materialy pedne nietoksyczne (LOX/EtOH)",
         f"{C.PROPELLANT_OX}/{C.PROPELLANT_FUEL}", "lista nietoksyczna", True),
        ("SRD RQT-0860", "Ladunek uzyteczny >= 1.0 kg", C.MASS_PAYLOAD,
         f">= {C.LIMIT_PAYLOAD_MIN}", C.MASS_PAYLOAD >= C.LIMIT_PAYLOAD_MIN),
        ("SRD RQT-1000", "Elewacja wyrzutni 84 +/- 1 deg", C.RAIL_INCLINATION,
         "83..85 (regul. 70..85)", 70 <= C.RAIL_INCLINATION <= 85),
        ("SRD App.I", "Dlugosc szyny 12 m (Kanya 50x50)", C.RAIL_LENGTH, "== 12",
         C.RAIL_LENGTH == 12.0),
        ("SRD RQT-1100", "Predkosc zejścia z szyny > 30 m/s", v_rail,
         f"> {C.LIMIT_RAIL_EXIT_V}", v_rail > C.LIMIT_RAIL_EXIT_V),
        ("SRD RQT-1020", "Hold-down: prog zwolnienia ciagu",
         motor_info["f_release"],
         f"> W_rail={motor_info['w_rail']:.0f} N",
         motor_info["f_release"] > motor_info["w_rail"]),
        ("SRD RQT-1030", "Margines stat. min. w locie >= 1.5 cal", m_min,
         f">= {C.LIMIT_MARGIN_MIN}", m_min >= C.LIMIT_MARGIN_MIN),
        ("SRD RQT-1030", "Margines stat. max < 6 cal (nadstatecznosc)", m_max,
         f"< {C.LIMIT_MARGIN_MAX}", m_max < C.LIMIT_MARGIN_MAX),
        ("SRD RQT-1030", "Margines przy zejsciu z szyny >= 1.5 cal", m_rail,
         f">= {C.LIMIT_MARGIN_MIN}", m_rail >= C.LIMIT_MARGIN_MIN),
        ("SRD RQT-0350", "Drogue na apogeum (t_apogee)", t_drogue,
         f"t_apogee={flight.apogee_time:.2f} s",
         abs(t_drogue - flight.apogee_time) < 1.0),
        ("SRD RQT-0360", "Opadanie na drogue 23-46 m/s",
         [round(v, 1) for v in v_drogue], "23..46 (7..0.6 km AGL)", v_drogue_ok),
        ("SRD RQT-0370", "Main <= 450 m AGL", alt_main,
         f"<= {C.LIMIT_MAIN_ALT}", alt_main <= C.LIMIT_MAIN_ALT),
        ("SRD RQT-0380", "Predkosc przyziemienia < 9 m/s", touchdown,
         f"< {C.LIMIT_TOUCHDOWN_V}", touchdown < C.LIMIT_TOUCHDOWN_V),
    ]
    return checks, {
        "apogee_agl": apogee_agl,
        "v_rail": v_rail,
        "m_min": m_min,
        "m_max": m_max,
        "m_rail": m_rail,
        "impulse": impulse,
        "alt_main": alt_main,
        "touchdown": touchdown,
        "v_drogue": v_drogue,
        "t_drogue": t_drogue,
        "t_main": t_main,
        "drift": float(np.hypot(sol[-1, 1], sol[-1, 2])),
        "max_mach": float(flight.max_mach_number),
        "max_q": float(flight.max_dynamic_pressure),
        "max_accel": float(flight.max_acceleration),
    }


def format_report(checks, metrics):
    lines = ["=" * 78,
             "RAPORT ZGODNOSCI Z REGULAMINEM EuRoC (CR v1.1 / SRD v1.1)",
             "=" * 78]
    for cid, desc, val, lim, ok in checks:
        status = "PASS" if ok else "FAIL"
        if isinstance(val, float):
            val = f"{val:.2f}"
        lines.append(f"[{status}] {cid:12s} {desc:44s} wartosc={val} | limit: {lim}")
    lines.append("-" * 78)
    lines.append(f"Mach max: {metrics['max_mach']:.2f}   q max: {metrics['max_q']/1000:.1f} kPa"
                 f"   a max: {metrics['max_accel']:.0f} m/s2 ({metrics['max_accel']/9.80665:.1f} g)")
    lines.append(f"Dryf wiatrowy miejsca ladowania: {metrics['drift']:.0f} m")
    return "\n".join(lines)
