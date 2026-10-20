# Empirischer Bezug: Datenprüfung und Versuchsdesign

Stand: 2026-10-20 · Konfiguration: `configs/experiments/sce_validation.yaml` · Code: `oikos/empirics/`

> **Vorab festgelegt.** Dieses Dokument und die Konfiguration werden committet, bevor eine Jev-Anfrage gesendet und bevor irgendein Modell auf der Teststichprobe ausgewertet wird. Die OIKOS-Basis bleibt unverändert.

## 1. Gesicherter Teststand

- Der Stand aller bisherigen Jev-Tests ist auf dem Branch `stand/jev-tests-2026-10-19` gesichert (Commit `2c8ce95`).
- Die Hypothesen des Paartests bleiben Hypothesen.
- Ein unverändertes Konsumbudget bei höheren Energiekosten (P4) ist nicht automatisch falsch: Haushalte können stattdessen ihre Ersparnisbildung oder ihre Rücklagen anpassen (Nachtrag in `07_jev_paartest.md`). Genau diese Aufteilung zwischen Konsum, Ersparnis und Verschuldung ist Gegenstand des hier gewählten Prüfziels.

## 2. Datenprüfung

Geprüft am 2026-10-20. „Erreichbar“ heißt: aus dieser Ausführungsumgebung tatsächlich abgerufen bzw. HTTP-Status geprüft.

| Quelle | Zugang | Lizenz / Bedingungen | Einschlägige Variablen | Ebene | Eignung |
|---|---|---|---|---|---|
| **NY Fed Survey of Consumer Expectations (SCE), Household Spending Survey + Kernbefragung** | frei herunterladbar, erreichbar, geladen und geprüft | NY-Fed-Nutzungsbedingungen (Stand 9.6.2023): Nutzung, Kopie, Weitergabe und Bearbeitung erlaubt, mit vorgegebener Quellenangabe und Kennzeichnung von Änderungen; kein Eindruck einer Unterstützung durch die NY Fed | QSP13new/QSP13a: Reaktion auf hypothetischen Einkommensrückgang um 10 % (Ausgaben kürzen, Ersparnis senken, Kredit aufnehmen). QSP12n/12a: dasselbe für +10 %. QSP1/2: selbstberichtete Ausgabenänderung gegenüber dem Vorjahr. Kern: Beschäftigung (Q10), Jobverlust-Wahrscheinlichkeit (Q13new), erwartete Einkommens- und Ausgabenänderung (Q25v2, Q26v2), Wahrscheinlichkeit verpasster Kreditzahlungen (Q30new), Kategorien für Alter, Bildung und Haushaltseinkommen | **individuell**; rotierendes Panel, bis zu 4 Spending-Wellen je Person innerhalb von 12 Monaten; 33 782 Antworten von 15 052 Personen, 12/2014–12/2024 | **geeignet für ein eng abgegrenztes Ziel.** Gemessen werden aber **Selbstauskünfte zu einem hypothetischen Szenario**, kein beobachtetes Verhalten. Population: USA, Online-Panel von Haushaltsvorständen. Genaue Angaben zu Einkommen und Alter sind in den öffentlichen Daten leer, nur Kategorien vorhanden |
| BLS Consumer Expenditure Survey, Public-Use Microdata | aus dieser Umgebung **nicht erreichbar** (HTTP 403) | US-Regierungswerk, nach meinem Kenntnisstand gemeinfrei (nicht geprüft) | vierteljährliche Ausgaben je Haushalt über bis zu 4 Interviews; Einkommen nur in einzelnen Interviews | individuell, kurzes Panel | inhaltlich interessant für **beobachtete** Ausgabenänderungen; Zugang hier nicht möglich |
| PSID (Michigan) | aus dieser Umgebung **nicht erreichbar** (HTTP 403); Registrierung erforderlich | eigene Nutzungsbedingungen, keine freie Weitergabe (nicht geprüft) | Konsum und Einkommen alle zwei Jahre seit 1999 | individuell, langes Panel | beste Grundlage für beobachtete Reaktionen; nicht ohne Registrierung durch dich nutzbar |
| SOEP, EVS, PHF, Bundesbank-Konsumentenbefragung (BOP-HH) | Antrag bei Forschungsdatenzentren (DIW, Destatis/FDZ, Bundesbank RDSC); kein freier Download | Nutzungsvertrag, Weitergabe ausgeschlossen | teils Konsum, Einkommen, Erwartungen, hypothetische Konsumreaktionen (BOP-HH) | individuell | für einen deutschen bzw. europäischen Bezug am besten geeignet; erfordert einen Antrag durch eine berechtigte Institution |

**Fazit der Datenprüfung:** Frei zugängliche individuelle Daten zu *beobachteten* Konsumänderungen nach *beobachteten* Einkommensänderungen habe ich aus dieser Umgebung nicht erhalten. Verfügbar sind individuelle *Selbstauskünfte* der SCE. Das daraus gebildete Prüfziel ist kleiner als „menschliches Konsumverhalten“, aber klar abgegrenzt und überprüfbar.

