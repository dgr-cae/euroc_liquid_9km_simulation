# Symulacja trajektorii rakiety AGH Space Systems — kategoria EuRoC **L9 (Liquid 9 km)**

Projekt rekrutacyjny (Zespół Symulacji AGH Space Systems 2026): kompletny model
symulacyjny rakiety na paliwo ciekłe w **RocketPy 1.13**, zbudowany w oparciu o:

* *Competition Rules* EuRoC — PTS_EDU_EuRoC_ST_001905, issue 1.1 (`CR`),
* *System Requirements Document* EuRoC — PTS_EDU_EuRoC_ST_001928, issue 1.1 (`SRD`),
* założenia własne (`zalozenia.txt` / `zalozenia2.txt`) — zasada „czarnej skrzynki".

## 1. Wymagania regulaminowe uwzględnione w modelu

| # | Wymóg (źródło) | Treść | Implementacja / weryfikacja |
|---|----------------|-------|-----------------------------|
| 1 | CR 4.1 | kategoria L9: apogeum 9000 m AGL z ładunkiem ≥ 1 kg | cel symulacji; raport `CR 4.1` (apogeum 9042 m, Δ = 0,5 %) |
| 2 | CR 4.3 | całkowity impuls ≤ 40 960 Ns | impuls z pełnej krzywej ciagu = **38 810 Ns** (94,8 % limitu) |
| 3 | SRD RQT-0010 | nietoksyczne materiały pędne | **LOX + etanol 96 %** (wprost na liście nietoksycznych) |
| 4 | SRD RQT-0860/0870 | ładunek ≥ 1000 g | 1,10 kg (format CubeSat: 1000–1330 g) |
| 5 | SRD RQT-1000 | elewacja nominalna 84° ± 1° (regulacja 70–85°) | `Flight(inclination=84)`; sweep 70–85° w analizie wrazliwości |
| 6 | SRD Appendix I | szyna 12 m, profil Kanya 50×50 | `rail_length=12` |
| 7 | SRD RQT-1100 | prędkość zejścia z szyny > 30 m/s | **33,3 m/s**; definicja SRD: ostatnia prowadnica przed CG (3,0 m od ogona) traci kontakt z szyną → droga 9,0 m; RocketPy z `rail_length=12` kończy fazę szynową dokładnie w tym momencie |
| 8 | SRD RQT-1020 | hold-down: zwolnienie dopiero po osiągnięciu ciągu wystarczającego do stabilnego lotu | próg zwolnienia 3,12 kN (0,75·F_peak) ≫ składowa ciężaru wzdłuż szyny 0,57 kN; modelowanie p. §3.3 |
| 9 | SRD RQT-1030 | margines statyczny ≥ 1,5 kalibra przez cały lot, unikać > 6 | min 2,32 / max 2,52 kalibra (z wędrówką CG i przesunięciem CP od oporu falowego) |
| 10 | SRD RQT-0340/0350 | dual deployment, I stopień na apogeum | trigger drogue: `v_z < 0` (apogeum), t = 43,0 s |
| 11 | SRD RQT-0360 | prędkość opadania na drogue 23–46 m/s | 35,8 → 25,9 m/s w pasmach 7,0–0,6 km AGL |
| 12 | SRD RQT-0370 | main ≤ 450 m AGL | trigger 400 m AGL (zapas 50 m) |
| 13 | SRD RQT-0380 | przyziemienie < 9 m/s | **7,45 m/s** |

Pełny raport zgodności: `results/baseline_compliance.txt` (15/15 PASS).

## 2. Założenia projektowe („czarna skrzynka")

Zgodnie z wytycznymi: podzespoły definiowane są wyłącznie makroparametrami
wpływającymi na tor lotu — bez modelowania elektroniki, zaworów, ładunków
pirotechnicznych, mechaniki wyrzutni.

### 2.1 Napęd (LOX / etanol, silnik ciśnieniowy)
* Isp efektywny 205 s (ve = 2010 m/s) — realistyczny zakres studenckich silników
  cisnieniowych LOX/EtOH (ok. 180–220 s); O/F = 1,25.
* Masa zatankowanego paliwa 19,5 kg (LOX 10,83 kg / EtOH 8,67 kg); 1 % masy
  pozostaje jako resztka niedostępna (sump/ullage) — impuls liczymy z masy
  spalonej: **I = ve·m_spalone = 38 810 Ns**.
* Krzywa ciągu: narastanie 0,25 s (pod hold-down), płytowe plateau z lekkim
  spadkiem (spadek ciśnienia butli He), wygaszanie 10,6→11,5 s (zamknięcie
  zaworów). F_peak = 4,16 kN, F_avg ≈ 3,5 kN, TWR ≈ 7.
