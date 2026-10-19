# Jev-Robustheitstests der Budgetfrage: Auswertung

Stand: 2026-10-19 · GitHub-Actions-Run 39332087964 · Code `4023d2a` · Rohdaten: `results/jev_robustness/` (je Test eine JSONL-Datei mit Anfrage, Antwort, Modellstand, Kosten, gezeigter Reihenfolge), Replay: `results/jev_robustness_replay/`

> Präzisiert am 2026-10-19: Ausgabenquote und absolute Ausgaben getrennt (Abschnitt 6); Deutung von T3 offen.
>
> Nur Beobachtungsmodus. Die Wirtschaft wurde nicht verändert und Jev hat nichts gesteuert. Alle Tests verwenden dieselben 48 Haushaltszustände wie der erste Lauf; die Zustände wurden aus dem Regellauf rekonstruiert und bytegleich gegen die gespeicherten Anfragen geprüft. Je Test wurde genau ein Faktor verändert. Jevs Scores sind modellinterne Werte, keine empirischen Entscheidungswahrscheinlichkeiten. Übereinstimmung mit der Regel ist kein Kriterium.

## Ablauf und Kosten

| | |
|---|---|
| Anfragen | 5 Tests × 48 = 240, alle erfolgreich, 0 Fehler, 0 wegen Kostenlimit übersprungen |
| Modellstand | durchgehend `typesafe/jev-1.14-20261014` |
| Kosten | 0,00654 USD (Limit 0,01 USD; zusammen mit Lauf 1 bisher ≈ 0,0078 USD) |
| Replay ohne Netz | identische Ergebnisse |
| Zugangsdaten in Dateien | keine gefunden |

Ein erster Startversuch scheiterte vor jeder Anfrage, ohne Kosten: Der v0.1-Referenztest schlug auf einem Runner ohne AVX-512 fehl. Die Ursache sind hardwareabhängige Rundungen in numpy (siehe `04_jev_anbindung.md`). Der Test prüft seitdem überall mit Toleranz und nur auf passender Hardware bitgenau.

## Ergebnisse

„Anteil“ ist das Budget relativ zum Einkommen nach der Energierechnung. „Score-gewichteter Anteil“ ist Σ Score × Betrag / Einkommen nach Energie, eine Zusammenfassung der ganzen Score-Verteilung. TVD ist der Totalvariationsabstand zwischen den Score-Verteilungen über dieselben Eurobeträge (0 = identisch, 1 = disjunkt).

| Test (ein Faktor geändert) | score-gewichteter Anteil Median (10–90 %) | gleiches €-Budget wie Original | TVD zum Original Median / Max |
|---|---|---|---|
| Original (Lauf 1) | 72 % (70–76 %) | – | – |
| **T5 erneute Live-Abfrage** (unverändert) | 72 % (71–76 %) | 81 % | **0,04** / 0,15 |
| T1 umgekehrte Reihenfolge | 81 % (79–83 %) | 19 % | 0,32 / 0,51 |
| T2 nur Eurobeträge, ohne Prozente | 80 % (78–82 %) | 56 % | 0,25 / 0,43 |
| T3 mit Vormonatsausgaben (synthetisch) | 90 % (83–93 %) | 8 % | 0,63 / 0,78 |
| T4 breiteres Angebot (30–110 %) | 60 % (58–63 %) | 38 % | – (andere Optionsmenge) |

Mittlere Score-Masse nach Budgetanteil:

| | < 55 % | 55–65 % | 65–80 % | 80–95 % | ≥ 95 % |
|---|---|---|---|---|---|
| Original | – (nicht angeboten) | 38 % | 43 % | 12 % | 6 % |
| T5 | – | 38 % | 43 % | 12 % | 7 % |
| T1 | – | 20 % | 31 % | 38 % | 12 % |
| T2 | – | 20 % | 37 % | 28 % | 15 % |
| T3 | – | 6 % | 21 % | 37 % | 35 % |
| T4 | 36 % | 31 % | 24 % | 5 % | 4 % |

### 1. Wiederholung (T5): Grundrauschen

Dieselben Anfragen ergeben fast dieselben Scores: Die absolute Abweichung je Option beträgt im Mittel 0,018, maximal 0,10; nur 1 von 48 Score-Vektoren ist exakt gleich. In 19 % der Fälle kippt die gewählte Option, weil die beiden führenden Optionen (60 % und 75 %) nahe beieinander liegen. Alle anderen Unterschiede sind an diesem Rauschen zu messen (TVD-Median 0,04).

### 2. Reihenfolge (T1): deutlicher Darstellungseffekt

Mittlerer Score nach gezeigter **Position**:

| Position | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Original (b1 … b5 = 60 … 110 %) | 0,38 | 0,43 | 0,12 | 0,05 | 0,01 |
| T1 (b5 … b1 = 110 … 60 %) | 0,02 | 0,09 | 0,38 | 0,31 | 0,20 |

