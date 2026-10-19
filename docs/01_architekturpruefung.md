# OIKOS – Architekturprüfung und Prototyp-Definition

*Offenes Labor für Wirtschaft und Gesellschaft – „Regeln verändern. Wechselwirkungen verstehen.“*

Stand: 2026-10-19 · Status: Arbeitsentwurf, Grundlage für Prototyp v0.1

---

## 0. Kurzfassung

1. **Die Kernidee trägt**: Buchführung, institutionelle Regeln und Verhalten werden in getrennte Schichten gelegt. Die Akteure sind heterogen, teilen sich aber Entscheidungsmodelle. Am Anfang steht ein regelbasiertes Basismodell, dessen Komponenten danach einzeln ersetzt und geprüft werden. Dieser Aufbau entspricht dem Stand der agentenbasierten, bestandsflusskonsistenten Makroökonomik (AB-SFC) und ist methodisch sauber.
2. **Drei Annahmen sind nicht belegt** und tragen viel Gewicht:
   a) dass LLM-Akteure menschliches Wirtschaftsverhalten realistischer abbilden als kalibrierte einfache Regeln;
   b) dass Millionen Akteure einen Erkenntnisgewinn bringen;
   c) dass sich die GPU-Analogie auf gekoppelte Märkte übertragen lässt.
   Keine davon ist widerlegt, aber alle drei müssen im Projekt geprüft werden. Voraussetzen darf man sie nicht.
3. **Die größten Schwierigkeiten liegen woanders, als die Idee nahelegt.** Die LLM-Anbindung ist technisch der einfachere Teil. Schwierig sind:
   - konsistente Buchführung mit endogener Geldschöpfung;
   - explizite Marktprotokolle;
   - der faire Vergleich von Szenarien;
   - Reproduzierbarkeit bei LLM-Aufrufen;
   - die Kalibrierung bei wenigen Daten und vielen Parametern.
4. **Empfehlung zur Grundlage**: ein **eigener schlanker Kern in Python/NumPy unter MIT-Lizenz**. AgentTorch, AgentSociety und Concordia eignen sich nicht als Fundament. Keines der drei Projekte hat eine doppelte Buchführung mit Bilanzen und Geldschöpfung. AgentTorch steht zudem unter AGPL-3.0. Einzelne Muster daraus übernehmen wir gezielt (siehe Abschnitt 4).
5. **Kleinster sinnvoller Prototyp (v0.1)**:
   - Akteure: 1 000 Haushalte, zwei Branchen (Konsumgüter, Energie), eine Bank, ein Staat und ein explizites Ausland.
   - Zeitschritt: ein Monat.
   - Verhalten und Buchführung: nur Regeln, Buchführung ganzzahlig und doppelt.
   - Erstes Experiment: Energiepreisschock mit vier Szenarien bei **gleichem fiskalischem Budget**, gemeinsamen Zufallszahlen und 100 Zufallsstarts je Szenario.
   - Ab v0.2 werden LLMs auf eine einzige Entscheidung angesetzt, die Energie- und Konsumentscheidung der Haushalte.

---

## 1. Tragfähige Bestandteile

| Element | Bewertung | Begründung |
|---|---|---|
| Trennung Buchführung / Institutionen / Verhalten | **tragfähig, zentral** | Nur so lassen sich Regeln austauschen, ohne dass Verhaltensannahmen unbemerkt mitwandern. Entspricht AB-SFC-Modellen (z. B. Caiani et al. 2016; Godley & Lavoie 2007 für die Bilanzlogik). |
| Pro Entscheidung das einfachste geeignete Modell | **tragfähig** | Für die meisten Entscheidungen in einem Monatsmodell genügen Regeln oder statistische Modelle. Ein LLM muss seinen Mehrwert erst nachweisen. |
| Geteilte Modelle, individueller Zustand | **tragfähig, Standard** | So arbeiten vektorisierte ABMs ohnehin: eine Entscheidungsfunktion, ein Zustands-Array. Auch bei LLMs ist das sinnvoll (ein Modell, viele Kontexte). |
| Ereignis- und periodengesteuerte teure Entscheidungen | **tragfähig** | Reduziert den Rechenaufwand um Größenordnungen. Die Auslöseregeln sind dann aber selbst Modellannahmen und müssen dokumentiert und variiert werden. |
| Erst Basismodell, dann Komponententausch | **tragfähig, methodisch entscheidend** | Nur so lässt sich der Beitrag einer KI-Komponente messen (Ablation). |
| Verteilungen statt Einzelläufe, vier Prüfebenen | **tragfähig** | Entspricht guter Praxis (Verifikation → Mechanismus → Mikrovalidierung → Makrovalidierung). |
| Explizite Quellen- und Unsicherheitsangaben in Profilen | **tragfähig** | Das ist eher eine Datenmodell-Disziplin als eine KI-Frage und lässt sich ab Tag 1 umsetzen. |

