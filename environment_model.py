# -*- coding: utf-8 -*-
"""
Model srodowiska lotu: atmosfera ISA z mozliwoscia odchylenia temperatury i
cisnienia oraz profilem wiatru (prawo potegowe w warstwie granicznej + wzrost
do poziomu pradu strumieniowego).  Dzieki `custom_atmosphere` te same funkcje
sluza do analiz wrazliwosci (wiatr, temperatura, cisnienie).

UWAGA: wysokosci w profilach RocketPy to wysokosci n.p.m. (ASL), dlatego
profile skladamy z wysokoscia terenu stanowiska.
"""
import numpy as np
import rocketpy as rp

import config as C

# stale atmosfery standardowej (ISA)
_T0, _P0, _L, _G, _R = 288.15, 101325.0, 0.0065, 9.80665, 287.053


def _isa_temperature(h_asl):
    """Temperatura ISA [K] do 11 km (troposfera)."""
    return _T0 - _L * h_asl


def _isa_pressure(h_asl):
    return _P0 * (1 - _L * h_asl / _T0) ** (_G / (_R * _L))


def wind_profile(z_asl, w10):
    """Predkosc wiatru [m/s] vs wysokosc ASL: prawo potegowe do 1 km, wyzej
    liniowy wzrost do wartosci pradu strumieniowego na 9 km."""
    z_agl = np.maximum(z_asl - C.SITE_ELEVATION, 0.0)
    w_bl = w10 * np.maximum(z_agl / 10.0, 1e-3) ** C.WIND_POWER_EXP
    w_top = w10 * C.WIND_TOP_SPEED_FACTOR
    frac = np.clip((z_agl - 1000.0) / 8000.0, 0.0, 1.0)
    return w_bl + (w_top - w_bl) * frac


def make_environment(wind10=None, temp_offset=None, pressure_factor=None,
                     heading_from=None, max_height=20000):
    """Buduje Environment z atmosfera niestandardowa (ISA + odchyki + wiatr).

    heading_from : kierunek, Z KTOREGO wieje wiatr [deg od polnocy]; domyslnie
    270 (wiatr zachodni -> skadowa +U).
    """
    wind10 = C.WIND_SPEED_10M if wind10 is None else wind10
    temp_offset = C.TEMP_OFFSET_ISA if temp_offset is None else temp_offset
    pressure_factor = C.PRESSURE_FACTOR if pressure_factor is None else pressure_factor
    heading_from = 270.0 if heading_from is None else heading_from

    env = rp.Environment(
        latitude=C.SITE_LATITUDE,
        longitude=C.SITE_LONGITUDE,
        elevation=C.SITE_ELEVATION,
        date=C.LAUNCH_DATE,
        timezone=C.TIMEZONE,
        max_expected_height=max_height,
    )

    def temp_f(h):
        return _isa_temperature(h) + temp_offset

    def pres_f(h):
        return _isa_pressure(h) * pressure_factor

    # sklowe wiatru: wiatr Z kierunku heading_from
    hd = np.radians(heading_from)
    wu, wv = -np.sin(hd), -np.cos(hd)   # wektor "dokad wieje" (U=east, V=north)

    def wind_u(h):
        return wind_profile(h, wind10) * wu

    def wind_v(h):
        return wind_profile(h, wind10) * wv

    env.set_atmospheric_model(
        type="custom_atmosphere",
        pressure=pres_f,
        temperature=temp_f,
        wind_u=wind_u,
        wind_v=wind_v,
    )
    return env