## 3. Vorhersageziel

**Was wird vorhergesagt?** Die Antwort einer befragten Person auf SCE-Frage QSP13new:

> „Now imagine that next year you were to find yourself with 10% less household income. What would you do?“

Die sieben Antwortkategorien des Fragebogens lassen sich drei Klassen zuordnen. Diese drei Klassen sind das **primäre Ziel**:

| Klasse | Antwortcodes | Anteil im Training (n = 10 133) |
|---|---|---|
| volle Ausgabenkürzung | 1 | 46,0 % |
| teilweise Kürzung (zusätzlich Ersparnis und/oder Kredit) | 4, 5, 7 | 48,4 % |
| keine Ausgabenkürzung (nur Ersparnis und/oder Kredit) | 2, 3, 6 | 5,6 % |

Sekundär werden alle sieben Codes ausgewertet.

**Warum dieses Ziel?**
- **Inhaltlich passend:** Es betrifft genau die offene Frage aus P4, ob Haushalte Einkommensverluste über Konsum, Ersparnis oder Kredit auffangen.
- **Technisch passend:** Es ist eine geschlossene Auswahl, wie Jevs Choice-Fragen, mit großer Fallzahl auf Personenebene und einem klar dokumentierten Wortlaut.

**Was es nicht ist:**
- Kein beobachtetes Verhalten.
- Keine deutsche oder europäische Population.
- Keine Prognose der Größenordnung von Konsumänderungen in Euro.

**Verworfen als primäres Ziel:**
- QSP2, die selbstberichtete tatsächliche Ausgabenänderung gegenüber dem Vorjahr: Sie mischt Preise, Haushaltsänderungen und Einkommen; eine passende gemessene Einkommensänderung liegt in den öffentlichen Daten nicht vor.
- QSP12, die Reaktion auf +10 %: Sie wird für einen späteren, getrennt festgelegten Test zurückgestellt.

## 4. Eingabekontext und Schutz vor Vorabinformation

**Eingaben** (Kernbefragung desselben Monats):
- Altersgruppe, Bildung, Haushaltseinkommen (Kategorie), Beschäftigung;
- Wahrscheinlichkeit des Jobverlusts (nur bei Erwerbstätigen erhoben);
- erwartete Einkommens- und Ausgabenänderung in den nächsten 12 Monaten;
- Wahrscheinlichkeit, eine Kreditzahlung in den nächsten 3 Monaten zu verpassen.

Jev und das Referenzmodell erhalten **dieselben** Informationen.

**Ausgeschlossen:**
- alle Antworten aus dem Spending-Modul, in dem auch das Ziel erfragt wird (u. a. QSP12, QSP13a, QSP1/2);
- Antworten derselben Person aus anderen Wellen;
- Gewichte, Kennungen und Datum.

Ein Test prüft, dass keine dieser Angaben in die Anfrage gelangt.

**Aufteilung** (deterministisch über einen Hash der Personenkennung, eine Zeile je Person: die erste gültige Welle):

| Menge | Definition | n |
|---|---|---|
| Training | erste Spending-Teilnahme vor 01/2022 | 10 133 |
| Anpassung (für Jev) | 400 Trainingspersonen mit Datensatz ab 01/2019 | 400 |
| Pufferjahr | erste Teilnahme 2022: ausgeschlossen | 1 286 |
| Test (versiegelt) | erste Teilnahme ab 01/2023, 800 Personen per Hash | 800 (von 2 401) |

Keine Person liegt in Training und Test zugleich; das ist geprüft.

**Offenlegung, was ich bereits angesehen habe:**
- Bei der Datenprüfung habe ich die Verteilung von QSP13new über **alle** Jahre angesehen, also einschließlich des späteren Testzeitraums (nur Randverteilung).
- Ich habe die Verteilung im Training angesehen.
- Testergebnisse einzelner Personen und Modellauswertungen auf der Teststichprobe gibt es noch nicht.

## 5. Modelle und Auswertung

| Modell | Beschreibung | angepasst auf |
|---|---|---|
| M0 | Klassenhäufigkeiten | Training |
| M1 | multinomiales Logit auf den Kontextvariablen (einfache statistische Referenz) | Training (10 133) |
| M2 | Jev-Scores, auf drei Klassen summiert (roh) | – |
| M3 | Jev kalibriert: Logit auf log M2 | Anpassung (400) |
| M4 | Logit + Jev: Logit auf (kreuzvalidiertes log M1, log M2) | Anpassung (400) |

- **Primäres Kriterium:** Log-Loss(M4) − Log-Loss(M1) auf der Teststichprobe, mit 95-%-Bootstrap-Intervall über Personen (2 000 Ziehungen).
  - **Zusätzlicher Vorhersagenutzen**, wenn die Obergrenze des Intervalls unter 0 liegt.
  - Ein niedrigerer Log-Loss von M2 oder M3 allein reicht nicht.
  - Übereinstimmung mit der OIKOS-Regel spielt keine Rolle.