## 2. Unbelegte Annahmen

### 2.1 „LLM-Akteure verhalten sich realistischer“
Die Evidenz ist gemischt:
- **Positiv**: Klassische verhaltensökonomische Experimente werden teils qualitativ reproduziert (Horton 2023, „Homo silicus“; Aher, Arriaga & Kalai 2023). Mit demografischer Konditionierung lassen sich Umfrageverteilungen teilweise annähern (Argyle et al. 2023). Speziell für Makrosimulation existiert EconAgent (Li et al. 2024).
- **Bekannte Probleme**:
  - zu geringe Streuung, d. h. stereotype oder „überrationale“ Antworten;
  - hohe Empfindlichkeit gegenüber der Formulierung des Prompts;
  - Verzerrung zugunsten englischsprachiger, westlicher Populationen (Santurkar et al. 2023);
  - mögliche Kontamination, weil bekannte Experimente in den Trainingsdaten vorkommen;
  - fehlende Konsistenz über die Zeit.
- **Für die Zielgruppe besonders kritisch**: Über informelle Ökonomien, informelle Kredite oder Haushalte in ärmeren Ländern gibt es in den Trainingsdaten wenig. Gerade dort ist die Gefahr plausibel klingender, aber erfundener Verhaltensmuster am größten.

**Folgerung**: Ein LLM ist eine Hypothese über Verhalten wie jede andere Regel auch. Es wird an denselben Mikrodaten gemessen und muss gegen kalibrierte Regeln bestehen.

### 2.2 „Millionen Akteure“
Makrodynamiken in AB-SFC-Modellen stabilisieren sich meist schon bei einigen Tausend Akteuren. Mehr Akteure verringern das Rauschen, machen das Modell aber nicht gültiger. Wirklich nützlich wird große Zahl erst bei räumlichen oder feinen Verteilungsfragen mit realen Mikrodaten (synthetische Bevölkerung). Statt einer Skalierung um jeden Preis nimmt die Architektur deshalb zwei Vorgaben auf:
- Der Zustand liegt in Arrays, sodass sich die Simulation später ohne Umbau vektorisieren lässt.
- In Experimenten wird geprüft, ab welcher Populationsgröße sich die Ergebnisse nicht mehr ändern (Konvergenztest).

### 2.3 GPU-Analogie
GPUs sind schnell, weil die Teilaufgaben gleichartig und **unabhängig** sind. Märkte koppeln die Akteure dagegen. Bei Rationierung, Matching und Zahlungsabwicklung zählt die Reihenfolge, und die Konsistenz ist eine globale Bedingung. Die Analogie trägt deshalb nur für den **Entscheidungsschritt**, wo viele Akteure gebündelt und parallel entscheiden. Für die **Interaktion** trägt sie nicht: Die Marktprozesse laufen sequenziell oder in definierten Runden. Das ist kein Problem, solange man es von vornherein so plant.

### 2.4 Konfidenz und Verhaltenswahrscheinlichkeit
Wie in der Projektbeschreibung festgehalten: Token-Wahrscheinlichkeiten eines LLM sind keine Entscheidungshäufigkeiten von Menschen. Jede Ausgabe mit Wahrscheinlichkeitscharakter muss deshalb ihre Semantik deklarieren (siehe Schnittstelle in 5.4). Erst eine Kalibrierung an beobachteten Wahlhäufigkeiten macht daraus eine Verhaltenswahrscheinlichkeit.

### 2.5 LLM-gestützte Literaturerschließung
Zwei Risiken stehen hier im Vordergrund:
1. **Erfundene Quellen.** Jede Quelle muss automatisch gegen DOI- oder Katalogdaten geprüft werden.
2. **Die Übersetzung qualitativer Befunde in Modellparameter.** Ein Beispiel: Aus „Vertrauen beeinflusst informelle Kreditvergabe“ wird „Kreditwahrscheinlichkeit × 1,3“. Dieser Schritt ist eine **Modellierungsentscheidung** und muss im Profil als „Annahme“ gekennzeichnet sein, nicht als „Beleg“.

