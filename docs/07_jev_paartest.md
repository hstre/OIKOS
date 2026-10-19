# Kontrollierter Paartest der Jev-Budgetfrage

Stand: 2026-10-19 · Konfiguration: `configs/experiments/jev_pairs.yaml`

> Nur Beobachtung: keine Verbindung zur simulierten Wirtschaft, kein Steuerungsmodus. Alle Haushaltsfälle sind **konstruiert**, keine empirischen Daten. Jevs Scores sind modellinterne Werte; auch gemittelte Scores gelten nicht als menschliche Entscheidungswahrscheinlichkeiten. Übereinstimmung mit der OIKOS-Regel ist kein Kriterium.

## Teil A: Vorab festgelegt (vor der ersten Anfrage committet)

### Fragestellung

Kann Jev wirtschaftlich relevante Informationen über einen Haushalt **konsistent** unterscheiden, also über verschiedene Darstellungen der Frage hinweg und deutlicher als das Rauschen zwischen Wiederholungen?

### Aufbau

- **Fallpaare**: Ein Basishaushalt; je Paar unterscheiden sich die beiden Fälle A und B in genau einem Merkmal. Das verfügbare Geld nach der Energierechnung (Ersparnis + Einkommen − Energierechnung) wird aus den Angaben abgeleitet und ändert sich mit, wo das Merkmal es betrifft (P2, P4, P5).
- **Feste Eurooptionen** 1 200 / 1 500 / 1 800 / 2 100 / 2 400 € für alle Fälle und Paare. Sie enthalten nur Eurobeträge, keine Prozentangaben (diese hatten in T2 die Antworten verschoben). Alle Optionen sind in jedem Fall finanzierbar. Weil die Optionen nicht mit Einkommen, Ersparnis oder anderen Merkmalen skalieren, ist keine Reaktion durch ihre Konstruktion eingebaut.
- **Darstellungskontrollen getrennt von wirtschaftlichen Informationen**:
  - Fünf Reihenfolgen bilden ein lateinisches Quadrat: Jeder Betrag steht genau einmal an jeder Position.
  - Die Kennungen sind neutral (kq, zt, vx, pw, hj). Ihre Zuordnung zu den Beträgen rotiert unabhängig von der Reihenfolge.
  - Fall A und Fall B eines Paars erhalten jeweils dieselbe Darstellung. Jeder Paarunterschied wird so innerhalb einer Darstellung gemessen.
  - Zusätzlich wird jeder Fall einmal mit Darstellung 0 wiederholt; daraus ergibt sich das Rauschen.
- **Umfang**: 6 Paare × 2 Fälle × 5 Darstellungen = 60 Anfragen, dazu 12 Wiederholungen, zusammen 72. Grenzen: höchstens 80 Anfragen und 0,01 USD.
- **Frage**: unverändert wie in allen bisherigen Läufen, also nach dem *wahrscheinlichen* Verhalten des Haushalts, nicht nach empfehlenswertem Verhalten.

### Hypothesen

Alle Vermutungen unten sind **Hypothesen**. Sie stützen sich auf gängige ökonomische Überlegungen, sind in diesem Projekt aber **nicht empirisch geprüft**. Sie legen nur fest, welche Richtung als „wie vermutet“ gilt.

| Paar | Merkmal A → B | Vermutete Reaktion (B − A) | Begründung (Status: Hypothese) |
|---|---|---|---|
| P0 | Straßenname Lindenstraße → Birkenweg | **kein** Unterschied über das Rauschen hinaus | wirtschaftlich irrelevant; Negativkontrolle |
| P1 | sichere → unsichere Beschäftigungsaussicht | niedriger | Vorsichtssparen bei erwartetem Einkommensrisiko |
| P2 | Rücklagen 500 € → 30 000 € | höher | Puffer-Sparen: Mit kleinem Puffer wird eher gespart, mit großem eher ausgegeben |
| P3 | Vormonatsausgaben 1 500 € → 2 300 € | höher | Gewohnheit **oder** Ankereffekt; beide sagen dieselbe Richtung voraus, der Test kann sie nicht trennen |
| P4 | Energiepreis 9 → 18 ct, Rechnung 150 → 300 € | niedriger | Budgetrestriktion: Mehr Geld für Energie lässt weniger für anderes; über die Größe wird nichts vermutet |
| P5 | Nettoeinkommen 1 800 → 3 200 € | höher, aber um weniger als 1 400 € | Konsum steigt mit dem Einkommen, mit marginaler Konsumquote zwischen 0 und 1 |

