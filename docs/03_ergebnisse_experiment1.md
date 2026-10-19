# Experiment 1: Energiepreisschock – Auswertung v0.1

Stand: 2026-10-19 · Code `ef7f4c6` · Rohergebnisse: `results/energy_shock/`, `results/energy_shock_sensitivity/`

> **Geltungsbereich.** Alle Aussagen sind bedingte Aussagen über ein stilisiertes Modell mit gesetzten, nicht kalibrierten Parametern (12 von 12 Profilparametern haben den Status „assumed“). Sie sagen, was aus den implementierten Mechanismen folgt, nicht was in einer realen Wirtschaft passieren würde. Validiert ist bisher nur die Software (Ebene 1) und teilweise die Umsetzung der Mechanismen (Ebene 2). Verhalten (Ebene 3) und Gesamtsystem (Ebene 4) sind nicht geprüft.

## Aufbau

- **Schock**: Der Weltenergiepreis verdoppelt sich für 24 Monate. Für Haushalte steigt der Preis von 9,0 auf 16,2 ct/kWh.
- **Szenarien**: S0 keine Maßnahme, S1 pauschaler Transfer, S2 Preissubvention (50 % des Preisanstiegs), S3 Effizienzinvestition. Das Budget ist bei allen gleich: B ≈ 1,03 Mio. € für 1 000 Haushalte über 24 Monate, also rund 43 € pro Haushalt und Monat.
- **Ensemble**: 100 Seeds, gemeinsame Zufallszahlen. Bis Monat −1 verlaufen alle Szenarien eines Seeds identisch; das ist getestet.
- **Software-Prüfung**: In allen 500 Läufen gelten alle Buchführungsinvarianten in jedem Monat exakt. Ein erneut gerechneter Lauf ist bitgleich. Das Basismodell ohne Schock ist quasistationär: Zwischen den Monaten −12…−1 und 48…59 ändert sich die Arbeitslosigkeit im Median um +0,5 Pp. und das Preisniveau um +1 %.

## Was der Schock im Modell bewirkt (S0 gegenüber Lauf ohne Schock)

- Die Arbeitslosigkeit steigt in den Monaten 0–23 von rund 6 % auf 7 % im Mittel, mit einer Spitze um 9 %.
- Der reale Konsum im untersten Einkommensquintil sinkt um etwa 4,6 %.
- Der Anteil der Haushalte, die mehr als 10 % ihres Nettoeinkommens für Energie ausgeben, steigt von rund 2 % auf 21 %.
- Kein Haushalt kann seine gewünschte Energiemenge nicht bezahlen. Die Einlagen reichen dafür aus (siehe Grenzen).

## Ergebnisse (gepaarte Differenz zu S0, Median und 5–95 %-Spanne über 100 Seeds)

| | S1 Transfer | S2 Subvention | S3 Investition |
|---|---|---|---|
| Arbeitslosigkeit 0–23 (Pp.) | −1,2 (−1,6 … −0,9) | −1,2 (−1,6 … −0,8) | −1,4 (−1,9 … −1,1) |
| Realer Konsum Q1 0–23 (Einheiten/HH) | +2,6 (+0,9 … +4,7) | +2,2 (+0,4 … +4,0) | −1,2 (−3,0 … +0,3) |
| Realer Konsum Q5 0–23 | +8,6 | +7,9 | +5,1 |
| Haushalte mit Energiekosten > 10 % (Pp.) | −1,8 | −12,8 | −0,7 |
| Energieimporte 0–23 (GWh, Basis ≈ 49) | +0,28 | +0,79 | −0,04 (−0,12 … +0,08) |
| Energieimporte 24–59 (GWh, Basis ≈ 76) | +0,04 (−0,09 … +0,19) | +0,05 (−0,13 … +0,23) | −1,71 (−1,94 … −1,51) |
| Güterpreisniveau 0–23 | +1,3 % | +1,2 % | +1,4 % |
| Staatsschuld bis Monat 59 (Mio. €) | +0,68 | +0,66 | +0,67 |
| Tatsächliche Programmkosten (Mio. €) | 1,03 | 1,00 | 1,03 |

### Lesart

