# Jev-Anbindung (Beobachtungsmodus)

Stand: 2026-10-19 · Status: implementiert, mit simulierten Antworten getestet und in einem ersten echten Beobachtungslauf geprüft (48 Entscheidungen, 0 Fehler, ≈ 0,0013 USD). Auswertung: [`05_jev_beobachtung_lauf1.md`](05_jev_beobachtung_lauf1.md).

## Was Jev ist (laut OpenRouter-Dokumentation, geprüft am 19.10.2026)

- Jev ist ein **System-One-Entscheidungsmodell** von TypeSafe, kein Sprachmodell. Es erhält einen Zustand (`state`) und typisierte Fragen und liefert typisierte Antworten mit Wahrscheinlichkeiten, aber keinen Text und keine Begründungen.
- **Schnittstelle**: `POST https://openrouter.ai/api/alpha/decisions`, Fragetypen `choice`, `noul`, `score` und `box`.
- **Modell**: `typesafe/jev-1.14`; der Alias `~typesafe/jev-latest` zeigt auf die jeweils neueste Version. Die Antwort nennt den tatsächlich verwendeten datierten Stand, etwa `typesafe/jev-1.14-20261014`. OIKOS fixiert `typesafe/jev-1.14` und protokolliert den datierten Stand.
- **Preis**: 0,042 USD pro Mio. Eingabetokens, Ausgabe kostenlos. Jede Antwort enthält `usage.cost`.
- **Keine Seed- oder Temperatur-Parameter.** Laut Dokumentation können die Wahrscheinlichkeiten zwischen Läufen leicht schwanken. Reproduzierbarkeit gibt es deshalb nur über den Replay-Modus.
- **Nicht verwechseln**: `typesafe/jev-router` ist ein Router, der Anfragen an andere Sprachmodelle weiterleitet. Für OIKOS ist er nicht geeignet und wird nicht verwendet.

## Umfang der ersten Anbindung

| | |
|---|---|
| Entscheidung | Konsumbudget für Güter außer Energie in diesem Monat, Auswahl aus 5 vorgegebenen Budgets |
| Optionen | 60 / 75 / 90 / 100 / 110 % des Einkommens nach der Energierechnung, auf 10 € gerundet, höchstens das verfügbare Geld. Die Optionen sind unabhängig von der Regel definiert, die Regelantwort ist also nicht automatisch eine der Optionen |
| Zustand (nur, was der Haushalt kennt) | Erwerbsstatus, Nettoeinkommen dieses Monats, Ersparnis vor Einkommen, Energiepreis jetzt und gewohnt, Energierechnung dieses Monats, verfügbares Geld nach der Energierechnung |
| Nicht im Zustand | Konsumneigungen und andere Modellparameter, Einkommensrang, Daten anderer Haushalte, gesamtwirtschaftliche Größen |
| Modus | **Beobachtung**: Die v0.1-Regel steuert die Wirtschaft; Jev wird nur protokolliert. Ein Test prüft, dass die Wirtschaft bitgleich zum reinen Regellauf bleibt |
| Umfang | Monate −1, 3, 12 und 30 des Experiments S0, je 12 zufällig gezogene Haushalte, also 48 Entscheidungen; harte Obergrenze 50 im Code |
| Wahrscheinlichkeiten | als **modellinterne Scores** gespeichert (`probability_semantics: score`), nicht als empirische Entscheidungswahrscheinlichkeiten |

## Fehlerbehandlung: nichts wird stillschweigend ersetzt