### Entscheidungsregel

- Primäres Maß je Darstellung j: Δⱼ = score-gewichtetes Budget(B, j) − score-gewichtetes Budget(A, j), in Euro. Das score-gewichtete Budget ist Σ Score × Betrag.
- Rauschen: Median über alle 12 Fälle von |gewichtetes Budget(Wiederholung) − gewichtetes Budget(Darstellung 0)|.
- **„Konsistent unterschieden“**, wenn Δⱼ in allen 5 Darstellungen dasselbe Vorzeichen hat **und** |Median Δⱼ| größer als das Zweifache des Rauschens ist; sonst „nicht konsistent unterschieden“.
- Die Richtung im Vergleich zur Hypothese wird gesondert berichtet: wie vermutet oder entgegengesetzt.
- Für P0 wird „nicht konsistent unterschieden“ erwartet. Fällt P0 anders aus, reagiert Jev auf irrelevante Angaben, und die Aussagekraft der übrigen Paare sinkt.
- Getrennt berichtet werden außerdem:
  - Eurobeträge (gewählt und score-gewichtet);
  - Quoten relativ zum Nettoeinkommen und zum Einkommen nach Energie;
  - gewählte Optionen nach Betrag, Position und Kennung;
  - vollständige Score-Verteilungen und der Totalvariationsabstand zwischen A und B im Vergleich zum Abstand bei Wiederholungen.
- Nach Sichtung der Ergebnisse werden weder Frage, Optionen, Fälle noch Kriterien geändert. Eine Folgeuntersuchung ist ein neuer, vorab festgelegter Test.

## Teil B: Ergebnisse

GitHub-Actions-Run 39334647830 · Code `d4c65ba` (Vorab-Festlegung in `0fca50b`, davor committet) · Rohdaten: `results/jev_pairs/` (Anfragen, Antworten, Modellstand, Kosten, gezeigte Reihenfolge, Kennungen) · Replay: `results/jev_pairs_replay/` (identisch)

### Ablauf

| | |
|---|---|
| Anfragen | 72, alle erfolgreich, 0 Fehler, keine übersprungen |
| Modellstand | durchgehend `typesafe/jev-1.14-20261014` |
| Kosten | 0,00173 USD (Limit 0,01 USD); alle Jev-Läufe zusammen bisher ≈ 0,0096 USD |
| Rauschen (Wiederholung derselben Anfrage) | Median 24 € beim score-gewichteten Budget (Spanne 6–75 €), TVD-Median 0,05 |
| Schwelle der Entscheidungsregel | 2 × 24 € = 48 € |

### Ergebnis nach der vorab festgelegten Regel

| Paar | Merkmal A → B | Hypothese | Δ score-gewichtetes Budget, Median (min…max) | gleiches Vorzeichen | konsistent unterschieden | Richtung gegenüber Hypothese |
|---|---|---|---|---|---|---|
| P0 | Straßenname | kein Unterschied | +6 € (−24…+36) | 3/5 | nein | wie vermutet (Negativkontrolle unauffällig) |
| P1 | sichere → unsichere Beschäftigung | niedriger | **−204 €** (−267…−138) | 5/5 | **ja** | wie vermutet |
| P2 | Rücklagen 500 → 30 000 € | höher | −18 € (−45…−3) | 5/5 | nein (unter 48 €) | kleine Abweichung in Gegenrichtung, unter der Schwelle |
| P3 | Vormonatsausgaben 1 500 → 2 300 € | höher | **+714 €** (+657…+759) | 5/5 | **ja** | wie vermutet |
| P4 | Energiepreis 9 → 18 ct, Rechnung 150 → 300 € | niedriger | +18 € (−18…+27) | 3/5 | nein | nicht unterschieden |
| P5 | Nettoeinkommen 1 800 → 3 200 € | höher, < 1 400 € | **+483 €** (+390…+543) | 5/5 | **ja** | wie vermutet |