* Zmiana masy: mdot(t) = F(t)/ve; dwa zbiorniki (`MassFlowRateBasedTank`)
  dają wędrówkę CG w trakcie spalania.
* Zbiorniki: cylindryczne, wypełnienie ~85 % (LOX Ø176×460 mm, EtOH Ø180×500 mm).

### 2.2 Masy i geometria
| pozycja | wartość |
|---|---|
| masa sucha silnika (komora, wtryskiwacz, zbiorniki, He, zawory) | 17,5 kg |
| korpus / przedziały | 11,0 kg |
| awionika (redundantna) | 3,2 kg |
| odzysk (2 spadochrony, wyrzut, uprząż) | 4,5 kg |
| ładunek użyteczny | 1,1 kg |
| pozostałe (wiązki, baterie) | 2,0 kg |
| **masa sucha całkowita** | **39,8 kg** |
| **masa startowa** | **59,3 kg** |

Geometria: kaliber 200 mm, długość 3,90 m (L/D ≈ 19,5), głowica von Kármán
0,85 m, 4 stateczniki trapezowe (root 0,50 m, tip 0,18 m, span 0,11 m,
grubość 8 mm CFRP), prowadnice szynowe na 1,05 m i 3,00 m od ogona.
Struktura masy: payload + awionika z przodu, napęd z tyłu → CG startowy
1,98 m od ogona; wędrówka CG w locie < 2 cm (CG paliwa ≈ CG suchemu),
więc margines stabilności jest praktycznie stały (2,32→2,52 cal).

### 2.3 Aerodynamika
Cd(Mach) oszacowane analitycznie (punkt wyjścia zamiast CFD — ograniczenie):
Cd0 = 0,28 (poddźwięk), pik transoniczny 0,48–0,52 przy M ≈ 1,1, spadek do
0,34 przy M = 3; krzywa power-on nieznacznie niższa. Max Mach 1,54,
q_max 113 kPa (t = 10,7 s, z ≈ 3,0 km).

### 2.4 System odzysku (dual deployment)
* Drogue: CdS = 1,00 m² (Cd 0,8 → czasza stożkowa Ø ≈ 1,26 m), lag 0,7 s,
  trigger na apogeum → opadanie 35,8–25,9 m/s (pasmo 23–46 m/s spełnione
  w całym zakresie wysokości).
* Main: CdS = 11,4 m² (Cd 1,4 → czasza okrągła Ø ≈ 3,22 m), lag 1,2 s,
  trigger 400 m AGL → przyziemienie 7,45 m/s.
* Dobór potwierdzony sweepem CdS (`analysis_recovery.py`,
  `results/08_recovery_sweep.png`, `results/recovery_sweep.csv`).

### 2.5 Środowisko lotu
* Miejsce: poligon **Santa Margarida** k. Constância (Portugalia) — stanowisko
  startowe EuRoC od 2021 r.; 39.4176° N, 8.2930° W, 150 m n.p.m.
  (wysokość z open-elevation API). Data: 18.10.2026, 10:00 (okno EuRoC 2026:
  17–20.10).
* Atmosfera: ISA z możliwością odchyłki temperatury/cisnienia
  (`custom_atmosphere`), wiatr: prawo potęgowe (wykł. 0,14) do 1 km, wyżej
  liniowy wzrost do 2,2·v₁₀ na 9 km (prąd strumieniowy); baza v₁₀ = 5 m/s,
  azymut wiatru 270°, azymut startu 133° (korytarz EuRoC wg DTEG).

## 3. Implementacja w RocketPy — uwagi kluczowe

### 3.1 Konwencje
* `Flight.inclination` w RocketPy = kąt od poziomu → 84° odpowiada wprost
  „launch elevation 84°" z SRD RQT-1000. (Uwaga: Appendix I SRD mówi o
  „inclination 84°±1° to vertical", co jest wewnętrznie sprzeczne z RQT-1000
  i z fotografiami startów EuRoC — przyjęto interpretację RQT-1000 /
  DTEG: elewacja od poziomu, zakres regulacji 70–85°.)
* Współrzędna `z` wektora stanu RocketPy to wysokość **n.p.m.**
  (z_init = elevacja stanowiska) — wszystkie wielkości AGL liczone jako
  `z − elevation`.
* Margines statyczny RocketPy = (CG − CP)/kaliber w układzie `tail_to_nose`
  (CP za CG = stateczność dodatnia); `Flight.static_margin(t)` daje margines
  w funkcji czasu z wędrówką CG (spalanie) i CP (Mach).