- **Sekundär:** Brier-Score, Trefferquote, AUC für „überhaupt Kürzung“ und „volle Kürzung“, Log-Loss für sieben Klassen, mittlere vorhergesagte gegenüber beobachteten Anteilen, M3 gegenüber M1.
- **Technische Kontrolle** (Lehre aus den Darstellungstests):
  - **Darstellungen:** vier Reihenfolgen der sieben Antworten (Original, umgekehrt, zwei Verschiebungen) mit neutralen, rotierenden Kennungen. Jede Person erhält eine Darstellung per Hash, ausgewogen verteilt.
  - **Kontrollgruppe:** 40 Anpassungspersonen werden zusätzlich in den drei anderen Darstellungen abgefragt, einmal wiederholt und einmal mit einem irrelevanten Zusatzfeld (Placebo).
  - **Kennzahl:** Berichtet wird der Totalvariationsabstand. Liegt er über die Darstellungen im Median über 0,2, gilt das Ergebnis als darstellungsempfindlich.
- **Jevs Frage:** Wie wahrscheinlich gibt die Person welche Antwort? Gefragt wird nach der *wahrscheinlichen Antwort*, nicht nach empfehlenswertem Verhalten. Auch kalibriert sind die Ergebnisse vorhergesagte Wahrscheinlichkeiten einer Befragungsantwort, keine Wahrscheinlichkeiten tatsächlichen Verhaltens.
- **Umfang und Kosten:** 1 400 Anfragen (400 + 800 + 40 × 5). Eine Beispielanfrage hat rund 1,4 kB, die Schätzung liegt bei 0,035–0,045 USD. Das Limit (0,06 USD) wird vor jeder Anfrage geprüft. **Der Lauf braucht deine Freigabe.**

## 6. Was ein Ergebnis bedeuten würde

| Ergebnis | Bedeutung |
|---|---|
| M4 besser als M1 (Intervall unter 0) | Jev liefert für die Vorhersage *angegebener* Reaktionen auf einen hypothetischen Einkommensverlust Information über eine einfache Statistik mit denselben Angaben hinaus. Ein Entscheidungsmodul könnte dann das kalibrierte M4 nutzen: Aus dem Haushaltskontext ergäbe sich eine Verteilung über die Aufteilung eines Einkommensverlusts auf Konsum, Ersparnis und Kredit. |
| kein Unterschied oder schlechter | Für dieses Ziel bringt Jev keinen Zusatznutzen; ein Entscheidungsmodul sollte die einfache Statistik verwenden. |
| darstellungsempfindlich | Jevs Beitrag hängt von der Präsentation ab; nur das über Darstellungen gemittelte, kalibrierte Ergebnis wäre verwendbar. |

In keinem Fall belegt das Ergebnis, dass Jev oder OIKOS *tatsächliches* Konsumverhalten abbildet. Es bleibt bei angegebenem Verhalten einer US-Stichprobe.

## 7. Verbindung zu OIKOS und Grenzen

- OIKOS-Haushalte haben derzeit keine Konsumentenkredite. Die Kategorie „Kredit aufnehmen“ hätte im Modell keine Entsprechung, das Modul müsste sie zunächst der Ersparnis zuschlagen. Diese Annahme wäre zu dokumentieren.
- Die SCE-Stichprobe ist US-amerikanisch. Für eine europäische Anwendung wäre ein deutscher Datensatz nötig, etwa die BOP-HH der Bundesbank mit ähnlichen hypothetischen Fragen. Dafür wäre ein Datenantrag durch eine berechtigte Institution erforderlich.
- Kleineres Ausweichziel, falls der Lauf nichts ergibt: binär „überhaupt Ausgabenkürzung ja/nein“ (bereits als sekundäre AUC enthalten).

## 8. Reproduzierbarkeit

- **Rohdaten:** Sie werden per Skript geladen (`oikos/empirics/sce.py`), mit festgehaltenen SHA-256-Prüfsummen. Bei geänderten Quelldateien bricht das Skript ab; es rechnet nicht still weiter. Die Rohdaten sind nicht im Repository (`data/sce/` in `.gitignore`).
- **Referenzmodell:** Das multinomiale Logit ist ohne zusätzliche Bibliotheken implementiert und getestet (Bedingung erster Ordnung, Wiedergewinnung bekannter Parameter).
- **Pipeline-Tests:** Sie laufen auf synthetischen Daten, einschließlich Replay, Darstellungsrotation und Prüfung auf Vorabinformation.
- **Workflow:** `.github/workflows/sce-validation.yml` ist vorbereitet und startet durch Push eines Branches `sce-run/<name>`. **Er ist nicht gestartet.**

Quellenangabe: Survey of Consumer Expectations, © 2013-2026 Federal Reserve Bank of New York (FRBNY). Content from the New York Fed subject to the Terms of Use at newyorkfed.org. Die hier verwendeten Daten sind verändert (Auswahl, Umkodierung, eine Zeile je Person). Die FRBNY ist für diese Analyse und Interpretation nicht verantwortlich.
