# -*- coding: utf-8 -*-
"""
Konfiguracja projektu symulacyjnego rakiety AGH Space Systems - kategoria EuRoC L9
(Liquid 9 km).  Wszystkie parametry w jednostkach SI, chyba ze zaznaczono inaczej.

Kazdy parametr opatrzono komentarzem z uzasadnieniem oraz - tam gdzie to mozliwe -
odwolaniem do wymogu regulaminu EuRoC:
  [CR]  PTS_EDU_EuRoC_ST_001905 Competition Rules v1.1
  [SRD] PTS_EDU_EuRoC_ST_001928 System Requirements Document v1.1

Zasada "czarnej skrzynki": podzespoly modelujemy wylacznie przez makroparametry
wplywajace na tor lotu (masa, ciag, opor, punkt wyzwolenia), bez implementacji
elektroniki, zaworow, ladunkow pirotechnicznych itd.
"""

# -----------------------------------------------------------------------------
# 1. MIEJSCE I CZAS STARTU (Srodowisko)
# -----------------------------------------------------------------------------
# Poligon Santa Margarida k. Constancii (Portugalia) - miejsce startow EuRoC
# od edycji 2021.  Wspolrzedne GPS brygady zmechanizowanej (zrodlo: Exercito
# Portugues); wysokosc terenu z API open-elevation (~151 m n.p.m.).
SITE_LATITUDE = 39.417582      # [deg N]
SITE_LONGITUDE = -8.292971     # [deg E]
SITE_ELEVATION = 150.0         # [m n.p.m.]
LAUNCH_DATE = (2026, 10, 18, 10)   # okno startowe EuRoC 2026: 17-20.10.2026
TIMEZONE = "Europe/Lisbon"

# Kierunek azymutu korytarza balistycznego EuRoC: 133 deg (zgodnie z DTEG)
LAUNCH_HEADING = 133.0         # [deg] od polnocy
# [SRD EuRoC-LV-RQT-1000] elewacja nominalna 84 +/- 1 deg (zakres regulacji 70-85)
RAIL_INCLINATION = 84.0        # [deg] nad horizontem (konwencja RocketPy = elewacja)
RAIL_LENGTH = 12.0             # [m] [SRD Appendix I: szyna 12 m, profil Kanya 50x50]
# [SRD RQT-1100] zejscie z szyny = chwila, w ktorej OSTATNIA prowadnica PRZED
# CG traci kontakt z szyna. Górna prowadnica siedzi 3.0 m od ogona, wiec
# efektywna droga rozpedzania = 12 - 3.0 = 9.0 m. RocketPy z rail_length=12
# konczy faze szynowa dokladnie w tym momencie (patrz rocket_model.run_flight).
RAIL_BUTTON_SPAN = 1.95        # [m] rozstaw prowadnic na korpusie
# Efektywna dlugosc prowadzenia = RAIL_LENGTH - odleglosc dolnej prowadnicy od
# konca szyny (przyjecie: dolna prowadnica zjezdza z szyny ~0.8 m przed jej koncem)

# -----------------------------------------------------------------------------
# 2. NAPED - silnik cieczowy LOX / etanol (cisnieniowy)
#    [SRD EuRoC-LV-RQT-0010]_materialy_pedne nietoksyczne: LOX i etanol sa wprost
#    wymienione jako nietoksyczne.  [CR 4.3] impuls calkowity <= 40 960 Ns.
# -----------------------------------------------------------------------------
PROPELLANT_OX = "LOX"
PROPELLANT_FUEL = "Etanol (96%)"
OF_RATIO = 1.25                # [-] stosunek utleniacz/paliwo (typ. 1.2-1.3 dla EtOH)
ISP_EFFECTIVE = 205.0          # [s] efektywny impuls wlasciwy (poz. morza),
                               #     realny dla studenckich silnikow LOX/EtOH
                               #     cisnieniowych (ok. 180-220 s)
