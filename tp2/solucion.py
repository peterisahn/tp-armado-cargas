"""Validación de soluciones

Una solución es una lista de camiones; cada camión es una lista de índices de productos
(desde 0). Esta validación es la del problema básico: cada producto en exactamente un
camión y ningún camión por encima de la capacidad. Las reglas del modelo (temperatura y
similitud mínima) se chequean con Contexto.camion_valido (modelo.py).
"""

from __future__ import annotations

from typing import Sequence

from .instancia import TOL, Instancia


class SolucionInvalida(ValueError):
    """La solución no cumple las restricciones del problema."""


def validar(inst: Instancia, camiones: Sequence[Sequence[int]]) -> None:
    """Lanza SolucionInvalida si algún producto falta, se repite o no existe, o si algún
    camión supera la capacidad."""
    visto = [False] * inst.n
    for k, camion in enumerate(camiones):
        carga = 0.0
        for i in camion:
            if not (0 <= i < inst.n):
                raise SolucionInvalida(f"Camión {k}: el índice {i} no existe (n = {inst.n}).")
            if visto[i]:
                raise SolucionInvalida(f"El producto {i} aparece en más de un camión.")
            visto[i] = True
            carga += inst.pesos[i]
        if carga > inst.capacidad + TOL:
            raise SolucionInvalida(
                f"Camión {k}: carga {carga:g} supera la capacidad {inst.capacidad:g}.")
    faltan = [i for i in range(inst.n) if not visto[i]]
    if faltan:
        raise SolucionInvalida(
            f"Productos sin camión: {faltan[:10]}{'…' if len(faltan) > 10 else ''}.")