Nach **Kennung bzw. Betrag** ergibt das in T1: b1 (60 %) 0,20, b2 (75 %) 0,31, b3 (90 %) 0,38, b4 (100 %) 0,09, b5 (110 %) 0,02. Gewählt wurden b3 34-mal, b2 12-mal, b1 2-mal.

- Jev folgt weder rein der Position (dann läge die Masse bei Position 1 = 110 %) noch rein dem Betrag (dann bliebe die Verteilung über die Beträge gleich).
- Die Masse verschiebt sich durch die Umkehr deutlich zu höheren Budgets, im Median um 9 Prozentpunkte; der TVD von 0,32 liegt rund achtmal über dem Rauschen.
- Hohe Budgets (100–110 %) bleiben in beiden Reihenfolgen unattraktiv.
- Kennungen und Beträge blieben gekoppelt. Ob die Kennungen b1…b5 selbst wirken, lässt sich daraus nicht trennen.

### 3. Prozentangaben (T2): deutlicher Darstellungseffekt

Ohne Prozentangaben verschiebt sich die Masse ebenfalls nach oben: score-gewichtet 80 % statt 72 %, TVD 0,25. Die Angabe „about 60 % of the income …“ zieht die Antworten also nach unten. Die Prozentwerte sind eine Umrechnung derselben Information; eine Reaktion darauf ist eine Reaktion auf die Darstellung.

### 4. Vormonatsausgaben (T3): starke Reaktion, Deutung offen

Mit den Vormonatsausgaben aus dem Regellauf liegt die Masse bei 90 %, mit dem größten Abstand aller Tests (TVD 0,63). Diese Ausgaben entsprechen im Median 100 % des Einkommens nach Energie. Jevs score-gewichtetes Budget liegt im Median bei 91 % dieses Vormonatswerts. Jevs Antwort richtet sich also stark nach der vorgegebenen Geschichte. **Offen** ist, ob das eine Gewohnheitsreaktion ist (Haushalte halten ihr Ausgabenniveau) oder ein Ankereffekt (eine genannte Zahl zieht die Antwort an). Beide Deutungen sagen hier dieselbe Richtung voraus; der Test kann sie nicht unterscheiden.

Innerhalb von T3 korreliert die Antwort nicht positiv mit der Höhe der individuellen Vormonatsausgabe (Korrelation der Anteile −0,30). Die Verschiebung betrifft also das Niveau, nicht die Feinabstimmung je Haushalt.

Die Vormonatsausgaben sind **synthetische Modellgeschichte, keine empirischen Haushaltsdaten**. Das ist in jeder Anfrage (`history_note`) und im Log (`history_is_synthetic`) vermerkt. Der Hinweis selbst ist Teil des geänderten Faktors.

### 5. Breiteres Angebot (T4): Bereichseffekt, kein Sammeln am Rand

- Mit zusätzlichen Optionen von 30 % und 45 % sinkt der score-gewichtete Anteil von 72 % auf 60 %.
- Die neue unterste Option (30 %) erhält im Mittel nur 0,11, die 45-%-Option 0,25. Gewählt wurde meist 60 % (30-mal), dann 45 % (11-mal) und 75 % (7-mal).
- Die Antworten sammeln sich also **nicht** am unteren Rand. Sie wandern aber mit dem angebotenen Bereich nach unten, etwa um 12 Prozentpunkte.
- Im ursprünglichen Angebot lag die meiste Masse auf den beiden untersten Optionen. Das war zum Teil eine Folge dieses Angebots, nicht nur eine Aussage über das gewünschte Budget.

### 6. Reaktion auf die Lage des Haushalts: was diese Daten zeigen können und was nicht

Ausgabenquote und absolute Ausgaben sind zu unterscheiden. Die Optionen waren als Anteile des Einkommens nach Energie konstruiert (60 % … 110 %). Damit skalieren alle angebotenen Eurobeträge bereits mit dem Einkommen:

