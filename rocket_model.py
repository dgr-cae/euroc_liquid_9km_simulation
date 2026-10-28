# -*- coding: utf-8 -*-
"""
Model platowca rakiety L9: korpus 200 mm, glowica von Karman, 4 stateczniki
trapezowe, prowadnice szynowe, dwojstopniowy system odzysku (dual deployment).
"""
import numpy as np
import rocketpy as rp

import config as C
import motor_model as MM


def drag_curve(cd_list):
    return rp.Function(
        np.column_stack([C.DRAG_MACH, cd_list]),
        inputs="Mach",
        outputs="Drag Coefficient",
        interpolation="linear",
        extrapolation="constant",
    )


def build_rocket(motor, fin_span=None, fin_root=None, fin_tip=None, fin_n=None,
                 mass_scale=1.0, com_shift=0.0, drogue_cd_s=None, main_cd_s=None,
                 main_alt=None):
    """Buduje obiekt RocketPy.Rocket wraz z systemem odzysku.

    Parametry opcjonalne sluza do analiz parametrycznych (stateczniki, masy,
    wielkosci spadochronow).
    """
    fin_span = C.FIN_SPAN if fin_span is None else fin_span
    fin_root = C.FIN_ROOT_CHORD if fin_root is None else fin_root
    fin_tip = C.FIN_TIP_CHORD if fin_tip is None else fin_tip
    fin_n = C.FIN_COUNT if fin_n is None else fin_n
    drogue_cd_s = C.DROGUE_CD_S if drogue_cd_s is None else drogue_cd_s
    main_cd_s = C.MAIN_CD_S if main_cd_s is None else main_cd_s
    main_alt = C.MAIN_DEPLOY_ALT if main_alt is None else main_alt

    mass = C.ROCKET_MASS * mass_scale
    inertia = tuple(np.array(C.INERTIA_WITHOUT_MOTOR) * mass_scale)

    rocket = rp.Rocket(
        radius=C.BODY_RADIUS,
        mass=mass,
        inertia=inertia,
        power_off_drag=drag_curve(C.DRAG_CD_OFF),
        power_on_drag=drag_curve(C.DRAG_CD_ON),
        center_of_mass_without_motor=C.COM_WITHOUT_MOTOR + com_shift,
        coordinate_system_orientation="tail_to_nose",
    )

    rocket.add_motor(motor, position=0.0)

    rocket.add_nose(length=C.NOSE_LENGTH, kind=C.NOSE_KIND,
                    position=C.ROCKET_LENGTH)

    rocket.add_trapezoidal_fins(
        n=fin_n,
        root_chord=fin_root,
        tip_chord=fin_tip,
        span=fin_span,
        position=C.FIN_POSITION,
        sweep_length=C.FIN_SWEEP,
    )

    # prowadnice szynowe (rail buttons): dolna tuz nad statecznikami,
    # gorna blisko CG w konfiguracji startowej
    lower = 1.05
    upper = lower + C.RAIL_BUTTON_SPAN
    rocket.set_rail_buttons(upper_button_position=upper,
                            lower_button_position=lower)

    # --- system odzysku ------------------------------------------------------
    # Drogue: wyzwalany na apogeum (vz < 0) - [SRD RQT-0350]
    # Sygnatura triggera RocketPy: (cisnienie [Pa], wysokosc AGL [m], wektor stanu)
    def drogue_trigger(pressure, height, y):
        # wysokosc AGL liczona ze wektora stanu (z - elevacja): odpornosc na
        # blad wysokosci barycznej (patrz README - ograniczenia)
        agl = y[2] - C.SITE_ELEVATION
        return bool(y[5] < 0.0 and agl > 500.0)

    rocket.add_parachute(
        name="Drogue",
        cd_s=drogue_cd_s,
        trigger=drogue_trigger,
        sampling_rate=100,
        lag=C.DROGUE_LAG,
    )

    # Main: wysokosc AGL <= 400 m - [SRD RQT-0370]
    def main_trigger(pressure, height, y):
        agl = y[2] - C.SITE_ELEVATION
        return bool(agl < main_alt and y[5] < 0.0)

    rocket.add_parachute(
        name="Main",
        cd_s=main_cd_s,
        trigger=main_trigger,
        sampling_rate=100,
        lag=C.MAIN_LAG,
    )
    return rocket


def run_flight(rocket, env=None, inclination=None, heading=None,
               terminate_on_apogee=False, max_time=900):
    import environment_model as EM
    env = env or EM.make_environment()
    inclination = C.RAIL_INCLINATION if inclination is None else inclination
    heading = C.LAUNCH_HEADING if heading is None else heading
    flight = rp.Flight(
        rocket=rocket,
        environment=env,
        rail_length=C.RAIL_LENGTH,  # RocketPy konczy faze szynowa, gdy górna
        # prowadnica (3.0 m od ogona) mija koniec szyny 12 m -> droga 9.0 m,
        # czyli dokladnie definicja z [SRD RQT-1100]
        inclination=inclination,
        heading=heading,
        terminate_on_apogee=terminate_on_apogee,
        max_time=max_time,
    )
    return flight