### 2.6 Destillation großer in kleine Modelle
Destillation funktioniert technisch für eng umrissene Aufgaben. Dabei übernimmt das kleine Modell aber auch die Verzerrungen des großen. Sinnvoll ist sie deshalb erst, nachdem das Lehrermodell an Verhaltensdaten geprüft wurde.

### 2.7 Spannung: offene Sprachmodelle und geschlossener Handlungsraum
Die Buchführung verlangt einen geschlossenen, typisierten Handlungsraum. Ein LLM wählt deshalb nur unter erlaubten, parametrisierten Aktionen. Damit fällt ein Teil seines vermuteten Vorteils weg, nämlich die offene Kreativität. Die prüfbare Frage lautet dann: Wählt ein LLM aus diesem Raum besser als ein kalibriertes Logit-Modell? Diese Frage ist gut beantwortbar, und genau das ist das Ziel.

## 3. Die größten Schwierigkeiten

### Technisch

1. **Bestandsflusskonsistenz mit Banken.**
   - Ein Kredit erzeugt gleichzeitig eine Forderung der Bank und eine Einlage des Kreditnehmers. Tilgung vernichtet beides, ein Ausfall vernichtet die Forderung zulasten des Bankkapitals.
   - Lösung: doppelte Buchführung in **ganzzahligen Cent-Beträgen**. Die Invarianten werden in jedem Schritt geprüft und brechen den Lauf bei Verletzung ab.
   - Die Vergleichsprojekte buchen dagegen einseitig (siehe 4).
2. **Marktprotokolle und Reihenfolge.**
   - Ohne Gleichgewichtsannahme braucht es explizite Regeln: Wer setzt Preise? Wer wird rationiert? In welcher Reihenfolge besuchen Käufer Anbieter?
   - Diese Regeln beeinflussen die Ergebnisse oft stärker als die Parameter. Sie gehören deshalb in die Institutionenschicht und in die Sensitivitätsanalyse.
3. **Fairer Szenarienvergleich.**
   - Szenarien müssen dieselben Zufallszahlen verwenden (*common random numbers*). Sonst überlagert Rauschen den Politikeffekt.
   - Die verglichenen Instrumente brauchen eine gleiche Bezugsgröße, etwa dasselbe Budget.
   - Der Ausgangszustand muss nach einer Einschwingphase quasistationär sein.
4. **Reproduzierbarkeit mit LLMs.**
   - LLM-Ausgaben sind auch bei Temperatur 0 nicht garantiert deterministisch: Batching und Hardware spielen hinein, API-Modelle ändern sich.
   - Lösung: Jeder Aufruf wird mit dem Hash von Modell, Gewichten, Prompt und Sampling-Parametern gecacht. Ein Experiment lässt sich dann exakt aus dem Cache wiederholen.
5. **Rechenkosten.** Größenordnung für v0.1:

   1 000 Haushalte × 120 Monate × 4 Szenarien × 100 Zufallsstarts = **48 Mio. Haushaltsentscheidungen**.

   | Entscheidungsmodell | Aufwand |
   |---|---|
   | Regeln | Sekunden pro Lauf |
   | LLM pro Haushalt | grob 10⁷ Aufrufe, für ein Labor mit begrenzten Mitteln nicht machbar |
   | LLM mit 20 Archetypen pro Monat | ≈ 10⁶ Aufrufe, machbar, aber teuer, und eine zusätzliche Näherung, deren Fehler gemessen werden muss |

   Folgen:
   - LLM-Varianten laufen auf kleineren Ensembles.
   - Globale Sensitivitätsanalysen (Morris, Sobol) sind praktisch nur für das Regelmodell möglich.
6. **Zugänglichkeit.** Das Ziel „Universitäten und Kommunen mit begrenzten Mitteln“ wird zur harten technischen Bedingung: Das Basismodell muss auf einem gewöhnlichen Laptop ohne GPU und ohne kostenpflichtige API laufen. LLM-Komponenten bleiben optional.

### Wissenschaftlich

