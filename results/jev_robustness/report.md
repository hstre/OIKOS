# Jev-Robustheitstests: household_goods_budget_v1

Nur Beobachtung, dieselben 48 Haushaltszustände wie im ersten Lauf, je Test genau ein veränderter Faktor. Scores sind modellinterne Werte, keine empirischen Entscheidungswahrscheinlichkeiten. „Anteil“ = Budget relativ zum Einkommen nach der Energierechnung.

- Modus: live; Kosten gesamt 0.00653927 USD (Limit 0.01 USD)
- Code: `4023d2a86bd8`

## Überblick

| Test | gesendet | Fehler/übersprungen | gewählter Anteil Median (10–90 %) | score-gewichteter Anteil Median (10–90 %) | gleiches €-Budget wie Original | TVD zum Original Median / Max |
|---|---|---|---|---|---|---|
| Original (Lauf 1) | 48 | – | 75% (60%–75%) | 72% (70%–76%) | – | – |
| T5_repeat | 48 | 0  | 75% (60%–75%) | 72% (71%–76%) | 81% | 0.040 / 0.150 |
| T1_reversed_order | 48 | 0  | 90% (75%–90%) | 81% (79%–83%) | 19% | 0.315 / 0.510 |
| T2_euro_only | 48 | 0  | 75% (75%–90%) | 80% (78%–82%) | 56% | 0.250 / 0.430 |
| T3_with_history | 48 | 0  | 90% (75%–100%) | 90% (83%–93%) | 8% | 0.625 / 0.780 |
| T4_wider_range | 48 | 0  | 60% (45%–75%) | 60% (58%–63%) | 38% | – / – |

TVD = Totalvariationsabstand der Score-Verteilungen über dieselben Optionen (0 = identisch, 1 = disjunkt); nur für Tests mit identischen Optionsbeträgen. T5 zeigt das Rauschen zwischen zwei Live-Abfragen.

## Mittlere Score-Masse nach Budgetanteil

| Test | <55 % | 55–65 % | 65–80 % | 80–95 % | ≥95 % |
|---|---|---|---|---|---|
| Original | 0% | 38% | 43% | 12% | 6% |
| T5_repeat | 0% | 38% | 43% | 12% | 7% |
| T1_reversed_order | 0% | 20% | 31% | 38% | 12% |
| T2_euro_only | 0% | 20% | 37% | 28% | 15% |
| T3_with_history | 0% | 6% | 21% | 37% | 35% |
| T4_wider_range | 36% | 31% | 24% | 5% | 4% |

## Reihenfolge, Positionen und Kennungen

| Test | gewählte Kennungen | gewählte Positionen (1 = zuerst gezeigt) |
|---|---|---|
| T5_repeat | {'b1': 14, 'b2': 34} | {'1': 14, '2': 34} |
| T1_reversed_order | {'b1': 2, 'b2': 12, 'b3': 34} | {'3': 34, '4': 12, '5': 2} |
| T2_euro_only | {'b2': 42, 'b3': 6} | {'2': 42, '3': 6} |
| T3_with_history | {'b2': 7, 'b3': 20, 'b4': 21} | {'2': 7, '3': 20, '4': 21} |
| T4_wider_range | {'b2': 11, 'b3': 30, 'b4': 7} | {'2': 11, '3': 30, '4': 7} |

In T1 tragen b1…b5 weiterhin dieselben Beträge; nur die Reihenfolge ist umgekehrt (b5 steht an Position 1). Ein Einfluss der Kennungen selbst wird dadurch nicht ausgeschlossen.

## Reaktion auf Informationen: mittlerer score-gewichteter Anteil nach Gruppen

| Test | vor/nach Schock | im Schock | erwerbstätig | erwerbslos | Ersparnis < Median | ≥ Median |
|---|---|---|---|---|---|---|
| Original | 72% (n=24) | 73% (n=24) | 72% (n=41) | 76% (n=7) | 72% (n=24) | 73% (n=24) |
| T5_repeat | 72% (n=24) | 74% (n=24) | 72% (n=41) | 76% (n=7) | 72% (n=24) | 74% (n=24) |
| T1_reversed_order | 81% (n=24) | 81% (n=24) | 81% (n=41) | 82% (n=7) | 80% (n=24) | 82% (n=24) |
| T2_euro_only | 79% (n=24) | 81% (n=24) | 80% (n=41) | 80% (n=7) | 79% (n=24) | 80% (n=24) |
| T3_with_history | 90% (n=24) | 88% (n=24) | 89% (n=41) | 85% (n=7) | 89% (n=24) | 89% (n=24) |
| T4_wider_range | 60% (n=24) | 60% (n=24) | 60% (n=41) | 63% (n=7) | 59% (n=24) | 61% (n=24) |

## Kosten und Modelle

| Test | Kosten USD | Modelle |
|---|---|---|
| T5_repeat | 0.00129158 | typesafe/jev-1.14-20261014 |
| T1_reversed_order | 0.00129158 | typesafe/jev-1.14-20261014 |
| T2_euro_only | 0.00113635 | typesafe/jev-1.14-20261014 |
| T3_with_history | 0.00138634 | typesafe/jev-1.14-20261014 |
| T4_wider_range | 0.00143342 | typesafe/jev-1.14-20261014 |

T3 enthält die Ausgaben des Vormonats aus dem Regellauf. Das ist **synthetische Modellgeschichte, keine empirischen Haushaltsdaten**; im Zustand an Jev ist dies ebenfalls vermerkt (`history_note`).
