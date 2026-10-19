# Jev-Paartest: jev_pairs_v1

Konstruierte Fälle, nur Beobachtung. Scores sind modellinterne Werte, keine Entscheidungswahrscheinlichkeiten. Vorab festgelegte Regel: konsistent unterschieden = gleiches Vorzeichen in allen 5 Darstellungen und |Median Δ| > 2 × Rauschen.

- Modus replay; Anfragen 72, erfolgreich 72, Fehler 0
- Modelle: typesafe/jev-1.14-20261014; Kosten 0.00172822 USD
- Rauschen (Median |Δ gewichtetes Budget| bei Wiederholung): 0.0 € (TVD-Median 0.000)
- Gewählte Positionen über alle Anfragen: {'1': 5, '2': 15, '3': 21, '4': 12, '5': 19}; Kennungen: {'hj': 11, 'kq': 19, 'pw': 14, 'vx': 20, 'zt': 8}
- Code `d4c65ba710bf`

## Ergebnis je Paar

| Paar | Merkmal | Hypothese | Median Δ gewichtetes Budget (min…max) | gleiches Vorzeichen | konsistent unterschieden | Richtung | TVD A–B Median |
|---|---|---|---|---|---|---|---|
| P0_placebo | street name (economically irrelevant) | kein Unterschied | +6 € (-21…+36) | 3/5 | nein | höher | 0.030 |
| P1_job_security | expected job security | niedriger | -204 € (-267…-138) | 5/5 | ja | niedriger | 0.320 |
| P2_savings | savings | höher | -18 € (-45…-9) | 5/5 | ja | niedriger | 0.090 |
| P3_last_month_spending | last month's spending on other goods and services | höher | +714 € (+657…+759) | 5/5 | ja | höher | 0.940 |
| P4_energy_price | energy price shock (price and resulting bill) | niedriger | +18 € (-18…+102) | 3/5 | nein | höher | 0.080 |
| P5_income | net income this month | höher | +483 € (+390…+543) | 5/5 | ja | höher | 0.610 |

## Je Darstellung: Eurobeträge, Quoten, gewählte Optionen

### P0_placebo: street name (economically irrelevant)

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1719 | 1719 | +0 | 1800 (3, vx) | 1800 (3, vx) | 72% / 76% | 72% / 76% | 0.030 |
| 1 | 1791 | 1797 | +6 | 1800 (2, hj) | 1800 (2, hj) | 75% / 80% | 75% / 80% | 0.020 |
| 2 | 1707 | 1743 | +36 | 1500 (5, kq) | 1500 (5, kq) | 71% / 76% | 73% / 77% | 0.050 |
| 3 | 1704 | 1734 | +30 | 1800 (5, pw) | 1800 (5, pw) | 71% / 76% | 72% / 77% | 0.080 |
| 4 | 1686 | 1665 | -21 | 1800 (4, kq) | 1800 (4, kq) | 70% / 75% | 69% / 74% | 0.030 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.04 | 0.13 | 0.19 | 0.35 | 0.28 |
| B | 0.04 | 0.12 | 0.20 | 0.36 | 0.27 |

### P1_job_security: expected job security

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1692 | 1473 | -219 | 1800 (3, vx) | 1500 (2, zt) | 70% / 75% | 61% / 65% | 0.360 |
| 1 | 1767 | 1500 | -267 | 1800 (2, hj) | 1200 (5, vx) | 74% / 79% | 62% / 67% | 0.400 |
| 2 | 1713 | 1575 | -138 | 1500 (5, kq) | 1500 (5, kq) | 71% / 76% | 66% / 70% | 0.190 |
| 3 | 1701 | 1497 | -204 | 1800 (5, pw) | 1500 (4, vx) | 71% / 76% | 62% / 67% | 0.320 |
| 4 | 1644 | 1476 | -168 | 1800 (4, kq) | 1200 (2, pw) | 68% / 73% | 62% / 66% | 0.270 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.04 | 0.14 | 0.17 | 0.36 | 0.29 |
| B | 0.02 | 0.36 | 0.07 | 0.17 | 0.38 |