1. **Identifikation und Kalibrierung.** Viele Parameter stehen wenigen Makrodaten gegenüber. Dadurch erzeugen oft mehrere Parametersätze dieselben Daten (Äquifinalität). Kalibrierte, gesetzte und freie Parameter müssen deshalb getrennt ausgewiesen werden.
2. **Strukturelle Unsicherheit.** Alternative Marktprotokolle und Verhaltensregeln gehören zur Sensitivitätsanalyse, nicht nur Parameterwerte.
3. **Veränderte Regeln verändern Verhalten** (analog zur Lucas-Kritik). Regeln, die unter dem alten Regime angepasst wurden, gelten unter neuen Institutionen nicht automatisch weiter. LLMs lösen das nicht von selbst. Ob sie sich plausibel anpassen, ist eine prüfbare Frage.
4. **Validierungsdaten.** Für das Energieexperiment bietet die europäische Energiekrise 2022/23 ein natürliches Experiment, z. B. Entlastungspakete und die Gas- und Strompreisbremse in Deutschland oder den französischen Preisdeckel. Für ärmere Länder braucht es andere Quellen, etwa Haushaltssurveys wie die LSMS der Weltbank.
5. **Fehlinterpretation als Prognose.** Die Ausgaben werden deshalb so gestaltet, dass sie bedingte Aussagen erzwingen: Annahmen, Bandbreiten und Sensitivität erscheinen im Ergebnis selbst.

## 4. Prüfung der vorhandenen Arbeit

Für diese Prüfung wurde der Code im aktuellen Stand der Hauptzweige gelesen (Stand 19.10.2026), nicht nur die Selbstbeschreibungen.

### AgentTorch (AgentTorch/AgentTorch)
- **Lizenz**: **AGPL-3.0-or-later**, zusätzlich wird eine kommerzielle Lizenz angeboten. Würde OIKOS darauf aufbauen, müsste OIKOS als Gesamtwerk unter AGPL stehen. Das widerspricht dem gewählten MIT-Modell, ist aber nicht per se schlecht.
- **Implementiert**:
  - Tensor- bzw. PyTorch-basierte Simulation großer Populationen, differenzierbar und mit Gradienten-Kalibrierung;
  - ein „Archetype“-Mechanismus: wenige LLM-Aufrufe pro Gruppe, deren Ergebnis auf die Population verteilt wird.
- **Demonstriert**: Epidemie- und Arbeitsmarktmodelle (COVID in NYC) im zugehörigen Paper (Chopra et al., „On the limits of agency in agent-based models“).
- **Befund im Makroökonomie-Beispiel** (`models/macro_economics`):
  - Beim Konsum werden die Vermögen mit einem Zufallsfaktor multipliziert (`assets * torch.rand(1)`). Geld verschwindet also ohne Gegenbuchung.
  - Es gibt keine Bank- oder Staatsbilanz. Der Zins kommt aus einer Taylor-Regel, nicht aus Bilanzen.
  - Die Importe verweisen auf einen alten Paketnamen (`AgentTorch.*` statt `agent_torch`). Das Beispiel ist ohne Anpassung vermutlich nicht lauffähig; ausgeführt wurde es nicht.
- **Eignung für OIKOS**: als Fundament nein. Das **Archetypen-Muster** ist dagegen als Idee für Abschnitt 4 der Projektbeschreibung relevant und wird in v0.2 als Vergleichsvariante nachgebaut.

### AgentSociety (tsinghua-fib-lab/AgentSociety)
- **Lizenz**: Apache-2.0.
- **Implementiert**: Plattform für LLM-getriebene soziale Simulation:
  - Mobilität im Stadtraum;
  - Gedächtnis (mem0);
  - Anbindung über litellm und MCP;
  - Analyse-Werkzeuge.
  - Die Abhängigkeiten sind umfangreich.
- **Demonstriert**: Simulationen mit vielen LLM-Agenten zu sozialen Fragestellungen.
- **Befund in `economy_space.py`** (AgentSociety 2):
  - Die Haushaltsvariable „currency“ wird **einseitig** verändert: Zinsen entstehen ohne zahlende Bank, Steuern verschwinden ohne empfangenden Staat, Konsum ohne verkaufendes Unternehmen.
  - Einkommen ist ein gesetzter Wert.
- **Eignung für OIKOS**: als Fundament nein. Die Architektur geht von „ein LLM-Agent pro Person“ aus, also vom teuren Pfad, und die Ökonomie ist nicht konsistent.

### Concordia (google-deepmind/concordia)
- **Lizenz**: Apache-2.0. Das Projekt wird aktiv gepflegt (letzter Import am 19.10.2026).
- **Implementiert**: Framework für generative Agenten mit einem „Game Master“, der Handlungen in der Welt auflöst.
  - Im `contrib`-Bereich gibt es einen **deterministischen, erhaltenden Stock-Flow-Ledger** mit Rezepten, Transportwegen, Audit-Trail und Erhaltungsprüfung sowie einen Marktplatz.
  - Der Ledger bucht jedoch **physische Bestände in Gleitkommazahlen**. Bilanzen mit Forderungen und Verbindlichkeiten fehlen, Geldschöpfung lässt sich damit nicht abbilden.
