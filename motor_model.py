# -*- coding: utf-8 -*-
"""
Model napedu cieczowego (LOX / etanol) w konwencji "czarnej skrzynki":
silnik definiuja wylacznie (1) masa poczatkowa materialow pednych,
(2) krzywa ciagu, (3) zmiana masy w czasie (mdot = F / ve).

Implementacja hold-down [SRD EuRoC-LV-RQT-1020]:
  Fizycznie silnik zapala w T_ign = 0 i buduje ciag pod przytrzymaniem.
  Rakieta rusza dopiero, gdy ciag przekroczy prog zwolnienia F_release.
  RocketPy w fazie szynowej sam utrzymuje rakiete w spoczynku, dopoki
  wypadkowa sila wzdluz szyny jest <= 0 (udot_rail1: `if a3 > 0`).
  Aby prog zwolnienia byl dokladnie F_release (a nie skladowa ciezaru),
  krzywa ciagu przekazana do calkowania jest scieta: dla t < t_release
  F_dyn = min(F, 0.98 * W_rail), a w t_release nastepuje skok do F_release.
  "Brakujacy" ciag miedzy W_rail a F_release przejmuja szczeki hold-down -
  identycznie jak w rzeczywistym ukladzie.  Impuls calkowity raportujemy
  z PELNEJ krzywej (konserwatywnie).
"""
import numpy as np
import rocketpy as rp
from rocketpy.motors.tank import MassFlowRateBasedTank
from rocketpy.motors.tank_geometry import TankGeometry

import config as C

G0 = 9.80665
def _integrate(y, x):
    """Calka metoda trapezow, odporna na wersje numpy:
    numpy < 2.0 ma np.trapz, numpy >= 2.0 ma np.trapezoid."""
    fn = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
    if fn is None:
        return float(np.sum(0.5 * (y[1:] + y[:-1]) * np.diff(x)))
    return float(fn(y, x))

def _thrust_shape(n=400):
    """Bezwymiarowy ksztalt krzywej ciagu (szczyt ~1): narastanie ~0.6 s,
    plyto z lagodnym spadkiem (spadek cisnienia butli He), wygaszanie
    po zamknieciu zaworow - profil typowy dla silnika cisnieniowego."""
    t = np.linspace(0.0, C.BURN_TIME, n)
    f = np.zeros_like(t)
    t_ramp = C.HOLD_DOWN_RAMP_TIME
    t_tail = C.THRUST_TAIL_START
    for i, ti in enumerate(t):
        if ti < t_ramp:                       # narastanie (pod hold-down)
            f[i] = (ti / t_ramp) ** 1.2
        elif ti < t_tail:                     # plyto: lekki nadwyzkowy poczatek
            f[i] = 1.25 - 0.34 * (ti - t_ramp) / (t_tail - t_ramp)
        else:                                 # wygaszanie (zamkniecie zaworow)
            f[i] = 0.91 * max(0.0, 1 - (ti - t_tail) / (C.BURN_TIME - t_tail)) ** 1.3
    return np.column_stack([t, f])


def full_thrust_curve(prop_mass=None, isp=None, thrust_scale=1.0, n=400):
    """Pelna krzywa ciagu [s, N], znormalizowana tak, by impuls calkowity
    wynosil dokladnie I = ve * m_prop * thrust_scale (spojnosc masy i ciagu)."""
    prop_mass = C.PROPELLANT_MASS if prop_mass is None else prop_mass
    isp = C.ISP_EFFECTIVE if isp is None else isp
    ve = isp * G0
    shape = _thrust_shape(n)
    scale = ve * prop_mass * thrust_scale / _integrate(shape[:, 1], shape[:, 0])
    curve = shape.copy()
    curve[:, 1] *= scale
    return curve


def release_time(curve):
    """Czas osiagniecia progu zwolnienia hold-down F_release."""
    f_rel = C.HOLD_DOWN_RELEASE_FRACTION * float(curve[:, 1].max())
    t, f = curve[:, 0], curve[:, 1]
    idx = np.argmax(f >= f_rel)
    return float(t[idx]), f_rel


def hold_down_clipped_curve(curve, m_wet, inclination_deg):
    """Krzywa ciagu 'widziana' przez dynamike po uwzglednieniu hold-down."""
    t_rel, f_rel = release_time(curve)
    w_rail = m_wet * G0 * np.sin(np.radians(inclination_deg))
    cap = 0.98 * w_rail
    out = []
    for ti, fi in curve:
        if ti < t_rel:
            out.append([ti, min(fi, cap)])
        else:
            out.append([ti, fi])
    # punkt tuz przed skokiem, zeby interpolacja nie rozmywala zwolnienia
    out.append([t_rel - 1e-4, cap])
    out = np.array(sorted(out, key=lambda r: r[0]))
    return out, t_rel, f_rel, w_rail