### 3.2 Stateczniki a `position`
W RocketPy 1.13 osiowe położenie zestawu stateczników należy podać przy
budowie (`add_trapezoidal_fins(position=...)`); CP zestawu przesuwa się 1:1
z tym parametrem. Kalibracja: `position=0.50 m` daje CP stateczników
0,35 m od ogona. Dobór geometrii: sweep 42 konfiguracji
(`results/06_fin_sweep.png`) — konfiguracja bazowa daje margines 2,3–2,5 cal
(minimum regulaminowe 1,5, unikamy nadstateczności > 6).

### 3.3 Hold-down jako warunek brzegowy
RocketPy w fazie szynowej sam utrzymuje rakietę w spoczynku, dopóki wypadkowa
siła wzdłuż szyny jest ≤ 0 (`udot_rail1`: `if a3 > 0`). Aby próg zwolnienia
był dokładnie progiem układu hold-down (a nie składową ciężaru), krzywa ciągu
przekazana dynamice jest ścięta: dla t < t_release F_dyn = min(F, 0,98·W_rail),
a w t_release następuje skok do F_release. „Brakujący" ciąg pomiędzy
W_rail a F_release przejmują szczęki hold-down — identycznie jak fizycznie.
Impuls raportowany jest z **pełnej** krzywej (konserwatywnie).
Wykres: `results/02_thrust_hold_down.png`.

### 3.4 Wyzwalacze spadochronów
Trigger-y liczą wysokość AGL bezpośrednio z wektora stanu
(`y[2] − elevation`), nie z sygnału barycznego: w RocketPy 1.13 funkcja
`Environment.barometric_height` dla `custom_atmosphere` jest błędna poniżej
~2 km (zwraca wartość stałą), co blokowało wyzwalanie maina. W realiach
odpowiada to „idealnemu altimetrowi"; wpływ błędu barycznego można dodać
jako szum w MC.

## 4. Wyniki bazowe

| wielkość | wartość |
|---|---|
| apogeum AGL | **9042 m** (cel 9000, Δ = 0,5 %) |
| impuls całkowity | 38 810 Ns (94,8 % limitu 40 960) |
| prędkość zejścia z szyny (def. SRD) | 33,3 m/s |
| max Mach / q_max | 1,54 / 113 kPa |
| max przyspieszenie | 80 m/s² (≈ 8,2 g) |
| margines statyczny min / max | 2,32 / 2,52 kalibra |
| MECO / apogeum (czas) | 11,5 s / 43,0 s |
| opadanie na drogue (7→0,6 km) | 35,8 → 25,9 m/s |
| otwarcie main / przyziemienie | 399,8 m AGL / 7,45 m/s |
| czas lotu / dryf wiatrowy | 365 s / 3,5 km |

Wykresy: `01_altitude_velocity.png`, `02_thrust_hold_down.png`,
`03_stability.png`, `04_descent.png`, `05_ground_track.png`.

## 5. Analizy

### 5.1 Stabilność (`analysis_stability.py`)
Sweep geometrii stateczników (span 0,08–0,16 m, root 0,40–0,60 m, 3 i 4
stateczniki): margines na starcie 1,6–5,3 cal; konfiguracja bazowa
(span 0,11 m, root 0,50 m, 4 szt.) = 2,32 cal na starcie, 2,34 cal na zejściu
z szyny, min 2,32 / max 2,52 cal w locie — spełnia RQT-1030 z zapasem i bez
nadstateczności. Wykresy `06_fin_sweep.png`, `07_cg_cp_margin.png`
(wędrówka CG/CP: CG przesuwa się < 2 cm, CP cofa się o ~4 cm w zakresie
transonicznym — uwzględnione w min marginesu).

### 5.2 Odzysk (`analysis_recovery.py`)
Sweep CdS drogue 0,70–1,30 m²: pasmo 23–46 m/s spełnione dla 0,70–1,15 m²
(przy 1,30 prędkość przy 0,6 km spada do 22,7 m/s — poza pasmem);
sweep CdS main 9–14 m²: przyziemienie 8,4–6,7 m/s (limit 9). Baza:
1,00 / 11,4 m² → komfortowy zapas w obu kierunkach. Czas opadania ~6 min,
dryf 3,5 km (informacyjnie: strefa lądowania poligonu).

### 5.3 Wrazliwość + Monte Carlo (`analysis_sensitivity.py`)
Deterministycznie (tornado `09_sensitivity_tornado.png`):
* elewacja szyny: 70° → apogeum 7832 m (−13 %), 85° → 9056 m; zmiana elewacji
  to najsilniejszy czynnik „operacyjny" — przy wymuszonej elewacji 70°
  (prawo organizatora) rakieta nie osiąga celu: wniosek: korekta impulsem
  lub akceptacja niższego wyniku punktowego;
