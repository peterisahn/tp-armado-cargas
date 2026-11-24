"""Métricas para comparar soluciones de distintos modelos con la misma vara.

Se calculan sobre la solución, sin importar con qué modelo se obtuvo, para responder las
preguntas de la empresa de cuántos vehículos cuesta cada criterio y si
las cargas serían aceptables.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from .instancia import Instancia
from .modelo import categoria, inseguro

UMBRAL_INCOMPATIBLE = 0.2  # pares con s_ij < 0.2 se consideran "no deberían ir juntos"


def metricas(inst: Instancia, vehiculos: Sequence[Sequence[int]]) -> Dict[str, float]:
    s = inst.similitudes
    cats = [categoria(t) for t in inst.temperaturas]
    pares = 0
    suma = 0.0
    incompatibles = 0
    inseguros = 0
    rango_max = 0.0
    for v in vehiculos:
        if inseguro([cats[i] for i in v]):
            inseguros += 1
        ts = [inst.temperaturas[i] for i in v]
        rango_max = max(rango_max, max(ts) - min(ts))
        for a in range(len(v)):
            for b in range(a + 1, len(v)):
                x = s[v[a]][v[b]]
                pares += 1
                suma += x
                if x < UMBRAL_INCOMPATIBLE:
                    incompatibles += 1
    K = len([v for v in vehiculos if v])
    return {
        "K": K,
        "similitud_total": suma,
        "similitud_media_par": suma / pares if pares else 0.0,
        "pct_pares_incompatibles": 100.0 * incompatibles / pares if pares else 0.0,
        "vehiculos_inseguros": inseguros,
        "pct_vehiculos_inseguros": 100.0 * inseguros / K if K else 0.0,
        "rango_temp_max": rango_max,
    }