- **Absolute Ausgaben:** Jevs score-gewichtetes Eurobudget reicht von 1 249 € bis 6 609 € (Median 1 535 €) und steigt fast proportional mit dem Einkommen nach Energie (log-log-Steigung 0,99, Korrelation mit dem Nettoeinkommen 1,00). Diese Proportionalität ist **durch die Optionen vorgegeben**: Schon die niedrigste Option hat die Steigung 1,00. Über die Einkommensreaktion sagt dieses Ergebnis deshalb nichts aus.
- **Ausgabenquote:** Die Quote (Budget relativ zum Einkommen nach Energie) ist nahezu konstant (Standardabweichung über die 48 Haushalte 0,023). Wegen der proportionalen Optionen ist eine konstante Quote mit sehr unterschiedlichen absoluten Reaktionen vereinbar. Sie belegt **keine** fehlende Reaktion auf das Einkommen.
- **Andere Merkmale:** Auch Unterschiede nach Ersparnis, Erwerbsstatus und Energiepreisschock sind in diesem Aufbau nur als Quote messbar, und die Quote unterscheidet sich zwischen diesen Gruppen kaum. Im Schock sind die Eurobudgets im Median etwas niedriger (1 518 € gegenüber 1 539 €), weil das Einkommen nach Energie niedriger ist (2 119 € gegenüber 2 146 €), nicht wegen einer anderen Quote.
- **Beobachtungsdaten statt Experiment:** Die 48 Haushalte unterscheiden sich in mehreren Merkmalen zugleich (Einkommen, Ersparnis, Energierechnung, Erwerbsstatus), und die Gruppen sind klein (Erwerbslose n = 7). Ob Jev einzelne Informationen unterscheiden kann, lässt sich damit nicht feststellen. Dafür ist ein kontrollierter Test mit festen Eurooptionen und gezielt variierten Merkmalen nötig (`07_jev_paartest.md`).
- **Eine reproduzierte Korrelation:** Die Quote korreliert positiv mit dem Energiekostenanteil am Einkommen (0,49 im Original, 0,48 in T5). Eine mögliche Lesart: Jev senkt das Eurobudget weniger als eins zu eins mit der Energierechnung. Bei 2 Prozentpunkten Spannweite und 48 Fällen ist das ein schwacher Hinweis.

## Zusammenfassung

| Frage | Befund | Sicherheit |
|---|---|---|
| Sind Jevs Antworten wiederholbar? | weitgehend: kleine Score-Schwankungen (TVD ≈ 0,04), bei knappen Fällen kippt die Wahl (19 %) | mittel (eine Wiederholung) |
| Reagiert Jev auf die Darstellung? | ja, deutlich: Reihenfolge (TVD 0,32), Prozentangaben (0,25), Optionsbereich (−12 Pp.) | hoch für diese Frage und diesen Modellstand |
| Sammeln sich die Antworten am unteren Rand? | nein; sie verschieben sich aber mit dem Angebot | mittel |
| Reagiert Jev auf Informationen über den Haushalt? | mit diesem Aufbau nicht feststellbar: Einkommensreaktion durch proportionale Optionen verdeckt; Quote nach Ersparnis, Erwerbsstatus, Energiepreis kaum verschieden (beobachtet, nicht kontrolliert); stark auf vorgegebene Vormonatsausgaben (Gewohnheit oder Anker, offen) | gering; n = 48, Merkmale nicht getrennt variiert |

**Insgesamt:** Für diese Frageform ist belegt, dass die Darstellung (Reihenfolge, Prozentangaben, Optionsbereich) die Antwort deutlich verschiebt, um ein Mehrfaches des Rauschens. Ob Jev wirtschaftliche Informationen über den Haushalt unterscheiden kann, ist mit diesem Aufbau **nicht entschieden**: Die Optionen skalierten mit dem Einkommen, und die Merkmale wurden nicht getrennt variiert. Die Frage in dieser Form ist keine tragfähige Grundlage für einen Steuerungsmodus.

## Verbleibende Unsicherheit

- **Begrenzte Daten:** ein Modellstand, ein Seed, 48 Zustände, je Test eine Abfrage. Gruppenvergleiche stehen auf sehr kleinen Zahlen (Erwerbslose n = 7).
- **Kennungseffekte** sind nicht getrennt. In T1 blieben b1…b5 an die Beträge gebunden, in T4 bezeichnen dieselben Kennungen andere Beträge.
- **Gewohnheit oder Anker?** Ob T3 eine Gewohnheitsreaktion oder einen Ankereffekt zeigt, bleibt offen; beide sagen dieselbe Richtung voraus. Der Wert stammt aus dem Regellauf und ist selbst nicht empirisch.
- **Darstellungseffekte könnten sich überlagern.** Reihenfolge, Prozentangaben und Bereich wirken in dieselbe Richtung. Wie stark sie zusammen wirken, ist nicht getestet.
- **Kein Bezug zu echtem Verhalten:** Kein Ergebnis sagt, welche Budgetwahl realistischer ist. Dafür braucht es empirische Referenzen wie Konsumquoten nach Gruppen. Das gehört zur separaten Arbeit an den Haushaltsprofilen.

## Mögliche nächste Schritte (nicht gestartet)

1. Neutrale, zufällige Optionskennungen und zufällige Reihenfolge je Anfrage, um Kennungs- und Positionseffekte zu trennen bzw. auszumitteln.
2. Mehrere Darstellungen je Zustand, mit dem Mittel über die Darstellungen als Antwort. So lässt sich prüfen, ob Unterschiede zwischen Haushalten dann sichtbar werden.
3. Erst danach eine Gegenüberstellung mit empirischen Konsumquoten. Ein Steuerungsmodus bleibt zurückgestellt.
