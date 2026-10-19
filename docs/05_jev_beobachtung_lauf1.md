# Jev-Beobachtung, Lauf 1: Auswertung

Stand: 2026-10-19 · GitHub-Actions-Run 39262606893 · Code `c541275` · Rohdaten: `results/jev_observe/`, Replay: `results/jev_observe_replay/`

> Beobachtungsmodus: Die v0.1-Regel steuerte die Wirtschaft; Jev beantwortete dieselbe Budgetentscheidung nur protokollierend. 48 Entscheidungen aus einem Lauf (Seed 1, Szenario S0) sind eine Funktionsprüfung, keine statistische Untersuchung. Jevs Scores sind modellinterne Werte, keine empirischen Entscheidungswahrscheinlichkeiten.

## Funktioniert die Anbindung?

Ja, für den getesteten Umfang.

| Prüfung | Ergebnis |
|---|---|
| Testanfrage (ping) | HTTP 200, 1 Versuch, Antwort schemakonform |
| Beobachtungslauf | 48 von 48 Anfragen erfolgreich, 0 Fehler, 0 Wiederholungen nötig |
| Antwortendes Modell | durchgehend `typesafe/jev-1.14-20261014` (Anbieter TypeSafe) |
| Wirtschaft durch Beobachtung unverändert | ja, bitgleich zum reinen Regellauf |
| Replay ohne Netz und ohne Schlüssel | identische Entscheidungen und Kennzahlen |
| Schlüssel in Ausgabedateien | nicht gefunden (Suche nach `sk-or` und `Bearer` in allen Dateien) |

## Kosten und Laufzeit

| | |
|---|---|
| Testanfrage | 639 Eingabetokens, 0,0000268 USD, 4,0 s (erste Anfrage, vermutlich Kaltstart) |
| 48 Entscheidungen | ≈ 640 Eingabetokens je Anfrage, zusammen 0,00129 USD (≈ 0,000027 USD je Entscheidung) |
| Latenz im Lauf | Median 0,21 s, Maximum 0,86 s |
| Gesamtkosten dieses Schritts | ≈ 0,0013 USD |

Hochgerechnet auf eine volle Haushaltsentscheidung im Steuerungsmodus (1 000 Haushalte × 120 Monate × 5 Szenarien × 100 Seeds = 6 · 10⁷ Anfragen) wären das grob 1 600 USD und bei sequenzieller Abfrage rund 150 Tage Laufzeit. Eine direkte Steuerung jeder Einzelentscheidung durch Jev ist also nur für kleine Ensembles oder mit Bündelung bzw. Zwischenspeicherung praktikabel.

## Worin Jevs Entscheidungen abweichen

| | Regel (nächstliegende Option) | Jev |
|---|---|---|
| Gewählte Optionen | b4 (100 %) 40×, b3 (90 %) 4×, b5 (110 %) 4× | b2 (75 %) 31×, b1 (60 %) 17× |
| Übereinstimmung | – | 0 von 48 |
| Abstand in Stufen (Jev − Regel) | – | −1: 2×, −2: 29×, −3: 15×, −4: 2× |
| Medianer Budgetunterschied | – | −27 % |
| Score, den Jev der Regeloption gibt | – | Median 0,04 |
| Konfidenz | – | 0,17 bis 0,50, Median 0,32 |

Beobachtungen:

1. **Jev wählt systematisch deutlich niedrigere Budgets als die Regel.** Die Regel gibt im eingeschwungenen Zustand etwa das ganze Einkommen nach der Energierechnung aus, weil sie für die Stationarität der Wirtschaft so eingestellt ist. Jev wählt 60–75 %, was einer Sparquote von 25–40 % entspräche.
2. **Jevs Ausgabenquote unterscheidet sich kaum zwischen den Lagen.** *(Präzisiert: Das betrifft die Quote. Weil die Optionen proportional zum Einkommen nach Energie konstruiert waren, steigen die absoluten Eurobudgets mit dem Einkommen schon durch den Aufbau. Eine konstante Quote belegt daher keine fehlende Reaktion auf das Einkommen; siehe `06_jev_robustheit.md`, Abschnitt 6.)* Das Muster (b1 ≈ 0,4, b2 ≈ 0,45, Rest klein) ist vor dem Schock (Preis 9 ct), während des Schocks (16,2 ct, Energierechnung bis 346 €) und danach fast gleich. Auch Erwerbslose und Haushalte mit sehr hohen oder sehr niedrigen Ersparnissen unterscheiden sich kaum. Bei einigen Erwerbslosen und Haushalten mit hoher Energierechnung verteilen sich die Scores etwas breiter auf b3/b4. Bei 48 Fällen ist das nicht belastbar.
3. **Die Konfidenz ist niedrig.** Jev trennt im Wesentlichen nur zwischen „niedrig“ und „sehr niedrig“.

## Was daraus folgt und was nicht

- Belegt ist: Die technische Anbindung, die Fehlerbehandlung, das Protokoll und der Replay-Modus funktionieren, und die Kosten sind sehr gering.
- **Nicht** belegt ist, dass Jev menschliches Konsumverhalten abbildet, und ebenso wenig das Gegenteil. Weder Jev noch die Regel wurden an Verhaltensdaten geprüft. Die Regel ist auf Stationarität eingestellt, nicht auf beobachtete Sparquoten.
- Die geringe Reaktion auf die Lage kann am Modell liegen oder an der Frageformulierung. Mögliche Ursachen, die sich prüfen lassen:
  - **Positionseffekt**: b1 steht zuerst. Test mit umgekehrter oder zufälliger Reihenfolge.
  - **Verankerung an den Prozentangaben** in den Optionstexten. Test nur mit Eurobeträgen.
  - **Formulierung** „most likely to set“. Test einer Variante, die nach dem tatsächlichen Ausgabeverhalten im letzten Monat fragt.
  - **Fehlender Kontext**: Der Zustand enthält keine Information über bisherige Ausgaben. Gerade das wäre aber Wissen, das ein Haushalt hat.
- Jeder dieser Tests kostet weniger als 0,01 USD und ändert weder die Wirtschaft noch v0.1. Ein Steuerungsmodus mit Jev sollte erst folgen, wenn klar ist, wovon Jevs Wahl abhängt.

## Vorschlag für den nächsten Schritt (getrennt freizugeben)

1. **Robustheit der Frage**: dieselben 48 Zustände mit drei Varianten (umgekehrte Optionsreihenfolge, nur Eurobeträge, zusätzlich Vormonatsausgaben im Zustand), weiterhin im Beobachtungsmodus, je höchstens 50 Anfragen.
2. **Wiederholbarkeit**: dieselben 48 Anfragen ein zweites Mal live, um die Schwankung der Scores zwischen Läufen zu messen. Laut Dokumentation sind sie nicht deterministisch.
3. Erst danach: Vergleich mit einer empirischen Referenz, etwa Konsumquoten nach Einkommen und Erwerbsstatus aus Haushaltsbefragungen. Das gehört zur separaten Arbeit an den Haushaltsprofilen.