- **Eignung für OIKOS**: als Kern nein, dafür ist es zu stark auf Erzählung und LLMs ausgerichtet. Brauchbar ist es:
  - als Designreferenz für den physischen Ledger;
  - später für seltene, sprachlich komplexe Interaktionen wie Tarif- oder Kreditverhandlungen.

### Bestehende agentenbasierte Wirtschaftsmodelle (Auswahl, als fachliche Vorlage)
- **Lengnick (2013)**, „Agent-based macroeconomics: A baseline model“: sehr schlankes Haushalte-Firmen-Modell mit expliziten Güter- und Arbeitsmarktprotokollen. Gute Vorlage für den Kern.
- **Caiani et al. (2016)**, AB-SFC-Benchmarkmodell (Java/JMAB): Bilanzlogik mit Banken und Staat. Vorlage für die Finanzseite.
- **Poledna et al. (2023)**, ABM für Österreich, kalibriert auf volkswirtschaftliche Gesamtrechnungen, mit einer Julia-Implementierung (BeforeIT.jl). Referenz für spätere empirische Kalibrierung. Lizenz und Code wurden hier noch **nicht geprüft**.
- **Mesa** (Apache-2.0): allgemeines Python-ABM-Framework ohne ökonomische Bausteine. Für unseren einfachen Monatsablauf bringt es wenig. Es bleibt eine Option, falls Visualisierung oder räumliche Modelle hinzukommen.

### Empfehlung
**Eigener Kern in Python 3.11+ mit NumPy, MIT-Lizenz.** Die Begründung:
1. Der schwierige und für OIKOS wesentliche Teil, eine bilanzkonsistente Buchführung mit Geldschöpfung, fehlt in allen drei Projekten.
2. Die LLM-Anbindung ist eine dünne Schicht hinter einer Schnittstelle und braucht kein Framework.
3. Python mit wenigen Abhängigkeiten erfüllt die Zugänglichkeitsanforderung am besten.

Die Entscheidung ist reversibel. Der Zustand liegt in Arrays, sodass der Kern bei Bedarf auf JAX oder PyTorch portiert werden kann.

## 5. Kleinster sinnvoller Prototyp (v0.1)

### 5.1 Umfang

| Sektor | Anzahl | Bilanz (Aktiva / Passiva) | Rolle |
|---|---|---|---|
| Haushalte | 1 000 (konfigurierbar 200–5 000) | Einlagen / – ; Eigentumsanteile an Firmen | Arbeit, Konsum von Gütern und Energie |
| Konsumgüterfirmen | 20 | Einlagen, Lager / Kredite | produzieren mit Arbeit und Energie |
| Energieversorger | 3 | Einlagen / Kredite | kaufen Primärenergie im Ausland, verkaufen an Haushalte und Firmen |
| Bank | 1 | Kredite, Staatskredit / Einlagen, Eigenkapital | Kreditvergabe (Regel), Zinsen |
| Staat | 1 | Einlagen / Kredit bei der Bank | Steuern, Arbeitslosengeld, Politikinstrumente |
| Ausland | 1 | Einlagen / – | verkauft Primärenergie zum exogenen Weltpreis |

Für v0.1 gelten bewusste Vereinfachungen, jeweils dokumentiert und später austauschbar:
- keine Zentralbank, der Staat verschuldet sich direkt bei der Bank;
- ein einziges homogenes Konsumgut;
- kein Kapitalstock, Produktion nur aus Arbeit und Energie;
- das Ausland gibt einen Teil seiner Einnahmen für inländische Güter aus. Der Parameter `rest_of_world.spending_rate` ist eine **sichtbare** Annahme (umgesetzt mit 0,5; ursprünglich war 0 geplant, siehe `02_modell_v0_1.md`, Abschnitt 9);
- **kein informeller Sektor** (siehe Rückfrage).

Neben dem Geld wird Energie **physisch** gebucht (kWh), damit der Ressourcenverbrauch messbar ist.

### 5.2 Periodenablauf (ein Monat, Reihenfolge ist Teil der Institutionen)

