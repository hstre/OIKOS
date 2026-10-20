Replay neu erzeugt (lokal, 2026-10-20) mit korrigiertem ReplayClient: Identische Anfragen
(die 40 Wiederholungen der technischen Kontrolle) erhalten ihre Antworten in der ursprünglichen
Reihenfolge. Der im Workflow erzeugte Replay nutzte die alte Version, in der die Wiederholung die
Hauptantwort überschrieb. Abweichung zum Live-Lauf jetzt: alle Kennzahlen innerhalb 1e-6 außer zwei
AUC-Werten von M3 (Differenz < 5e-5, Gleichstände bei hardwareabhängiger Rundung).