### P2_savings: savings

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1734 | 1725 | -9 | 1800 (3, vx) | 1800 (3, vx) | 72% / 77% | 72% / 77% | 0.100 |
| 1 | 1818 | 1800 | -18 | 1800 (2, hj) | 2100 (3, kq) | 76% / 81% | 75% / 80% | 0.080 |
| 2 | 1809 | 1776 | -33 | 1800 (1, zt) | 2100 (2, vx) | 75% / 80% | 74% / 79% | 0.180 |
| 3 | 1797 | 1752 | -45 | 1800 (5, pw) | 1800 (5, pw) | 75% / 80% | 73% / 78% | 0.070 |
| 4 | 1698 | 1680 | -18 | 1800 (4, kq) | 1800 (4, kq) | 71% / 75% | 70% / 75% | 0.090 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.03 | 0.09 | 0.25 | 0.40 | 0.23 |
| B | 0.04 | 0.13 | 0.25 | 0.33 | 0.25 |

### P3_last_month_spending: last month's spending on other goods and services

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1527 | 2241 | +714 | 1500 (2, zt) | 2400 (5, hj) | 64% / 68% | 93% / 100% | 0.920 |
| 1 | 1524 | 2214 | +690 | 1500 (1, pw) | 2100 (3, kq) | 64% / 68% | 92% / 98% | 0.940 |
| 2 | 1512 | 2226 | +714 | 1500 (5, kq) | 2400 (3, pw) | 63% / 67% | 93% / 99% | 0.940 |
| 3 | 1506 | 2163 | +657 | 1500 (4, vx) | 2100 (1, hj) | 63% / 67% | 90% / 96% | 0.960 |
| 4 | 1512 | 2271 | +759 | 1500 (3, hj) | 2400 (1, vx) | 63% / 67% | 95% / 101% | 0.970 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.00 | 0.02 | 0.01 | 0.03 | 0.93 |
| B | 0.47 | 0.01 | 0.50 | 0.02 | 0.01 |

### P4_energy_price: energy price shock (price and resulting bill)

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1692 | 1794 | +102 | 1800 (3, vx) | 1800 (3, vx) | 70% / 75% | 75% / 85% | 0.140 |
| 1 | 1779 | 1761 | -18 | 1800 (2, hj) | 1800 (2, hj) | 74% / 79% | 73% / 84% | 0.050 |
| 2 | 1713 | 1731 | +18 | 1500 (5, kq) | 1500 (5, kq) | 71% / 76% | 72% / 82% | 0.090 |
| 3 | 1731 | 1755 | +24 | 1800 (5, pw) | 1800 (5, pw) | 72% / 77% | 73% / 84% | 0.060 |
| 4 | 1698 | 1686 | -12 | 1800 (4, kq) | 1800 (4, kq) | 71% / 75% | 70% / 80% | 0.080 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.04 | 0.12 | 0.19 | 0.37 | 0.28 |
| B | 0.05 | 0.14 | 0.22 | 0.34 | 0.24 |

### P5_income: net income this month

| Darst. | A gewichtet € | B gewichtet € | Δ € | A gewählt € (Pos., Kennung) | B gewählt € (Pos., Kennung) | A Quote netto / nach Energie | B Quote netto / nach Energie | TVD |
|---|---|---|---|---|---|---|---|---|
| 0 | 1482 | 1881 | +399 | 1500 (2, zt) | 2100 (4, pw) | 82% / 90% | 59% / 62% | 0.540 |
| 1 | 1482 | 1977 | +495 | 1500 (1, pw) | 2100 (3, kq) | 82% / 90% | 62% / 65% | 0.610 |
| 2 | 1497 | 2040 | +543 | 1500 (5, kq) | 2400 (3, pw) | 83% / 91% | 64% / 67% | 0.620 |
| 3 | 1503 | 1986 | +483 | 1500 (4, vx) | 2400 (2, kq) | 84% / 91% | 62% / 65% | 0.610 |
| 4 | 1545 | 1935 | +390 | 1500 (3, hj) | 2100 (5, zt) | 86% / 94% | 60% / 63% | 0.530 |

Mittlere Scores je Betrag über die 5 Darstellungen (modellintern):

| Fall | 2400 € | 1200 € | 2100 € | 1800 € | 1500 € |
|---|---|---|---|---|---|
| A | 0.04 | 0.33 | 0.04 | 0.13 | 0.46 |
| B | 0.26 | 0.07 | 0.30 | 0.24 | 0.14 |