1. Exogener Pfad: Weltenergiepreis.
2. Firmen planen Produktion und Preise (Lagerregel nach Lengnick).
3. Kreditantrag für eine Lohnlückenfinanzierung; die Bank entscheidet per Regel nach Verschuldungsgrad.
4. Arbeitsmarkt: Vakanzen; Arbeitslose werden in einer zufälligen Reihenfolge (gesetzter Seed) zugeordnet.
5. Produktion; Energieversorger kaufen Primärenergie im Ausland.
6. Löhne.
7. Staat: Arbeitslosengeld und das jeweilige Politikinstrument.
8. Haushalte entscheiden ihr Budget: Energie als Grundbedarf mit geringer Preiselastizität, danach Güter. Auf dem Gütermarkt besuchen sie *k* zufällige Anbieter, bei Knappheit wird rationiert.
9. Steuern, Zinsen, Tilgung, Dividenden.
10. Insolvenz: negatives Eigenkapital führt zum Austritt, der Kredit wird abgeschrieben. Der Markteintritt folgt einer expliziten Regel.
11. **Invariantenprüfung**: Bei Verletzung bricht der Lauf ab.

### 5.3 Buchführung (Kern)
- Alle Geldbeträge werden als `int64` in Cent geführt. Jede Buchung ist ein Satz `(t, Soll-Konto, Haben-Konto, Betrag, Typ)`.
- Buchungen laufen vektorisiert, d. h. viele Buchungen als Arrays in einem Schritt. Das bleibt auch bei größeren Populationen schnell.
- Pro Schritt wird ein aggregiertes Journal geführt. Die Einzelbuchungen werden optional mitgeschrieben.

Geprüfte Invarianten:
1. Jede Forderung hat eine gleich hohe Verbindlichkeit bei einem Gegenüber.
2. Die Summe aller Einlagen ist gleich den Einlageverbindlichkeiten der Bank.
3. Geld entsteht nur durch Kreditvergabe und verschwindet nur durch Tilgung oder Abschreibung. Der Saldo wird aus dem Journal nachgerechnet.
4. In der Transaktionsflussmatrix summieren sich Zeilen und Spalten zu null, und die Finanzierungssalden der Sektoren summieren sich zu null.
5. Physisch: importierte Energie = verbrauchte Energie + Lagerveränderung.

### 5.4 Schnittstellen

```python
class DecisionModel(Protocol):
    meta: ModelMeta    # Name, Version, Art (rule|statistical|nn|system1|llm),
                       # Hash von Gewichten/Konfiguration, deterministisch?,
                       # Semantik der Wahrscheinlichkeiten ("none" | "score" | "calibrated_choice_prob"),
                       # Validierungsstatus und -daten
    def decide(self, obs: ObservationBatch, space: ActionSpace,
               rng: np.random.Generator) -> DecisionBatch: ...
```

- **ObservationBatch**: strukturierte Arrays für alle Akteure, die in diesem Schritt entscheiden. Er enthält nur Informationen, die der Akteur tatsächlich lokal kennt. Ein Aufruf deckt den ganzen Batch ab, was die Bündelung der Aufrufe ergibt.
- **ActionSpace**: geschlossen und typisiert, z. B. Konsumquote ∈ [0, 1] oder Preisänderung ∈ {−5 %, …, +5 %}. Die Simulation lehnt ungültige Aktionen ab und verwendet stattdessen eine dokumentierte Ersatzregel. Diese Fälle werden gezählt.
- **System-1-Entscheidungsmodelle (Prinzip Jev)**: Modelle, die keinen Text erzeugen, sondern zu einem Zustand und vorgegebenen Handlungsoptionen eine strukturierte, typisierte Entscheidung oder Bewertung liefern. Sie passen ohne Adapter auf diese Schnittstelle. In `ModelMeta` werden sie als eigene Art geführt (`kind: system1`), getrennt von `nn` und `llm`. Für ihre Bewertung gelten zwei Punkte:
  - Ihre Gültigkeit hängt von den Trainingsdaten ab. Wurde ein solches Modell auf Ausgaben eines LLM trainiert, erbt es dessen Verzerrungen (vgl. 2.6). Wurde es auf beobachteten Entscheidungen trainiert, ist es direkt an Verhalten prüfbar.
  - Seine Bewertungen sind Scores. Als Wahrscheinlichkeiten menschlicher Entscheidungen gelten sie erst nach Kalibrierung (vgl. 2.4).
