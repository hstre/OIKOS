# SCE-Vorhersagetest: Jev gegen einfache Referenzen

Ziel: angegebene Antwort auf QSP13new (hypothetischer Einkommensrückgang um 10 %). Selbstauskunft zu einem hypothetischen Szenario, kein beobachtetes Verhalten. Source: Survey of Consumer Expectations, © 2013-2026 Federal Reserve Bank of New York; modified for this analysis.

- Stichproben: Training 10133, Anpassung 400 (400 mit Jev), Test 800 (800 mit Jev)
- Anfragen 1400, Fehler 0, Kosten 0.03934161 USD, Modelle typesafe/jev-1.14-20261014
- Code `2beaf68152b5`

## Primäres Kriterium (vorab festgelegt)

Δ Log-Loss M4 (Logit + Jev) − M1 (Logit): -0.0043, 95 %-Intervall [-0.0175, +0.0090] → **kein nachgewiesener zusätzlicher Vorhersagenutzen**

## Kennzahlen (Test, drei Klassen: volle Kürzung / teilweise / keine)

Beobachtete Anteile: [0.4162, 0.5112, 0.0725]

| Modell | Log-Loss | Brier | Trefferquote | AUC Kürzung ja/nein | AUC volle Kürzung | mittlere vorhergesagte Anteile |
|---|---|---|---|---|---|---|
| M0_prior | 0.9033 | 0.5630 | 0.511 | 0.500 | 0.500 | [0.4601, 0.4842, 0.0558] |
| M1_logit | 0.8938 | 0.5535 | 0.536 | 0.556 | 0.590 | [0.4577, 0.4866, 0.0557] |
| M2_jev_raw | 1.1151 | 0.6617 | 0.522 | 0.475 | 0.540 | [0.1921, 0.6455, 0.1625] |
| M3_jev_calibrated | 0.9030 | 0.5617 | 0.514 | 0.493 | 0.532 | [0.4074, 0.5326, 0.06] |
| M4_stacked | 0.8895 | 0.5505 | 0.536 | 0.547 | 0.590 | [0.411, 0.5299, 0.0591] |

Sieben Klassen, Log-Loss: {'M0_prior': 1.2698444356883323, 'M1_logit': 1.2259583427566794, 'M2_jev_raw': 1.5163989430656166}

M3 − M1: {'mean': 0.00914429109955984, 'ci95': [-0.005902971748862028, 0.024381045015519406]}

## Technische Kontrolle (Darstellung)

{'other_presentation': {'n': 120, 'median_tvd': 0.12999999999999998, 'max_tvd': 0.35000000000000003}, 'repeat': {'n': 40, 'median_tvd': 0.0, 'max_tvd': 0.0}, 'placebo': {'n': 40, 'median_tvd': 0.04, 'max_tvd': 0.07999999999999999}, 'presentation_sensitive': False}