### Eurobeträge, Quoten und Score-Verteilungen getrennt

Mittlere Scores je Betrag über die 5 Darstellungen. Sie sind modellintern und keine Entscheidungswahrscheinlichkeiten.

| Fall | 1 200 € | 1 500 € | 1 800 € | 2 100 € | 2 400 € | score-gewichtet (Median der Darstellungen) | Quote netto / nach Energie |
|---|---|---|---|---|---|---|---|
| P0 A Lindenstraße | 0,13 | 0,28 | 0,35 | 0,19 | 0,04 | 1 707 € | 71 % / 76 % |
| P0 B Birkenweg | 0,12 | 0,28 | 0,36 | 0,20 | 0,04 | 1 734 € | 72 % / 77 % |
| P1 A sicher | 0,14 | 0,29 | 0,36 | 0,17 | 0,04 | 1 701 € | 71 % / 76 % |
| P1 B unsicher | 0,36 | 0,38 | 0,17 | 0,07 | 0,02 | 1 497 € | 62 % / 67 % |
| P2 A 500 € Rücklage | 0,09 | 0,22 | 0,40 | 0,24 | 0,03 | 1 797 € | 75 % / 80 % |
| P2 B 30 000 € Rücklage | 0,13 | 0,25 | 0,33 | 0,25 | 0,04 | 1 752 € | 73 % / 78 % |
| P3 A Vormonat 1 500 € | 0,02 | **0,93** | 0,03 | 0,01 | 0,00 | 1 512 € | 63 % / 67 % |
| P3 B Vormonat 2 300 € | 0,01 | 0,01 | 0,02 | 0,50 | 0,47 | 2 226 € | 93 % / 99 % |
| P4 A 9 ct / 150 € | 0,12 | 0,28 | 0,37 | 0,19 | 0,04 | 1 713 € | 71 % / 76 % |
| P4 B 18 ct / 300 € | 0,14 | 0,25 | 0,35 | 0,21 | 0,05 | 1 731 € | 72 % / 82 % |
| P5 A 1 800 € netto | 0,33 | 0,46 | 0,13 | 0,04 | 0,04 | 1 497 € | 83 % / 91 % |
| P5 B 3 200 € netto | 0,07 | 0,14 | 0,24 | 0,30 | 0,26 | 1 977 € | 62 % / 65 % |

Gewählte Optionen nach Betrag, Position und Kennung je Darstellung: `results/jev_pairs/report.md`. Über alle Anfragen verteilen sich die gewählten Positionen ungleich: Position 1 wurde 5-mal gewählt, die Positionen 2–5 15-, 21-, 12- und 19-mal. Durch das lateinische Quadrat wirkt diese Ungleichheit auf A und B gleich und hebt sich im Paarvergleich auf. Auch die Niveaus hängen von der Darstellung ab: Fall P1 A liegt je nach Darstellung zwischen 1 644 € und 1 767 €, eine Spanne deutlich über dem Wiederholungsrauschen. Die **Paarunterschiede** sind dagegen über die Darstellungen stabil.

### Lesart

1. **Jev unterscheidet in diesem Aufbau drei Merkmale konsistent**: unsichere Beschäftigung (niedriger), höhere Vormonatsausgaben (höher) und höheres Einkommen (höher). Alle drei bleiben über fünf ausgewogene Darstellungen bestehen, und die Negativkontrolle P0 ist unauffällig. Damit ist die offene Frage aus `06_jev_robustheit.md` teilweise beantwortet: Bei festen Eurooptionen reagiert Jev auf das Einkommen.
2. **Einkommen (P5):** Ein Mehreinkommen von 1 400 € erhöht das score-gewichtete Budget um 483 €. Das entspräche einer marginalen Konsumquote von rund 0,35 innerhalb des angebotenen Bereichs.
   - Die Quote fällt dabei von 83 % auf 62 % des Nettoeinkommens.
   - Fall B legt 26 % der Scores auf die höchste Option von 2 400 €. Die Reaktion ist also vermutlich durch die Obergrenze des Angebots gedeckelt; der Wert 0,35 ist eine Untergrenze für diesen Aufbau und keine Schätzung einer Konsumquote.
