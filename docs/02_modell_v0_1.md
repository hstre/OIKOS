# OIKOS v0.1 – Modellbeschreibung

Stand: 2026-10-19 · gehört zu Code-Version 0.1.0

Dieses Dokument beschreibt, was im Code **tatsächlich** umgesetzt ist. Abweichungen von der Planung in `01_architekturpruefung.md` stehen in Abschnitt 9.

## 1. Sektoren und Bilanzen

Alle Geldbeträge sind ganzzahlige Cent (`int64`). Jeder Akteur außer der Bank hat ein Einlagenkonto bei der einzigen Bank und kann ihr einen Kredit schulden.

| | Haushalte | Firmen | Energieversorger | Staat | Ausland | Bank | Σ |
|---|---|---|---|---|---|---|---|
| Einlagen | +D_h | +D_f | +D_e | +D_g | +D_r | −ΣD | 0 |
| Kredite | | −L_f | −L_e | −L_g | | +ΣL | 0 |
| Lager (Güter, zu Stückkosten) | | +V | | | | | V |
| Reinvermögen | | | | | | E_b = ΣL − ΣD | |

Eigentum an Firmen, Energieversorgern und der Bank liegt bei den reichsten 10 % der Haushalte (anfängliche Einlagen); jede Firma hat 20 Eigentümer mit gleichen Anteilen. Anteile werden nicht bewertet und nicht gehandelt.

**Eröffnungsbilanz.** Haushaltseinlagen lognormal, Firmen mit 1,5 Monaten Lohnsumme Einlagen und 1 Monat Lohnsumme Kredit. Die Staatsschuld bei der Bank ergibt sich als Residuum, sodass die Bank anfangs 12 % Eigenkapital auf ihre Kredite hat. Ohne Zentralbank kann die Bank nur Kredite als Aktiva halten; Einlagen müssen daher durch Kredite gedeckt sein.

## 2. Periodenablauf (ein Monat)

Die Reihenfolge ist Teil der institutionellen Annahmen.

1. **Exogen**: Weltenergiepreis. Zu Programmbeginn wird das Budget B festgelegt; fällige Sanierungen wirken.
2. **Energieversorger**: Absatzerwartung (adaptiv), Personalbedarf proportional zur erwarteten Menge, Preis = (Weltpreis + Lohnkosten je kWh) × (1 + 20 %).
3. **Güterfirmen**: Absatzerwartung, Produktionsplan, Aufschlag, Lohn (Regel, Abschnitt 4).
4. **Finanzierung**: Kreditantrag für die Lücke zwischen geplantem Lohn- und Energiebudget und Einlagen. Bankregel (Schuld ≤ 1 × erwartetem Jahresumsatz), danach Kapitalanforderung (privates Kreditvolumen ≤ Eigenkapital / 8 %).
5. **Arbeitsmarkt**: 1,5 % exogene Fluktuation; Entlassungen begrenzt auf 10 % der Belegschaft pro Monat, außer ein Arbeitgeber kann seine Leute nicht bezahlen; Arbeitslose erreichen mit Wahrscheinlichkeit 0,5 eine offene Stelle (zufällige Reihenfolge).
6. **Produktion**: Arbeit × 400 Einheiten; Energie 2,5 kWh je Einheit vom günstigsten Versorger.
7. **Einkommen**: Löhne (Lohnsteuer 25 % einbehalten), Arbeitslosengeld (60 % des Durchschnittslohns), ggf. Transfer.
8. **Haushalte**: Energie- und Konsumbudget (Regel, Abschnitt 4); Energiekauf, ggf. Subvention vom Staat an den Versorger; Anpassung des Referenzpreises; Versorgerwechsel (2 %/Monat zum günstigsten).
9. **Gütermarkt**: Haushalte kaufen bei ihren drei festen Lieferanten, günstigste zuerst; bei Knappheit proportionale Rationierung (Alternative: Zufallsschlange). Danach Staat (reguläre Käufe, ggf. Investitionsprogramm) und Ausland, verteilt nach Lagerbeständen. Lieferbeziehungen werden gelegentlich gewechselt (Preisvergleich, Rationierung). Lager schrumpft um 2 %/Monat.
10. **Energieimporte**: Versorger bezahlen die verkaufte Menge zum Weltpreis an das Ausland.
11. **Zinsen und Tilgung**: 5 % p. a. auf Kredite, 1 % p. a. auf Einlagen; Firmen tilgen 1/36 des Kredits pro Monat.
12. **Gewinne**: periodengerechter Gewinn (inkl. Lagerwertänderung), Gewinnsteuer 20 %, Dividenden = Eigenkapital über 1 Monat Kosten, begrenzt durch Liquidität über 1 Monat Kosten. Bank schüttet Eigenkapital über 12 % aller Kredite aus. Dividendensteuer 25 %.
13. **Insolvenz**: Firma mit negativem Eigenkapital (Einlagen + Lager − Kredit) scheidet aus; Kredit wird so weit möglich getilgt, der Rest abgeschrieben, Lager abgeschrieben. Eine neue Firma übernimmt den Platz; die Eigentümer zahlen 2 Monate Lohnsumme Eigenkapital ein, ein Rest wird als Kredit finanziert.
14. **Staat**: tilgt Kredit, wenn Einlagen über einem Monat Ausgaben liegen. Reguläre Käufe folgen einer geglätteten Regel: Mittel der letzten 12 Monate (Steuern − Arbeitslosengeld − Zinsen). Programmausgaben sind schuldenfinanziert und fließen nicht in diese Regel.
15. **Prüfung**: Buchführungs- und physische Invarianten; Kennzahlen.

