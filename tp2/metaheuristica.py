"""Metaheurística: Iterated Local Search con "romper y rearmar".

    s = búsqueda local(constructiva)  # una buena solución de partida
    mejor = s
    mientras quede tiempo:
        s' = romper_y_rearmar(s)  # vaciar un cuarto de los camiones y reubicar
        s' = búsqueda local(s')
        si f(s') < f(s): s = s'  # sólo se aceptan mejoras
    devolver s

- ROMPER: se vacía el camión menos cargado (el candidato natural a desaparecer) y, además,
  un cuarto de los camiones de la solución elegidos al azar (para no romper siempre lo
  mismo). "Un cuarto" es el parámetro `fraccion` (0,25 por defecto)
- REARMAR: los productos sueltos se reubican, de mayor a menor peso, con la misma
  constructiva (bfd o parecido) sobre los camiones que quedaron.
"""

from __future__ import annotations

import random
import time
from typing import List, Optional

from .busqueda_local import busqueda_local
from .constructivas import construir
from .instancia import TOL
from .modelo import Contexto

Solucion = List[List[int]]


def elegir_camiones_a_romper(ctx: Contexto, camiones: Solucion, fraccion: float,
                             rng: random.Random) -> set:
    """Posiciones de los camiones a vaciar: el menos cargado y, además, ⌊fraccion·K⌋ al
    azar entre los demás (K = camiones de la solución; con 0,25 es un cuarto)."""
    menos_cargado = min(range(len(camiones)), key=lambda k: ctx.carga(camiones[k]))
    otros = [k for k in range(len(camiones)) if k != menos_cargado]
    cuantos = min(len(otros), int(fraccion * len(camiones)))
    return {menos_cargado} | set(rng.sample(otros, cuantos))


def romper_y_rearmar(ctx: Contexto, camiones: Solucion, fraccion: float, criterio: str,
                     rng: random.Random) -> Solucion:
    """Vacía los camiones que elige elegir_camiones_a_romper y vuelve a ubicar sus
    productos con la constructiva `criterio` (bfd o parecido)."""
    if len(camiones) <= 1:
        return [list(c) for c in camiones]
    rotos = elegir_camiones_a_romper(ctx, camiones, fraccion, rng)
    quedan = [c for k, c in enumerate(camiones) if k not in rotos]
    sueltos = [i for k in rotos for i in camiones[k]]
    sueltos.sort(key=lambda i: -ctx.inst.pesos[i])
    return construir(ctx, criterio, orden=sueltos, camiones=quedan)


def ils(ctx: Contexto, tiempo_max: float = 10.0, semilla: int = 0, fraccion: float = 0.25,
        constructiva: str = "parecido", relocate: bool = True, swap: bool = True,
        historia: Optional[list] = None) -> Solucion:
    """ILS devuelve la mejor solución encontrada en tiempo_max segundos.

    fraccion: qué parte de los camiones se vacía en cada vuelta, además del 
    menos cargado (0,25 = un cuarto; elegido en el experimento A2).
    constructiva:  "parecido" o "bfd": con cuál se arma la solución inicial y se rearma.
    relocate/swap: operadores de la búsqueda local.
    historia: si es una lista, se le agrega (segundos, f) cada vez que mejora.
    """
    inicio = time.perf_counter()
    rng = random.Random(semilla)

    def queda():
        return tiempo_max - (time.perf_counter() - inicio)

    actual = busqueda_local(ctx, construir(ctx, constructiva), queda(), relocate, swap)
    f_actual = ctx.valor(actual)
    if historia is not None:
        historia.append((time.perf_counter() - inicio, f_actual))

    while queda() > 0:
        nueva = romper_y_rearmar(ctx, actual, fraccion, constructiva, rng)
        nueva = busqueda_local(ctx, nueva, queda(), relocate, swap)
        f_nueva = ctx.valor(nueva)
        if f_nueva < f_actual - TOL:          # sólo se aceptan mejoras
            actual, f_actual = nueva, f_nueva
            if historia is not None:
                historia.append((time.perf_counter() - inicio, f_actual))
    return actual
