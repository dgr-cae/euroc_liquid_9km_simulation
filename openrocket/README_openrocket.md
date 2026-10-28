# Walidacja krzyżowa w OpenRocket (wariant C)

Pliki wygenerowane automatycznie z modelu RocketPy (`python openrocket_export.py`):

| Plik | Zawartość |
|---|---|
| `L9_AGH.ork` | kompletny model rakiety + gotowa symulacja (ZIP z `rocket.ork`, format 1.10 → **wymaga OpenRocket ≥ 23.09**) |
| `L9-AGH-38k.eng` | krzywa ciągu silnika LOX/EtOH (format RASP, 7-polowy nagłówek; OpenRocket sam wylicza masę i wędrówkę CG z pól propellant/total weight) |
| `validation_targets.csv` | wyniki RocketPy do porównania 1:1 |

## Instrukcja (ok. 20–30 min)

1. **Zainstaluj silnik**: skopiuj `L9-AGH-38k.eng` do katalogu krzywych użytkownika:
   - Windows: `C:\Users\<TWÓJ_USER>\AppData\Roaming\OpenRocket\ThrustCurves\`
     — najszybciej: wciśnij `Win+R`, wpisz `%APPDATA%\OpenRocket\ThrustCurves` i Enter.
     Jeśli folderu nie ma, **utwórz go ręcznie** (AppData jest ukryty — w Eksploratorze:
     Widok → Pokaż → Ukryte elementy). Musiałeś choć raz uruchomić OpenRocket,
     żeby istniał folder `%APPDATA%\OpenRocket`.
   - Linux: `~/.openrocket/ThrustCurves/`, macOS: `~/Library/Application Support/OpenRocket/ThrustCurves/`.
   - **Alternatywa bez szukania folderów**: utwórz folder np. `Dokumenty\moje_silniki`,
     wrzuć tam plik `.eng`, a w OpenRocket: *Edit → Preferences → General →
     User-defined thrust curves → Add* i wskaż ten folder.
   Zrestartuj OpenRocket.
2. **Otwórz `L9_AGH.ork`**. Jeśli silnik nie dopasował się automatycznie (komunikat
   o nierozpoznanym motorze): *Motor configuration → Select motor → User motors →
   AGHSS / L9-AGH-38k* (kod producenta w pliku `.eng` to `AGHSS` — parser RASP
   nie przyjmuje nazw ze spacjami).
3. **Sprawdź kluczowe ustawienia** (importowane, ale warto rzucić okiem):
   - masy: CG bez silnika **2.50 m** od ogona, masa startowa **58.8 kg**, sucha **39.3 kg**;
   - stateczniki: 4× trapez, root 0.50 / tip 0.18 / span 0.11 / sweep 0.20, grubość 8 mm,
     leading edge przy samym ogonie korpusu;
   - szyna: długość **12 m**, kąt **6° od pionu** (84° od poziomu), kierunek 133°,
     rail buttony na 1.05 i 3.00 m;
   - odzysk: drogue D≈1.26 m (Cd 0.8) na apogeum + 0.7 s; main D≈3.22 m (Cd 1.4)
     na **400 m AGL** (zdarzenie „Altitude descending") + 1.2 s;
   - warunki: wiatr wielopoziomowy wg profilu z modelu (kier. 270°, ~5 m/s @10 m
     rosnący do ~11 m/s na 9 km), atmosfera ISA, wys. startu 150 m n.p.m.,
     szer./dług. 39.4176 / −8.2930 (Santa Margarida).
4. **Uruchom symulację** „L9 nominal (walidacja vs RocketPy)" i porównaj z
   `validation_targets.csv`.
5. (Opcjonalnie) *Simulate → Monte Carlo* z rozrzutem wiatru ±1 m/s i masy ±2% —
   odpowiada naszej analizie `analysis_sensitivity.py`.

## Czego się spodziewać (różnice metodyczne — to jest wartość walidacji)

| Wielkość | RocketPy | Oczekiwanie w OR | Dlaczego |
|---|---|---|---|
| Apogeum | 9042 m | 8100–9900 m (±10%) | OR liczy własne Cd (Barrowman + empiryczne), my mamy zadaną krzywą Cd(Mach) |
| v_rail | 33.3 m/s (przelot 9 m, def. SRD) | ~33–35 m/s | OR raportuje prędkość po ~11–12 m przelotu (tylny button opuszcza szynę); OR też modeluje hold-down (ruch startuje gdy ciąg > składowa ciężaru) |
| Margines stat. | 2.32–2.52 cal | ±0.3 cal | obie metody Barrowman; drobne różnice w CP korpusu/głowicy |
| Opadanie na drogue | 26–36 m/s (7→0.6 km) | ±5% | te same CdS, inny profil gęstości (OR: ISA) |
| Prędkość przyziemienia | 7.45 m/s | 7–8 m/s | to samo CdS maina |
| Dryft | 3524 m | większy rozrzut | OR: wiatr jako poziomy (bez składowej pionowej) i inna konwencja kierunku — sprawdź, czy dryft jest w tę samą stronę |

Uwagi:
- **Konwencja kierunku wiatru**: wpisano 270° jako kierunek *z którego* wieje
  (meteorologiczna). Jeśli w OR dryft wyjdzie w przeciwną stronę — zmień na 90°.
- OR nie modeluje wymuszonego opóźnienia otwarcia tak samo jak RocketPy
  (`lag` ↔ `deploy delay` ≈ to samo, ale OR nie symuluje procesu napełniania).
- Jeśli Twój OpenRocket jest starszy niż 23.09, wiatr wielopoziomowy zostanie
  zignorowany — użyje wartości `windaverage` = 5 m/s (też zapisana w pliku).
- Plik `.ork` celowo używa materiałów o zerowej gęstości dla geometrii, aby cały
  rozkład mas pochodził z komponentów masowych — identycznie jak w modelu RocketPy
  (zasada „czarnej skrzynki").