PROPELLANT_MASS = 19.5         # [kg] calkowita masa materialow pednych (LOX+EtOH)
BURN_TIME = 11.5                # [s] czas pracy silnika (zaplon -> MECO)
THRUST_PEAK = 5200.0           # [N] maksymalny ciag na plyto
THRUST_TAIL_START = 10.6        # [s] poczatek wygaszania (zamkniecie zaworow)
HOLD_DOWN_RELEASE_FRACTION = 0.75   # [-] prog zwolnienia hold-down jako ulamek
                               #     ciagu plyto: F_release = 0.75 * THRUST_PEAK
                               #     [SRD EuRoC-LV-RQT-1020]
HOLD_DOWN_RAMP_TIME = 0.25      # [s] czas narastania ciagu 0 -> ~THRUST_PEAK

# -----------------------------------------------------------------------------
# 3. GEOMETRIA I MASY rakiety (bez silnika - patrz motor_model)
# -----------------------------------------------------------------------------
BODY_RADIUS = 0.100            # [m] kaliber 200 mm
ROCKET_LENGTH = 3.90           # [m] dlugosc calkowita (bez silnika wystajacego)
NOSE_LENGTH = 0.85             # [m] glowica von Karman
NOSE_KIND = "vonKarman"

# Stateczniki - punkt wyjscia do optymalizacji (analiza stabilnosci)
FIN_COUNT = 4
FIN_ROOT_CHORD = 0.50          # [m]
FIN_TIP_CHORD = 0.18           # [m]
FIN_SPAN = 0.11                # [m] (0.8 kalibra)
FIN_SWEEP = 0.20               # [m]
FIN_POSITION = 0.50            # [m] od poczatku ukladu (ogon)
FIN_THICKNESS = 0.008          # [m] do analizy flutteru
FIN_MATERIAL_G = 6.9e9         # [Pa] modul Kirchoffa laminatu CFRP (os 45 deg)

# Rozklad mas rakiety BEZ silnika (RocketPy: Rocket.mass)
MASS_STRUCTURE = 11.0          # [kg] korpus, przedzialy, mocowania, izolacja
MASS_AVIONICS = 3.2            # [kg] redundatne altimetry, telemetria, GPS
MASS_RECOVERY = 4.5            # [kg] spadochrony, mozdzierze/ladunki, uprzaz
MASS_PAYLOAD = 1.10            # [kg] [SRD RQT-0860: >=1.0 kg; RQT-0870: CubeSat 1.0-1.33 kg]
MASS_MISC = 2.0                # [kg] wiazki, akumulatory, drobiazgi
ROCKET_MASS = MASS_STRUCTURE + MASS_AVIONICS + MASS_RECOVERY + MASS_PAYLOAD + MASS_MISC

# --- SILNIK (masa sucha i bezwladnosci - patrz motor_model) ------------------
MOTOR_DRY_MASS = 17.5          # [kg] komora+wtryskiwacz 6.5, zbiorniki+He 8.0,
                               #     zawory/orurowanie 3.0
MOTOR_I11 = 11.5               # [kg*m^2]
MOTOR_I33 = 0.09               # [kg*m^2]
MOTOR_COM_POSITION = 1.30      # [m] srodek masy suchego silnika od ogona
TANK_LOX_POSITION = 1.95       # [m] dol zbiornika LOX (uklad silnika)
TANK_LOX_HEIGHT = 0.46         # [m]
TANK_LOX_RADIUS = 0.088        # [m]
TANK_ETOH_POSITION = 1.40      # [m] dol zbiornika etanolu
TANK_ETOH_HEIGHT = 0.50        # [m]
TANK_ETOH_RADIUS = 0.090       # [m]

# Polozenie srodka masy rakiety bez silnika (ciezkie: payload+awionika z przodu)
COM_WITHOUT_MOTOR = 2.50       # [m] od ogona (uklad tail_to_nose)
# Tensor momentow bezwladnosci rakiety bez silnika (I11, I22, I33) [kg*m^2]
INERTIA_WITHOUT_MOTOR = (32.0, 32.0, 0.13)

