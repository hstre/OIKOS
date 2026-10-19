# OIKOS – Offenes Labor für Wirtschaft und Gesellschaft

*Regeln verändern. Wechselwirkungen verstehen.*

OIKOS ist eine offene Simulationsumgebung für Experimente mit wirtschaftlichen
Institutionen. Viele heterogene Akteure handeln mit begrenztem Wissen;
gesamtwirtschaftliche Entwicklungen entstehen aus ihren Wechselwirkungen.
Buchführung, institutionelle Regeln und Verhalten sind getrennte, austauschbare
Schichten.

**Stand: v0.1 – Forschungsprototyp.** Stilisierte Wirtschaft, alle
Verhaltensentscheidungen über einfache Regeln, alle Parameter gesetzt und nicht
kalibriert. Ergebnisse sind bedingte Aussagen über dieses Modell, keine Prognosen.

## Was v0.1 enthält

- 1 000 Haushalte, 20 Konsumgüterfirmen, 3 Energieversorger, eine Bank, ein Staat, das Ausland
- doppelte Buchführung in ganzzahligen Cent mit Geldschöpfung durch Kredit und
  Vernichtung durch Tilgung; sieben Bilanz- und Flussinvarianten werden in jedem
  Monat geprüft, eine Verletzung bricht den Lauf ab
- physische Buchführung für Energie (kWh) und Güter
- explizite Marktprotokolle (Gütermarkt mit festen Lieferbeziehungen und
  Rationierung, Arbeitsmarkt mit Fluktuation und Suchfriktion)
- eine Entscheidungsschnittstelle, hinter der Regeln, statistische Modelle,
  System-1-Modelle oder LLMs austauschbar sind
- gemeinsame Zufallszahlen über Szenarien, Manifest mit Code- und Konfigurations-Hashes,
  bitgleiche Wiederholbarkeit
- Experiment 1: Energiepreisschock mit vier Politikantworten bei gleichem Budget,
  plus Sensitivitätsanalyse

## Schnellstart

```bash
pip install -e ".[dev]"
python -m pytest                                    # Tests (~5 s)
python -m oikos run configs/experiments/energy_shock.yaml                    # 500 Läufe
python -m oikos sensitivity configs/experiments/energy_shock_sensitivity.yaml
```

Ergebnisse landen in `results/<experiment>/` (`report.md`, Grafiken, `summary.csv`,
`paired_differences.csv`, `manifest.json`).

## Dokumentation

- [`docs/01_architekturpruefung.md`](docs/01_architekturpruefung.md) – kritische Prüfung der Architektur, Wahl der Grundlage, Prototyp-Definition
- [`docs/02_modell_v0_1.md`](docs/02_modell_v0_1.md) – Modellbeschreibung v0.1: Bilanzen, Periodenablauf, Regeln, Annahmen, Grenzen
- [`results/energy_shock/report.md`](results/energy_shock/report.md) – Ergebnisse Experiment 1
- [`results/energy_shock_sensitivity/sensitivity.md`](results/energy_shock_sensitivity/sensitivity.md) – Sensitivität

## Struktur

```
oikos/core/          Kontenbuch, physische Konten, Zufallsströme
oikos/behavior/      Entscheidungsschnittstelle und Regeln
oikos/institutions/  Steuern/Transfers, Kreditregulierung, Energiepolitik
oikos/markets/       Güter- und Arbeitsmarktprotokolle
oikos/model.py       Periodenablauf
oikos/experiments/   Runner, Kennzahlen, Bericht, Sensitivität
configs/             Basiskonfiguration und Experimente
profiles/            Parameterprofile mit Quellen- und Statusangaben
```

## Lizenz

MIT
