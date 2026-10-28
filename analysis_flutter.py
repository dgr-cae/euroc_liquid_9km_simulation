# -*- coding: utf-8 -*-
"""
Analiza flutteru statecznikow (dodatkowa, poza wymogiem regulaminowym).

Kryterium Martina (NACA TN 4197, 1958, rown. 18) w postaci SKORYGOWANEJ
o czynnik sqrt(2) (J.K. Bennett, Apogee Peak of Flight #615, XII 2023;
por. RocketPy issue #1200 - wbudowana funkcja rocketpy zawyzza wynik o sqrt(2)):

    V_f = a * sqrt( 2 * G * (t/c)^3 * (AR + 2) / (1.337 * AR^3 * (lambda + 1) * P) )

gdzie: a - predkosc dzwieku na danej wysokosci, P - cisnienie statyczne,
G - modul scinania materialu, AR = b^2/S (b - polrozpietosc), lambda = ct/cr,
t/c - grubosc wzgledna (do cieciwy podstawy).

Sprawdzenie: V_f(z(q_max)) vs V_lot(z(q_max)) oraz zapas >= 1.5 (dla lotu
naddzwiekowego zalecane >= 2).

Uzycie: python analysis_flutter.py
"""
import os

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


def flutter_velocity(G, thickness, root_chord, tip_chord, span, pressure, a_sound):
    b = span / 2.0                      # polrozpietosc (fin poza korpusem)
    S = 0.5 * (root_chord + tip_chord) * b
    AR = b ** 2 / S
    lam = tip_chord / root_chord
    tc = thickness / root_chord
    vf = a_sound * np.sqrt(
        2 * G * tc ** 3 * (AR + 2) / (1.337 * AR ** 3 * (lam + 1) * pressure)
    )
    return vf, AR


def main():
    motor, _ = MM.build_motor()
    rocket = RM.build_rocket(motor)
    flight = RM.run_flight(rocket, EM.make_environment())   # pelny lot
    env = flight.env

    sol = flight.solution_array
    t = sol[:, 0]
    z_agl = sol[:, 3] - C.SITE_ELEVATION
    v = np.sqrt(sol[:, 4]**2 + sol[:, 5]**2 + sol[:, 6]**2)
    # q(t) liczone jawnie z gestosci i predkosci (niezaleznie od atrybutow Flight)
    rho = np.array([float(env.density(zz)) for zz in sol[:, 3]])
    q = 0.5 * rho * v ** 2
    i_t = int(np.argmax(q))
    dq, tq = float(q[i_t]), float(t[i_t])
    z_q, v_q = float(z_agl[i_t]), float(v[i_t])
    p_q = float(env.pressure(sol[i_t, 3]))
    a_q = float(env.speed_of_sound(sol[i_t, 3]))

    print(f"q_max = {dq/1000:.1f} kPa przy t = {tq:.2f} s, z = {z_q:.0f} m AGL, "
          f"V = {v_q:.0f} m/s, P = {p_q/1000:.1f} kPa, a = {a_q:.0f} m/s")

    rows = []
    for thk in (0.005, 0.006, 0.008, 0.010, 0.012):
        vf, AR = flutter_velocity(C.FIN_MATERIAL_G, thk, C.FIN_ROOT_CHORD,
                                  C.FIN_TIP_CHORD, C.FIN_SPAN, p_q, a_q)
        margin = vf / v_q
        rows.append((thk * 1000, vf, margin))
        tag = "  <-- baza" if abs(thk - C.FIN_THICKNESS) < 1e-9 else ""
        print(f"  grubosc {thk*1000:4.1f} mm: V_flutter = {vf:6.0f} m/s, "
              f"zapas V_f/V = {margin:4.2f}{tag}")

    # profil V_flutter vs wysokosc (cisnienie spada -> V_f rosnie)
    zz = np.linspace(0, 9000, 60)
    pp = np.array([float(env.pressure(z + C.SITE_ELEVATION)) for z in zz])
    aa = np.array([float(env.speed_of_sound(z + C.SITE_ELEVATION)) for z in zz])
    vf_prof = np.array([flutter_velocity(C.FIN_MATERIAL_G, C.FIN_THICKNESS,
                                         C.FIN_ROOT_CHORD, C.FIN_TIP_CHORD,
                                         C.FIN_SPAN, p, a)[0]
                        for p, a in zip(pp, aa)])
    v_at_z = np.array([float(v[np.argmin(np.abs(z_agl - z))]) for z in zz])

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(vf_prof, zz, "r", label="V_flutter (NACA TN 4197, skorygowane)")
    ax.plot(v_at_z, zz, "b", label="predkosc lotu V(z)")
    ax.axhline(z_q, color="gray", ls=":", label=f"z(q_max) = {z_q:.0f} m")
    ax.set_xlabel("predkosc [m/s]")
    ax.set_ylabel("z [m AGL]")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_title("Flutter statecznikow: granica vs predkosc lotu")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "11_fin_flutter.png"), dpi=130)
    plt.close(fig)

    with open(os.path.join(OUT, "flutter_analysis.csv"), "w") as f:
        f.write("thickness_mm,V_flutter_m_s,margin_at_qmax\n")
        for r in rows:
            f.write(f"{r[0]:.1f},{r[1]:.0f},{r[2]:.2f}\n")


if __name__ == "__main__":
    main()