- **Scheduler**: legt fest, wer wann entscheidet, periodisch oder ereignisbasiert. Die Auslöser sind Teil der Konfiguration.
- **Institution**: reine Funktionen bzw. Objekte, die in YAML parametrisiert werden (Steuertarif, Transfer, Subvention, Kreditregel, Insolvenzregel, Marktprotokoll). Ein Szenario ist eine Abweichung (Diff) gegenüber der Basiskonfiguration.
- **Messung**: Jeder `decide`-Aufruf protokolliert Aufrufe, Laufzeit und Speicher, bei LLMs zusätzlich Tokens.
- **Run-Manifest**: Git-Commit, Hash der Konfiguration, Seeds, Paketversionen, Modell- und Gewichts-Hashes, Hash des LLM-Caches. Jedes Ergebnis lässt sich darauf zurückführen.

### 5.5 Profile (Schema ab v0.1, Inhalt minimal)
```yaml
parameter: energy_price_elasticity_short_run
population: {region: "stilisiert, DE-ähnlich", group: "Haushalte, unteres Einkommensquintil"}
value: {distribution: normal, mean: -0.1, sd: 0.05}
status: assumed          # sourced | assumed | contested
sources: []              # DOI + Fundstelle + Geltungsbereich, wenn status=sourced
contradicting: []        # widersprechende Befunde bleiben erhalten
note: "Platzhalter; vor Experiment durch Literaturwert ersetzen oder als Annahme ausweisen"
reviewed_by: null
```
In v0.1 sind die meisten Werte ehrlicherweise **Annahmen**. Die Ergebnisberichte listen automatisch auf, wie viele Parameter belegt, angenommen oder umstritten sind.

### 5.6 Erstes Experiment: Energiepreisschock

- **Ausgangszustand**: 60 Monate Einschwingphase, Prüfung auf Quasistationarität (keine Drift über eine festgelegte Schwelle).
- **Schock**: Der Weltenergiepreis verdoppelt sich im Monat 0, bleibt 24 Monate auf diesem Niveau und kehrt danach zurück. Form und Höhe sind Parameter.
- **Szenarien**:

  | | Instrument |
  |---|---|
  | S0 | keine Maßnahme |
  | S1 | pauschale Transfers pro Haushalt |
  | S2 | Energiepreissubvention (Staat übernimmt Anteil des Endkundenpreises) |
  | S3 | öffentliche Effizienzinvestition (Staat kauft Sanierungsleistungen bei Konsumgüterfirmen, senkt dauerhaft den Energiebedarf der energieintensivsten Haushalte) |

- **Vergleichsbasis**: **gleiches Bruttobudget B** über 24 Monate, finanziert über Staatsverschuldung. Die Kosten der Subvention sind endogen. Ihr Satz wird deshalb vorab so kalibriert, dass die erwarteten Kosten ≈ B betragen; die tatsächlichen Kosten werden mitberichtet. Als Variante: Steuerfinanzierung.
- **Zufallszahlen**: gemeinsame Zufallszahlen für alle Szenarien, 100 Seeds je Szenario.
- **Kennzahlen**, jeweils als Verteilung über die Seeds und, wo sinnvoll, über Einkommensquintile:

  | Bereich | Kennzahlen |
  |---|---|
  | Versorgungssicherheit | Anteil der Haushalte, deren Energiebedarf nicht gedeckt ist, und Anteil mit Energiekosten > 10 % des Einkommens |
  | Beschäftigung | Arbeitslosenquote (Verlauf) |
  | Ungleichheit | Gini von verfügbarem Einkommen und Nettovermögen; realer Konsum nach Quintil |
  | Machtkonzentration | HHI im Gütersektor; Firmenaustritte |
  | Ressourcenverbrauch | importierte Primärenergie (kWh) |
  | Krisenanfälligkeit | maximaler Einbruch und Erholungsdauer der Beschäftigung; Kreditausfälle der Bank; Staatsschuld |

- **Vorab festgelegte Mechanismus-Erwartungen** dienen als Prüfung der korrekten Umsetzung, sind also noch keine Aussagen über die Wirklichkeit:
  - **E1**: Die Subvention (S2) senkt den Preisanreiz. Bei gleichem Budget sollte die importierte Energie in S2 über der in S1 liegen.
  - **E2**: Pauschale Transfers (S1) entlasten das unterste Quintil relativ stärker als die Subvention (S2).
  - **E3**: Die Investition (S3) wirkt kurzfristig schwächer, senkt aber Energieimporte und Energiearmut nach Monat 24.

  Weicht das Modell von diesen Erwartungen ab, ist das entweder ein Fehler oder ein erklärungsbedürftiger Befund. Beides wird dokumentiert.