3. **Vormonatsausgaben (P3):** Die Reaktion ist die stärkste im Test.
   - Bei 1 500 € Vormonatsausgaben liegen 93 % der Scores genau auf 1 500 €. Bei 2 300 € verteilen sie sich auf die beiden nächstgelegenen Optionen (2 100 € und 2 400 €); 2 300 € selbst war nicht angeboten.
   - Jev reproduziert also im Wesentlichen den Vormonatswert. Ob das eine Gewohnheitsreaktion oder einen Ankereffekt abbildet, bleibt **offen**, wie vorab festgehalten.
4. **Unsichere Beschäftigung (P1):** −204 € (Quote 71 % → 62 %), in allen Darstellungen. Die unsichere Variante ist ausdrücklich formuliert („may lose the job within the next three months“). Gemessen ist eine Reaktion auf diese Formulierung; wie stark Jev auf schwächere oder indirekte Hinweise reagiert, ist nicht geprüft.
5. **Rücklagen (P2):** Nicht konsistent unterschieden. Der Unterschied beträgt −18 €, hat in allen 5 Darstellungen dasselbe Vorzeichen, bleibt aber unter der Schwelle von 48 €; die Richtung ist der Hypothese entgegengesetzt. Eine Reaktion auf die Höhe der Rücklagen ist in diesem Aufbau nicht nachweisbar.
6. **Energiepreisschock (P4):** Nicht unterschieden (+18 €, Vorzeichen 3/5). Obwohl die Energierechnung um 150 € steigt, ändert Jev das Budget für andere Ausgaben nicht. Die Quote nach Energie steigt dadurch von 76 % auf 82 %. Eine Budgetanpassung an höhere Energiekosten zeigt Jev hier also nicht; die Hypothese wird nicht gestützt.

### Verbleibende Unsicherheit

- **Konstruierte Fälle** um einen einzigen Basishaushalt (2 400 € netto, 6 000 € Rücklagen). Ob die Muster bei anderen Ausgangslagen gelten, ist nicht geprüft.
- **Je Fall und Darstellung eine Abfrage**; das Rauschen ist aus nur 12 Wiederholungen geschätzt. Die Schwelle (2 × Median) ist eine vorab gesetzte Konvention, kein statistischer Test.
- **Optionsbereich** 1 200–2 400 €: Reaktionen über 2 400 € hinaus sind nicht messbar (Deckelung bei P5 und P3 B).
- **Formulierung:** P1 und P3 geben die Information sehr direkt. Eine Reaktion auf explizite Angaben zeigt noch nicht, wie Jev mit indirekter oder widersprüchlicher Information umgeht.
- **Kein empirischer Abgleich:** Die Tests prüfen, ob Jev Informationen konsistent unterscheidet, nicht, ob die Größenordnungen menschlichem Verhalten entsprechen. Die Hypothesen sind als ökonomische Vermutungen formuliert und hier nicht empirisch belegt.
- **Ein Modellstand** (`jev-1.14-20261014`). Mit einer neuen Version kann sich das Verhalten ändern; der Replay-Modus hält diesen Stand fest.

### Was daraus folgt (Vorschläge, nicht gestartet)

- Die Darstellung wirkt auf das Niveau, die Paarunterschiede bleiben stabil. Für spätere Nutzung empfiehlt sich deshalb, über ausgewogene Darstellungen zu mitteln, statt eine einzige Darstellung zu verwenden.
- Ein Steuerungsmodus bleibt zurückgestellt. Zuerst wären nötig:
  - weitere Basishaushalte;
  - ein Optionsbereich, der die Deckelung vermeidet;
  - abgestufte statt binärer Merkmale, etwa mehrere Einkommens- oder Rücklagenniveaus;
  - ein Abgleich der Größenordnungen mit empirischen Konsumquoten im Rahmen der Arbeit an den Haushaltsprofilen.