def build_motor(m_wet=None, inclination_deg=None, prop_mass=None, thrust_scale=1.0,
                isp=None):
    """Zwraca (LiquidMotor, dict z danymi pomocniczymi)."""
    m_wet = m_wet or _wet_mass()
    inclination_deg = inclination_deg if inclination_deg is not None else C.RAIL_INCLINATION
    prop_mass = prop_mass if prop_mass is not None else C.PROPELLANT_MASS
    isp = isp or C.ISP_EFFECTIVE
    ve = isp * G0                                  # [m/s] efektywna predkosc wypywu
    # 1% zatankowanego paliwa pozostaje niewykorzystana (resztki niedostepne
    # dla instalacji - ullage/sump); impuls liczymy z masy rzeczywiscie spalonej
    usable_fraction = 0.99
    m_cons = prop_mass * usable_fraction * thrust_scale

    curve = full_thrust_curve(prop_mass=m_cons, isp=isp, thrust_scale=1.0)
    clipped, t_rel, f_rel, w_rail = hold_down_clipped_curve(curve, m_wet, inclination_deg)

    total_impulse = _integrate(curve[:, 1], curve[:, 0])         # pelna krzywa
    mdot_curve = curve.copy()
    mdot_curve[:, 1] = curve[:, 1] / ve                           # [kg/s]

    # --- zbiorniki (czarna skrzynka: tylko masa i mdot w czasie) -------------
    m_ox = prop_mass * C.OF_RATIO / (1 + C.OF_RATIO)
    m_fu = prop_mass - m_ox
    flux = (0.0, C.BURN_TIME)

    def _tank(name, m0, share, density, radius, height, bottom):
        # mdot kazdego zbiornika proporcjonalny do krzywej ciagu
        mdot_out = mdot_curve.copy()
        mdot_out[:, 1] = mdot_curve[:, 1] * share
        geo = TankGeometry({(0.0, height): lambda h: radius})
        return MassFlowRateBasedTank(
            name=name,
            geometry=geo,
            flux_time=flux,
            liquid=rp.Fluid(name=name + "_liq", density=density),
            gas=rp.Fluid(name=name + "_gas", density=1.0),
            initial_liquid_mass=m0,
            initial_gas_mass=0.0,
            liquid_mass_flow_rate_in=0.0,
            gas_mass_flow_rate_in=0.0,
            liquid_mass_flow_rate_out=mdot_out,
            gas_mass_flow_rate_out=0.0,
            discretize=200,
        )

    # zbiorniki cylindryczne; position = dol zbiornika w ukladzie silnika
    tank_lox = _tank("LOX", m_ox, m_ox / prop_mass, 1141.0,
                     C.TANK_LOX_RADIUS, C.TANK_LOX_HEIGHT, C.TANK_LOX_POSITION)
    tank_etoh = _tank("EtOH", m_fu, m_fu / prop_mass, 800.0,
                      C.TANK_ETOH_RADIUS, C.TANK_ETOH_HEIGHT, C.TANK_ETOH_POSITION)

    motor = rp.LiquidMotor(
        thrust_source=clipped,
        dry_mass=C.MOTOR_DRY_MASS,
        dry_inertia=(C.MOTOR_I11, C.MOTOR_I11, C.MOTOR_I33),
        nozzle_radius=0.062,
        center_of_dry_mass_position=C.MOTOR_COM_POSITION,
        nozzle_position=0.0,
        burn_time=(0.0, C.BURN_TIME),
    )
    motor.add_tank(tank_lox, position=C.TANK_LOX_POSITION)
    motor.add_tank(tank_etoh, position=C.TANK_ETOH_POSITION)

    info = {
        "curve_full": curve,
        "curve_dyn": clipped,
        "mdot_curve": mdot_curve,
        "total_impulse": total_impulse,
        "ve": ve,
        "t_release": t_rel,
        "f_release": f_rel,
        "w_rail": w_rail,
        "m_ox": m_ox,
        "m_fu": m_fu,
        "prop_mass": prop_mass,
        "thrust_scale": thrust_scale,
        "isp": isp,
    }
    return motor, info


def _wet_mass():
    return C.ROCKET_MASS + C.MOTOR_DRY_MASS + C.PROPELLANT_MASS