## 3. Invarianten (geprüft nach jedem Monat)

| | Bedingung | Toleranz |
|---|---|---|
| I1 | Σ Einlagen = Einlageverbindlichkeiten der Bank (getrennt geführt) | exakt |
| I2 | Σ Kredite = Kreditforderungen der Bank | exakt |
| I3 | Eigenkapital der Bank = Forderungen − Verbindlichkeiten | exakt |
| I4 | Σ finanzielles Reinvermögen aller Akteure = 0 | exakt |
| I5 | Δ Geldmenge = geschöpft − vernichtet | exakt |
| I6 | Δ Bankeigenkapital = Erträge − Aufwendungen − Abschreibungen | exakt |
| I7 | je Sektor: Δ Einlagen = Zuflüsse − Abflüsse laut Journal (Transaktionsflussmatrix) | exakt |
| P1 | importierte Energie = von Haushalten und Firmen verbrauchte Energie | relativ 1e−9 |
| P2 | Δ Lager = Produktion − Verkauf − Verderb − Abschreibung | relativ 1e−9 |

Zusätzlich: keine negativen Einlagen (kein Dispo außer explizit gebuchten Krediten), keine Buchung von Gleitkommabeträgen.

## 4. Verhaltensregeln (austauschbar)

Alle Regeln implementieren `DecisionModel` (`oikos/behavior/protocol.py`): Beobachtungen aller entscheidenden Akteure als Arrays hinein, Aktionen aus einem geschlossenen Aktionsraum heraus. Ungültige Aktionen werden auf den zulässigen Bereich gesetzt und gezählt.

**Haushalte** (`household_budget_rule`):
- gewünschte Energie = Bedarf × clip((p / p_ref)^ε, 0,6, 1), ε ~ N(−0,15; 0,05), p_ref passt sich mit 5 %/Monat an
- gekaufte Energie = min(gewünscht, Einlagen / p)
- Konsumbudget = c_y × max(0, Nettoeinkommen − Energieausgaben) + c_w × Einlagen vor Einkommen, c_y ~ U(0,80; 0,96), c_w ~ U(0,01; 0,03)

**Güterfirmen** (`firm_planning_rule`, nach Lengnick 2013):
- Erwartung = 0,7 × alte Erwartung + 0,3 × letzter Absatz
- Produktion = Erwartung + 0,25 × (0,2 × Erwartung − Lager)
- Aufschlag steigt/fällt um U(0, 2 %), wenn Lager/Erwartung unter 0,10 / über 0,35
- Lohn +U(0, 1 %) nach unbesetzten Stellen; −U(0, 1 %) nach 24 Monaten ohne unbesetzte Stelle

**Energieversorger**: adaptive Erwartung, Personal proportional zur Menge, fester Aufschlag.

**Bank** (`leverage_credit_rule`): bewilligt bis Schuld = 1 × erwarteter Jahresumsatz.

## 5. Politikinstrumente (Experiment 1)

Budget B = 0,5 × (Anstieg des Endkundenpreises je kWh) × (Haushaltsverbrauch im Vormonat) × 24. B ist für alle Szenarien eines Seeds identisch.

| | Instrument | Umsetzung |
|---|---|---|
| S0 | keine | – |
| S1 | Transfer | B / (24 × Haushalte) pro Haushalt und Monat |
| S2 | Subvention | Staat zahlt 50 % des Preisanstiegs über dem Vorkrisenpreis je kWh an den Versorger; Kosten endogen |
| S3 | Investition | Staat kauft monatlich Güter für B/24; je 15 000 € eine Sanierung (−30 % Energiebedarf nach 6 Monaten) bei den Haushalten mit dem höchsten Bedarf |

## 6. Kennzahlen

Siehe `oikos/metrics.py` und `oikos/experiments/summary.py`. Quintile werden zu Programmbeginn nach dem mittleren Nettoeinkommen der letzten 12 Monate festgelegt und danach nicht mehr geändert (dieselben Haushalte werden verfolgt). „Energiekostenbelastung“ = Anteil der Haushalte mit Energieausgaben > 10 % des Nettoeinkommens. Diese Kennzahl misst den gezahlten Preis und begünstigt daher die Subvention mechanisch.

## 7. Explizite Annahmen, die Ergebnisse stark prägen