| Fall | Verhalten |
|---|---|
| `OPENROUTER_API_KEY` fehlt oder ist leer | Abbruch vor der ersten Anfrage mit klarer Meldung |
| Verbindungsfehler, HTTP 429, 5xx | höchstens 2 Wiederholungen, danach Eintrag `connection` bzw. `http_status` |
| HTTP 400/401/402/403 | keine Wiederholung, Eintrag `http_status` mit Fehlermeldung der API |
| Antwort ohne `answers`, `choice` oder `probabilities`, falscher Antworttyp, zusätzliche Antworten | `response_format` |
| Zahl oder Namen der Wahrscheinlichkeiten passen nicht zu den Optionen, Werte außerhalb [0, 1], Summe ≠ 1 (Toleranz 0,05) | `response_format` |
| Gewählte Option nicht im Optionsraum | `invalid_action` |
| Replay: Anfrage nicht im Log | `replay_miss` |
| Entscheidungsmodell liefert Arrays falscher Länge oder fehlende Aktionen (allgemeine Schnittstelle) | Abbruch mit `DecisionShapeError` statt stiller Übertragung auf alle Akteure |

Fehlerhafte Einträge enthalten keine Jev-Entscheidung. Sie werden gezählt, im Bericht nach Typ ausgewiesen, und der Befehl endet mit Exit-Code 1.

## Protokoll und Replay

`results/jev_observe/jev_log.jsonl` enthält eine Zeile je Anfrage:
- Anfrage (Zustand, Frage, Optionen) und ihr SHA-256-Hash
- rohe Antwort, tatsächlich antwortendes Modell, Anbieter, Generierungs-ID
- Tokens, Kosten, Latenz, Zahl der Versuche
- Fehlertyp und -meldung
- Regelbudget, nächstliegende Regeloption, Jev-Wahl, Scores, Abstand zur Regel

Der Schlüssel steht nur im Authorization-Header der ausgehenden Anfrage, nirgends sonst. Fehlermeldungen werden auf den Schlüssel geprüft und geschwärzt. Ein Test sucht in allen Ausgabedateien nach dem Schlüssel und nach „Bearer“.

`--mode replay --replay-log <log>` beantwortet dieselben Anfragen aus dem Log, ohne Netz und ohne Schlüssel. Ein Test prüft, dass Replay dieselben Entscheidungen und Kennzahlen ergibt.

## Wo der Schlüssel hinterlegt wird

Niemals in Dateien des Repositorys, in Konfigurationsdateien oder im Chat.

1. **GitHub Actions** (bereits erledigt): Repository-Secret `OPENROUTER_API_KEY`. Der Workflow `.github/workflows/jev-observe.yml` reicht es nur an die beiden Jev-Schritte weiter, und GitHub maskiert es in Logs. Start über den Actions-Tab (sobald die Datei auf `main` liegt) oder durch Push eines Branches `jev-run/<name>`.
2. **Claude-Code-Cloud-Umgebung**: im Umgebungsmenü der Sitzung (Titelleiste) → Bearbeiten → unter *Network secrets* bzw. *API credentials*, sonst als Umgebungsvariable `OPENROUTER_API_KEY`. Erst eine **neue Sitzung** übernimmt den Wert.
3. **Lokal**: `export OPENROUTER_API_KEY=...` in der Shell oder in einer `.env`-Datei außerhalb der Versionskontrolle (`.env` steht in `.gitignore`).

## Befehle

```bash
python -m oikos jev-ping                         # 1 echte Testanfrage (fester Beispielhaushalt)
python -m oikos jev-observe --mode live          # höchstens 50 beobachtete Entscheidungen
python -m oikos jev-observe --mode replay \
    --replay-log results/jev_observe/jev_log.jsonl --out results/jev_observe_replay
```

## Bewusst noch nicht enthalten

- Kein Steuerungsmodus: Jev beeinflusst die Wirtschaft nicht.
- Keine Ableitung menschlicher Entscheidungswahrscheinlichkeiten aus Jevs Scores.
- Keine Änderung an Parametern, Regeln oder Haushaltsprofilen. v0.1 ist als lokaler Tag `v0.1.0` markiert (das Pushen des Tags wurde von der Umgebung abgewiesen) und durch `tests/test_reference_v0_1.py` gesichert: Der Test vergleicht Regelläufe bitgenau mit den Hashes aus `results/energy_shock/manifest.json`.
