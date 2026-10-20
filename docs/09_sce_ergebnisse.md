# SCE-Vorhersagetest: Ergebnisse

Stand: 2026-10-20 · GitHub-Actions-Run 39504236760 · Code `2beaf68` (Design vorab festgelegt in `f0206e8`) · Rohdaten der Anfragen: `results/sce_validation/` · Replay: `results/sce_validation_replay/`

> Ziel war die *angegebene* Antwort auf eine hypothetische Frage (SCE QSP13new: Was würden Sie bei 10 % weniger Haushaltseinkommen tun?), nicht beobachtetes Verhalten. Alle Auswertungen folgen der vorab festgelegten Regel in `08_empirischer_bezug.md`. Source: Survey of Consumer Expectations, © 2013-2026 Federal Reserve Bank of New York; modified for this analysis.

## Ablauf

| | |
|---|---|
| Stichproben | Training 10 133 · Anpassung 400 · Test 800 (versiegelt bis zu diesem Lauf) |
| Jev-Anfragen | 1 400, alle erfolgreich, 0 Fehler; Modellstand durchgehend `typesafe/jev-1.14-20261014` |
| Kosten | 0,0393 USD (Limit 0,06 USD) |
| Replay | Der Workflow-Replay war fehlerhaft: Identische Wiederholungsanfragen überschrieben die Hauptantwort im Replay-Speicher. Der Fehler ist behoben und getestet; der neu erzeugte Replay stimmt mit dem Live-Lauf überein (alle Kennzahlen bis auf 1e-6; zwei AUC-Werte von M3 weichen um < 5e-5 ab, wegen Gleichständen bei hardwareabhängiger Rundung). Die Live-Auswertung war nicht betroffen. |

## Primäres Kriterium (vorab festgelegt)

**Log-Loss(M4: Logit + Jev) − Log-Loss(M1: Logit) = −0,0049, 95-%-Intervall [−0,0181; +0,0084].**

Das Intervall schließt null ein. **Kein nachgewiesener zusätzlicher Vorhersagenutzen** von Jev gegenüber der einfachen Statistik mit denselben Angaben.

## Kennzahlen auf der Teststichprobe

Drei Klassen: volle Ausgabenkürzung / teilweise / keine.

| Modell | Log-Loss | Brier | Trefferquote | AUC „überhaupt Kürzung“ | AUC „volle Kürzung“ | mittlere vorhergesagte Anteile |
|---|---|---|---|---|---|---|
| beobachtet | – | – | – | – | – | 41,6 % / 51,1 % / 7,3 % |
| M0 Häufigkeiten | 0,903 | 0,563 | 0,511 | 0,500 | 0,500 | 46,0 / 48,4 / 5,6 |
| M1 Logit | 0,894 | 0,554 | 0,536 | 0,556 | 0,590 | 45,8 / 48,7 / 5,6 |
| M2 Jev roh | 1,115 | 0,662 | 0,522 | 0,475 | 0,541 | 19,2 / 64,6 / 16,3 |
| M3 Jev kalibriert | 0,902 | 0,561 | 0,515 | 0,496 | 0,534 | 40,8 / 53,2 / 6,0 |
| M4 Logit + Jev | 0,889 | 0,550 | 0,534 | 0,550 | 0,591 | 41,1 / 53,0 / 5,9 |

- **Sekundär, sieben Antwortcodes (Log-Loss):** Häufigkeiten 1,270 · Logit 1,226 · Jev roh 1,516.
- **M3 gegenüber M1:** +0,0085 [−0,0064; +0,0236]. Kalibriertes Jev allein ist nicht besser als das Logit, eher schlechter.

## Lesart