# -----------------------------------------------------------------------------
# 4. AERODYNAMIKA - wspolczynnik oporu Cd(Mach) (oszacowanie analityczne,
#    punkt wyjscia zamiast CFD; zob. README - ograniczenia)
# -----------------------------------------------------------------------------
DRAG_MACH = [0.0, 0.6, 0.8, 0.9, 1.0, 1.1, 1.3, 1.6, 2.0, 2.5, 3.0]
DRAG_CD_OFF = [0.28, 0.28, 0.30, 0.36, 0.48, 0.52, 0.49, 0.44, 0.39, 0.36, 0.34]
DRAG_CD_ON = [0.26, 0.26, 0.28, 0.34, 0.45, 0.49, 0.46, 0.41, 0.37, 0.34, 0.32]

# -----------------------------------------------------------------------------
# 5. SYSTEM ODZYSKU - dual deployment
#    [SRD RQT-0350] drogue na apogeum; [RQT-0360] 23-46 m/s; [RQT-0370] main
#    <= 450 m AGL; [RQT-0380] przyziemienie < 9 m/s.
# -----------------------------------------------------------------------------
DROGUE_CD_S = 1.00             # [m^2] Cd*A spadochronu wstepnego (dobrane analiza)
DROGUE_CD = 0.80               # [-] Cd czaszy stozkowej -> A = 1.25 m^2, D ~ 1.26 m
DROGUE_LAG = 0.7               # [s] czas napelniania
MAIN_CD_S = 11.4               # [m^2] Cd*A czaszy glownej (dobrane analiza)
MAIN_CD = 1.40                 # [-] Cd czaszy okraglej -> A = 8.14 m^2, D ~ 3.22 m
MAIN_DEPLOY_ALT = 400.0        # [m AGL] < 450 m z zapasem [SRD RQT-0370]
MAIN_LAG = 1.2                 # [s] czas napelniania

# -----------------------------------------------------------------------------
# 6. ATMOSFERA / WIATR - profil bazowy i zakresy do analiz wrazliwosci
# -----------------------------------------------------------------------------
WIND_SPEED_10M = 5.0           # [m/s] wiatr przyziemny (bazowy, pazdziernik PT)
WIND_POWER_EXP = 0.14          # [-] wykladnik prawa potegowego (warstwa graniczna)
WIND_TOP_SPEED_FACTOR = 2.2    # [-] mnoznik predkosci na 9 km (prad strumieniowy)
TEMP_OFFSET_ISA = 0.0          # [K] odchyłka od ISA (bazowo 0)
PRESSURE_FACTOR = 1.0          # [-] mnoznik cisnienia (bazowo 1)

# -----------------------------------------------------------------------------
# 7. LIMITY REGULAMINOWE (do raportu zgodnosci)
# -----------------------------------------------------------------------------
LIMIT_TOTAL_IMPULSE = 40960.0  # [Ns]  [CR 4.3]
TARGET_APOGEE_AGL = 9000.0     # [m]   [CR 4.1] kategoria L9
LIMIT_RAIL_EXIT_V = 30.0       # [m/s] [SRD RQT-1100]
LIMIT_MARGIN_MIN = 1.5         # [cal] [SRD RQT-1030]
LIMIT_MARGIN_MAX = 6.0         # [cal] [SRD RQT-1030 nota: unikac nadstatecznosci]
LIMIT_DROGUE_V_MIN = 23.0      # [m/s] [SRD RQT-0360]
LIMIT_DROGUE_V_MAX = 46.0      # [m/s] [SRD RQT-0360]
LIMIT_MAIN_ALT = 450.0         # [m]   [SRD RQT-0370]
LIMIT_TOUCHDOWN_V = 9.0        # [m/s] [SRD RQT-0380]
LIMIT_PAYLOAD_MIN = 1.0        # [kg]  [SRD RQT-0860]
