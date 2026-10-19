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

*(wird nach dem Lauf ergänzt)*