* wiatr: 0→15 m/s zmienia apogeum 8964→8210 m (wiatr „zabiera" energię na
  utrzymanie kąta natarcia i znoszenie);
* temperatura ISA −15/+15 K: 8738/9341 m; ciśnienie 0,95/1,05: 9305/8800 m;
* masa sucha ±5 %: ∓110 m; Isp ±2 %: ±210 m; paliwo ±1,5 %: ±130 m.

Monte Carlo N = 48 (jednoczesny rozrzut: elewacja N(84; 0,5)°, wiatr
U(0;10) m/s + kierunek U(0;360)°, T N(0;7) K, p N(1;1,5 %), masa sucha
N(1;2,5 %), Isp N(1;1,5 %), paliwo N(1;1 %), CdS drogue N(1;5 %), main
U(350;450) m): apogeum mean 9022 m, p5–p95 = 8675–9363 m; **47/48 prób
w paśmie ±5 % celu**; v_rail min 32,6 m/s (> 30 we wszystkich); SM min
2,3 cal; przyziemienie max 7,7 m/s; wysokość main max 447,8 m (≤ 450).
Wykres `10_monte_carlo.png`, dane `monte_carlo_results.csv`.

Wniosek operacyjny: kryterium okna meteo utrzymujące apogeum w ±5 %:
wiatr ≤ 10 m/s i temperatura w ±15 K od ISA.

### 5.4 Flutter stateczników (`analysis_flutter.py`)
Kryterium Martina (NACA TN 4197) w postaci skorygowanej o √2 (Bennett,
Apogee PoF #615/2023; wbudowana funkcja RocketPy zawyża wynik o √2 —
issue #1200): dla q_max = 113 kPa (z = 3,0 km, V = 502 m/s) i CFRP
(G = 6,9 GPa): V_flutter = 4982 m/s przy grubości 8 mm → zapas V_f/V ≈ 9,9
(≥ 2 wymagane dla lotu naddźwiękowego); nawet 5 mm daje zapas 4,9.
Wykres `11_fin_flutter.png`.

## 6. Ograniczenia modelu

1. Cd(Mach) analityczne, bez CFD i bez separacji strugi silnika — traktowane
   jako punkt wyjścia; błąd ±10 % Cd przesuwa apogeum o ~±250 m (pokryte
   analizą wrazliwości przez Isp/masę).
2. Brak modelu sloshingu paliwa i elastyczności konstrukcji (SRD wspomina
   sloshing przy marginesie — uwzględniony tylko zapasem marginesu).
3. Spadochrony: stałe CdS, brak dynamiki napelniania poza parametrem `lag`,
   brak interakcji czasza–korpus (oscylacje).
4. Wiatr: profil deterministyczny (prawo potęgowe + liniowy wzrost), bez
   podmuchów szkwałowych (`add_wind_gust` dostępne, nie użyte w bazie).
5. MC: 48 prób (czas obliczeń), rozkłady uproszczone; wyniki traktować
   jako rząd wielkości ryzyka, nie dokładną dystrybucję.
6. Trigger-y odzysku zakładają idealny pomiar wysokości (patrz §3.4).
7. Model 6 DOF bez sterowania aktywnego (zgodnie z kategorią — brak ACS).

## 7. Struktura repozytorium i odtworzenie

```
euroc_l9/
├── config.py               # wszystkie założenia (SI) + limity regulaminowe
├── motor_model.py          # krzywa ciągu, hold-down, zbiorniki, LiquidMotor
├── rocket_model.py         # płatowiec, stateczniki, odzysk, Flight
├── environment_model.py    # stanowisko, ISA+odchyłki, profil wiatru
├── compliance.py           # raport zgodności CR/SRD (15 kontroli)
├── simulate_baseline.py    # lot nominalny + wykresy 01-05 + CSV
├── analysis_stability.py   # sweep stateczników, CG/CP, wykresy 06-07
├── analysis_recovery.py    # sweep CdS drogue/main, wykres 08
├── analysis_flutter.py     # flutter NACA TN 4197 (skorygowany), wykres 11
├── analysis_sensitivity.py # sweep deterministyczny + Monte Carlo, 09-10
├── run_all.py              # pełny potok (~2-4 min)
├── requirements.txt        # rocketpy==1.13.0, numpy, scipy, matplotlib
└── results/                # wykresy PNG, CSV, raport zgodności
```

Uruchomienie: `pip install -r requirements.txt`, następnie `python run_all.py`
(lub `python run_all.py quick` — mniejsze MC). Wszystkie symulacje
deterministyczne; MC z seedem 42.
