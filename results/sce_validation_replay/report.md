# SCE-Vorhersagetest: Jev gegen einfache Referenzen

Ziel: angegebene Antwort auf QSP13new (hypothetischer Einkommensrückgang um 10 %). Selbstauskunft zu einem hypothetischen Szenario, kein beobachtetes Verhalten. Source: Survey of Consumer Expectations, © 2013-2026 Federal Reserve Bank of New York; modified for this analysis.

- Stichproben: Training 10133, Anpassung 400 (400 mit Jev), Test 800 (800 mit Jev)
- Anfragen 1400, Fehler 0, Kosten 0.03934161 USD, Modelle typesafe/jev-1.14-20261014
- Code `f2ebca215fad`

## Primäres Kriterium (vorab festgelegt)

Δ Log-Loss M4 (Logit + Jev) − M1 (Logit): -0.0049, 95 %-Intervall [-0.0181, +0.0084] → **kein nachgewiesener zusätzlicher Vorhersagenutzen**

## Kennzahlen (Test, drei Klassen: volle Kürzung / teilweise / keine)

Beobachtete Anteile: [0.4162, 0.5112, 0.0725]

| Modell | Log-Loss | Brier | Trefferquote | AUC Kürzung ja/nein | AUC volle Kürzung | mittlere vorhergesagte Anteile |
|---|---|---|---|---|---|---|
| M0_prior | 0.9033 | 0.5630 | 0.511 | 0.500 | 0.500 | [0.4601, 0.4842, 0.0558] |
| M1_logit | 0.8938 | 0.5535 | 0.536 | 0.556 | 0.590 | [0.4577, 0.4866, 0.0557] |
| M2_jev_raw | 1.1150 | 0.6616 | 0.522 | 0.475 | 0.541 | [0.192, 0.6455, 0.1625] |
| M3_jev_calibrated | 0.9023 | 0.5612 | 0.515 | 0.496 | 0.534 | [0.4079, 0.5321, 0.0601] |
| M4_stacked | 0.8889 | 0.5501 | 0.534 | 0.550 | 0.591 | [0.4113, 0.5296, 0.0592] |

Sieben Klassen, Log-Loss: {'M0_prior': 1.2698444356883323, 'M1_logit': 1.2259583427566791, 'M2_jev_raw': 1.5161593765380832}

M3 − M1: {'mean': 0.008475484184077474, 'ci95': [-0.006391787114561566, 0.02355363492365043]}

## Technische Kontrolle (Darstellung)

{'other_presentation': {'n': 120, 'median_tvd': 0.12, 'max_tvd': 0.32999999999999996}, 'repeat': {'n': 40, 'median_tvd': 0.04000000000000001, 'max_tvd': 0.12000000000000004}, 'placebo': {'n': 40, 'median_tvd': 0.044999999999999984, 'max_tvd': 0.13}, 'presentation_sensitive': False}