- **Sensitivität v0.1**:
  - One-at-a-time und Morris-Screening über die Verhaltensparameter;
  - zwei alternative Marktprotokolle: Besuchsreihenfolge und Zahl *k* der besuchten Anbieter;
  - Populationsgröße 250 / 1 000 / 4 000.

### 5.7 Abnahmekriterien v0.1 (überprüfbar)
1. Die Invarianten gelten in allen Läufen und in jedem Schritt **exakt**, ohne Toleranz, weil ganzzahlig gebucht wird.
2. Derselbe Seed und dieselbe Konfiguration ergeben bitgleiche Ergebnisse.
3. Einheitstests decken die Mechanismen ab: Ein Kredit über X erhöht Einlagen und Forderungen um X; Tilgung und Abschreibung wirken korrekt; Steuern und Transfers sind gegengebucht.
4. Das Basisszenario ohne Schock bleibt nach der Einschwingphase quasistationär.
5. Ein Kommando reproduziert das gesamte Experiment inklusive Grafiken und Manifest auf einem Laptop in unter ca. 30 Minuten (Zielwert, wird gemessen).
6. Ergebnisberichte zeigen Bandbreiten, Einzelpfade und den Anteil angenommener Parameter. Mittelwerte allein reichen nicht.

### 5.8 Danach (v0.2 ff.)
- **v0.2**: Die Energie- und Konsumentscheidung der Haushalte erhält drei Alternativen:
  - (a) ein statistisches Modell mit Elastizitäten aus der Literatur;
  - (b) ein System-1-Entscheidungsmodell nach dem Prinzip Jev, sofern geeignete Trainingsdaten vorliegen;
  - (c) ein kleines lokales LLM mit Archetypen;
  - (d) ein LLM pro Haushalt auf einem Teilensemble zur Messung des Archetypenfehlers.

  Die Varianten werden gegen Mikrodaten zum Verbrauchsverhalten 2022/23 geprüft. Außerdem wird gemessen, ob sich die Makroergebnisse überhaupt ändern. LLM-Cache und Replay-Modus sind ab dieser Version Pflicht.
- **v0.3**: Preis- und Investitionsentscheidungen der Firmen, Kreditentscheidung der Bank als austauschbares Modell, Zentralbank.
- Später: informeller Sektor und informeller Kredit, Profile mit Rückmeldungen von Menschen vor Ort, LLM-gestützte Literaturerschließung mit automatischer Quellenprüfung.

### 5.9 Verzeichnisstruktur
```
oikos/
  core/          ledger.py, accounts.py, invariants.py, state.py, scheduler.py, rng.py
  institutions/  taxes.py, transfers.py, energy_policy.py, credit.py, bankruptcy.py, protocols.py
  markets/       labor.py, goods.py, energy.py
  sectors/       households.py, firms.py, energy_suppliers.py, bank.py, government.py, rest_of_world.py
  behavior/      protocol.py, rules/ (später: statistical/, llm/)
  experiments/   runner.py, manifest.py, metrics.py, report.py
configs/         baseline.yaml, experiments/energy_shock.yaml
profiles/        *.yaml
tests/
docs/
```

---

## Quellen (nur zitierte; vor Veröffentlichung bibliographisch prüfen)
- Aher, G., Arriaga, R., Kalai, A. (2023): Using Large Language Models to Simulate Multiple Humans and Replicate Human Subject Studies. ICML.
- Argyle, L. et al. (2023): Out of One, Many: Using Language Models to Simulate Human Samples. Political Analysis.
- Caiani, A. et al. (2016): Agent based-stock flow consistent macroeconomics: Towards a benchmark model. JEDC.
- Chopra, A. et al. (2024/25): On the limits of agency in agent-based models. (AgentTorch-Paper)
- Godley, W., Lavoie, M. (2007): Monetary Economics. Palgrave.
- Horton, J. (2023): Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus? NBER WP.
- Lengnick, M. (2013): Agent-based macroeconomics: A baseline model. JEBO.
- Li, N. et al. (2024): EconAgent: Large Language Model-Empowered Agents for Simulating Macroeconomic Activities. ACL.
- Poledna, S. et al. (2023): Economic forecasting with an agent-based model. European Economic Review.
- Santurkar, S. et al. (2023): Whose Opinions Do Language Models Reflect? ICML.
