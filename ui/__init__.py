"""Interfaccia web per l'RPD: cruscotto, inventario, coda di validazione, ricerca, registro delle decisioni.

Legge solo le predizioni prodotte da `classifier.pipeline` (JSON) e il registro dei trattamenti (CSV): non importa
il backend, così i due possono evolvere separatamente.
"""