1. **Energiebedarf, Einlagen und Einkommen sind unabhängig voneinander verteilt.** Real korrelieren sie. Das betrifft direkt den Vergleich Transfer gegen Subvention.
2. **Keine Liquiditätsnot bei Energie.** Mit den gesetzten Einlagen kann jeder Haushalt seine gewünschte Energie bezahlen; der Indikator „erzwungene Unterversorgung“ bleibt bei 0. Versorgungssicherheit wird in v0.1 daher nur über die Kostenbelastung abgebildet.
3. **Löhne sind nach unten starr** (Senkung erst nach 24 Monaten ohne unbesetzte Stelle). Das erzeugt Hysterese im Preisniveau nach Nachfragestützung.
4. **Energieangebot unbegrenzt**, nur der Preis steigt; keine Mengenknappheit.
5. **Das Ausland gibt 50 % seiner Einlagen pro Monat für inländische Güter aus.** Ohne diese Rückführung würde dauerhaft Geld abfließen und es gäbe keine stationäre Basis. Variante 0,2 in der Sensitivität.
6. **Staat kann sich unbegrenzt bei der Bank finanzieren**, Kapitalanforderung gilt nur für private Kredite.
7. **Ein homogenes Konsumgut, kein Kapitalstock, keine Zentralbank, kein informeller Sektor.**
8. **Basisregime**: Die Basis ist nachfragebeschränkt mit ca. 6 % Arbeitslosigkeit (überwiegend friktionell). Ob eine Wirtschaft nachfrage- oder kapazitätsbeschränkt ist, ändert die Wirkung von Transfers grundlegend; `low_household_wealth` in der Sensitivität testet ein nachfrageschwächeres Regime.

## 8. Austausch einer Entscheidungskomponente

```python
from oikos.model import Economy

class MyHouseholdModel:
    meta = ModelMeta(name="my_model", version="0.1", kind="system1", deterministic=True)
    def decide(self, obs, space, rng):
        ...  # obs: dict of arrays (need_kwh, energy_price, deposits, net_income, ...)
        return {"energy_wanted": ..., "energy_kwh": ..., "goods_budget": ...}

eco = Economy(cfg, seed=1, models={"household": MyHouseholdModel()})
```

Über die Konfiguration (`behavior.household`) stehen derzeit `rule` und `llm_table` zur Wahl. `llm_table` (`oikos/behavior/llm/household_table.py`) liest eine Entscheidungstabelle, die ein LLM einmal pro Situationszelle befüllt hat. Die Tabelle moduliert die individuelle Entscheidung (Energie = Bedarf × (1 + Änderung), Konsumbudget = Regelbudget × (1 + Änderung)). Die Preiselastizität der Regel wird dabei ersetzt, Bedarf und Konsumneigungen bleiben individuell. Die Zelleinteilung ist eine Näherung, deren Einfluss noch gemessen werden muss. Prompt, Schema, Modell-ID, die tatsächlich antwortenden Modelle, Tokens und Kosten stehen in der Tabellendatei.

Die Simulation prüft die Aktionen gegen den Aktionsraum, zählt Aufrufe, Einzelentscheidungen, Laufzeit und ungültige Aktionen und schreibt sie ins Manifest.

## 9. Abweichungen von der Planung (01_architekturpruefung.md)

- **Ausland** gibt Einnahmen zurück (`spending_rate` 0,5 statt 0): ohne Rückfluss keine stationäre Basis (Annahme 5).
- **Dividendenregel**: Ausschüttung des Eigenkapitals über einem Ziel statt eines Anteils am Gewinn. Erste Versionen behielten Gewinne ein bzw. zahlten auf Kassengewinne aus; das erzeugte Geldvernichtung (Deflation) bzw. systematischen Eigenkapitalabfluss und viele Insolvenzen.
- **Feste Lieferbeziehungen** (Lengnick 2013) statt täglicher Zufallsauswahl: Die Zufallsauswahl erzeugte starke Nachfrageschwankungen und unrealistisch viele Insolvenzen.
- **Fluktuation und Suchfriktion** im Arbeitsmarkt ergänzt: Ohne sie stellte sich Vollbeschäftigung ein, und Beschäftigungseffekte waren nicht messbar.
- **Subventionssatz** = Budgetanteil (0,5) unter der Annahme unveränderter Mengen statt iterativer Kalibrierung; die tatsächlichen Kosten werden berichtet.
- **Morris-Screening** ist noch nicht umgesetzt; v0.1 enthält eine One-at-a-time-Sensitivität einschließlich struktureller Varianten.

## 10. Bekannte Grenzen

- Parameter sind gesetzt, nicht kalibriert; keine Validierung an Mikro- oder Makrodaten.
- Bei 1 000 Haushalten sind Einzelpfade verrauscht; Aussagen nur über Verteilungen gepaarter Differenzen.
- Firmeneintritt erfolgt sofort auf demselben Platz; Marktkonzentration kann sich daher kaum dauerhaft erhöhen.
- Die Kennzahl „Erholungsdauer“ ist bei 1 000 Haushalten stark verrauscht.