1. **Jevs Rohwerte sind deutlich fehlkalibriert.** Jev sagt viel seltener „volle Ausgabenkürzung“ voraus (19 % statt 42 % beobachtet) und viel häufiger „keine Kürzung“ (16 % statt 7 %). Jev unterstellt also mehr Abfederung über Ersparnis und Kredit, als die Befragten angeben. Der Log-Loss liegt deutlich über dem der reinen Häufigkeiten.
2. **Nach Kalibrierung bleibt kaum Information.** Kalibriertes Jev (M3) erreicht etwa das Niveau der reinen Häufigkeiten (0,902 gegenüber 0,903). Die AUC für „überhaupt Kürzung“ liegt bei 0,50, also auf Zufallsniveau. Zusammen mit dem Logit (M4) verbessert sich der Log-Loss nur um 0,005, innerhalb der Unsicherheit.
3. **Die Aufgabe ist auch für die einfache Statistik schwer.** Das Logit schlägt die reinen Häufigkeiten nur knapp (0,894 gegenüber 0,903; AUC 0,56–0,59). Die acht verfügbaren Angaben erklären die Antwort nur schwach. Ein fehlender Zusatznutzen heißt hier also nicht, dass Jev mit mehr oder besseren Informationen nichts beitragen könnte. Mit diesen Informationen trägt es nichts Nachweisbares bei.
4. **Verschiebung zwischen den Zeiträumen.** Im Test (Erstteilnahme 2023/24) geben weniger Befragte eine volle Kürzung an als im Training (41,6 % gegenüber 46,0 %). Die auf Trainingsdaten angepassten Modelle tragen diese Verschiebung nicht. Für ein späteres Modul muss die Kalibrierung zeitlich aktuell gehalten werden.
5. **Darstellung (technische Kontrolle):** Der Abstand zwischen Darstellungen liegt im Median bei 0,12 (Maximum 0,33), bei Wiederholung und Placebo bei 0,04. Die Darstellung wirkt also etwa dreimal so stark wie das Rauschen, bleibt aber unter der vorab festgelegten Schwelle von 0,2. Weil die Darstellungen ausgewogen verteilt waren, mittelt sich ihr Einfluss in der Auswertung.
6. **Bezug zu P4 (nur als Beobachtung):** Im Paartest ließ Jev das übrige Budget bei höheren Energiekosten unverändert. Hier sagt Jev systematisch weniger Ausgabenkürzungen voraus, als Befragte für einen Einkommensverlust angeben. Beides weist in dieselbe Richtung; die Aufgaben sind aber verschieden, und das ist kein Nachweis eines allgemeinen Musters.

## Was daraus für das Entscheidungsmodul folgt

- Für diese Entscheidung, also die Aufteilung eines Einkommensverlusts auf Konsum, Ersparnis und Kredit, ist ein Jev-Baustein **nicht begründet**.
- Als empirisch prüfbare Grundlage eignet sich die einfache Statistik (M1). Sie ist auf Daten außerhalb der Anpassung geprüft und schlägt die Häufigkeiten knapp. Ihr Vorhersagewert ist allerdings gering.
- Die Ergebnisse betreffen angegebenes Verhalten einer US-Stichprobe. Auf deutsche bzw. europäische Haushalte und auf tatsächliches Verhalten übertragen lassen sie sich nicht ohne Weiteres.

## Verbleibende Unsicherheit

- Eine Frageformulierung an Jev, ein Modellstand, eine Teststichprobe von 800.
- Das Intervall des Hauptkriteriums reicht von −0,018 bis +0,008: Ein kleiner Nutzen ist nicht ausgeschlossen, aber auch nicht gezeigt.
- Andere Formulierungen oder mehr Kontext (etwa Vermögen, Schulden, Haushaltsgröße) wurden nicht geprüft. Sie wären ein neuer, vorab festzulegender Test.

## Vorschläge (nicht gestartet)

1. **Entscheidungsmodul v0.2 auf Basis von M1**: Es bildet den Haushaltskontext auf eine Verteilung über die Reaktion auf einen Einkommensverlust ab, mit dokumentierter Abbildung auf OIKOS (dort gibt es keine Konsumentenkredite; die Kreditkategorie würde der Ersparnis zugeschlagen) und einer Kalibrierung auf den jüngsten Zeitraum. Einbau in OIKOS nur als getrennte Variante, die v0.1-Referenz bleibt unverändert.
2. **Europäischer Bezug**: Datenantrag für die Konsumentenbefragung der Bundesbank (BOP-HH) über eine berechtigte Institution.
3. **Weitere Jev-Tests** nur mit neuem, vorab festgelegtem Ziel, bei dem mehr Kontextinformation verfügbar ist.