1. **Alle drei Instrumente senken die Arbeitslosigkeit während des Schocks** in ähnlichem Umfang. Im Modell wirken sie vor allem als Nachfrageimpuls. Die Staatsschuld steigt jeweils nur um rund zwei Drittel des Budgets, weil Steuereinnahmen zurückfließen. Das Ergebnis ist robust in allen 14 Sensitivitätsvarianten.
2. **Transfer und Subvention entlasten das unterste Quintil ähnlich.** Der Transfer liegt in 68 % der Seeds vorn (E2), der Unterschied ist klein. Absolut profitiert das oberste Quintil stärker, weil es mehr konsumiert und über Dividenden an der höheren Nachfrage verdient.
3. **Die Kennzahl „Energiekosten > 10 %“ begünstigt die Subvention mechanisch**, weil sie den gezahlten Preis misst. Dass die Subvention hier weit vorn liegt (E2b), ist deshalb kein Beleg für eine bessere Entlastung.
4. **Die Subvention erhöht den Energieverbrauch während des Schocks** gegenüber dem Transfer (E1, in 100 % der Seeds). Der Effekt ist klein: gegenüber S0 etwa +1,6 % der Importe, gegenüber dem Transfer etwa +1 %. Grund ist die kleine gesetzte Preiselastizität (−0,15). Mit Elastizität −0,30 steigt der Mehrverbrauch gegenüber S0 auf das 1,6-Fache.
5. **Die Investition wirkt erst nach dem Schock.** Ab Monat 24 sinken die Energieimporte robust um etwa 2,2 %, in jeder Sensitivitätsvariante. Während des Schocks hilft sie dem untersten Quintil nicht, sondern schadet in 91 % der Seeds leicht, weil sie das Preisniveau stärker anhebt, ohne Einkommen direkt zu stützen. Die 68 sanierten Haushalte sind die mit dem höchsten Energiebedarf.
6. **Hysterese im Preisniveau.** Mit allen drei Maßnahmen liegt das Preisniveau in den Monaten 36–59 etwa 6 % über S0, die Löhne nur etwa 3 %. Dadurch ist der reale Konsum des untersten Quintils langfristig etwas *niedriger* als ohne Maßnahme. Ursache ist die Lohnregel: Löhne steigen sofort, wenn Stellen offen bleiben, sinken aber erst nach 24 Monaten ohne offene Stelle, und die Aufschläge steigen mit der Nachfrage. Das ist eine Folge dieser Annahme, kein allgemeiner Befund über Transfers. In der Variante mit flexiblen Löhnen ist der Preisanstieg während des Schocks größer. Wie sich die langfristige Hysterese unter anderen Lohnregeln verhält, ist noch nicht ausgewertet.

### Was nicht robust ist

Aus der Sensitivitätsanalyse (14 Varianten, je 30 Seeds):
- **Langfristige Energieimporte unter S1/S2**: Das Vorzeichen wechselt zwischen den Varianten, der Effekt ist nicht von null unterscheidbar.
- **Wirkung von S3 auf das unterste Quintil und auf Importe während des Schocks**: Das Vorzeichen wechselt bei geringerer Haushaltsliquidität, niedrigerer Rückführung durch das Ausland und kleiner Population.
- **`min_energy_share`** bindet in diesem Experiment nicht. Ob Haushalte unter 60 % ihres Bedarfs sparen würden, wird hier also gar nicht getestet.
- **Nachfrageregime**: Mit geringerem Haushaltsvermögen (`low_household_wealth`) verdoppeln sich die Beschäftigungs- und Konsumeffekte aller Instrumente ungefähr. Die Ergebnisse hängen stark davon ab, wie nah die Basis an der Kapazitätsgrenze liegt.

## Grenzen, die die Aussagekraft am stärksten einschränken

1. **Energiebedarf, Vermögen und Einkommen sind unabhängig verteilt.** Das bestimmt direkt, wen Transfer und Subvention erreichen. Für den Vergleich S1 gegen S2 ist das die wichtigste offene Annahme.
2. **Keine Liquiditätsnot.** Der Indikator für Versorgungssicherheit (erzwungene Unterversorgung) bleibt bei 0. Haushalte ohne Ersparnisse fehlen, und damit genau die Gruppe, für die Versorgungssicherheit die eigentliche Frage ist.
3. **Kein Wettbewerb unter Energieversorgern** (identische Preise), keine Mengenknappheit, ein einziger Energieträger.
4. **Kaum Insolvenzen.** Firmenaustritte und Kreditausfälle sind in allen Szenarien null. Krisenanfälligkeit und Machtkonzentration lassen sich in diesem Experiment daher praktisch nicht beobachten.
5. **Keine Kalibrierung, keine Validierung an Daten.**

## Nächste Schritte (Vorschlag)

1. **Profile verbessern**: korrelierte Verteilung von Einkommen, Vermögen und Energiebedarf aus einer Haushaltsbefragung; Elastizitäten mit geprüften Quellen. Das wirkt am direktesten auf die Aussagekraft.
2. **Versorgungssicherheit messbar machen**: Haushalte ohne Ersparnisse, Zahlungsrückstände, ggf. Sperren.
3. **v0.2 Entscheidungskomponenten**: Ersatz der Haushaltsregel durch (a) ein statistisches Modell und (b) ein System-1-Modell, jeweils gegen Verbrauchsdaten 2022/23. Dazu der Vergleich, ob sich die Makroergebnisse ändern.
4. **Sensitivität ausbauen**: Morris-Screening; extensive Größen pro Haushalt normieren; alternative Lohnregeln als strukturelle Varianten.
