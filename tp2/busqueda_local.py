"""Búsqueda local: operadores relocate y swap.

  - relocate: sacar un producto de su camión A y ponerlo en otro camión B que ya existe.
  - swap: intercambiar dos productos de camiones distintos.

Una movida se acepta sólo si baja f.
Las dos se alternan hasta que ninguna mejora: ahí la solución es un óptimo local.

Cómo se chequea una movida, de lo más barato a lo más caro:
  1. el peso: guardamos la carga de cada camión en una lista (se actualiza al mover);
  2. la compatibilidad (temperatura y theta) con los productos del camión de destino;
  3. cuánto cambia f: sólo cambian dos camiones, A y B, así que
        delta = costo(A nuevo) + costo(B nuevo) - costo(A viejo) - costo(B viejo)
     con costo(camión) = alpha - beta * (similitud del camión), o 0 si quedó vacío.

Cómo baja la cantidad de camiones: cuando relocate saca el último producto de un camión,
el camión queda vacío y su costo pasa a 0. Relocate nunca abre un 
camión nuevo: esa movida siempre empeora f.
"""

from __future__ import annotations

import time
from typing import List

from .instancia import TOL
from .modelo import Contexto

Solucion = List[List[int]]


def pasada_relocate(ctx: Contexto, camiones: Solucion, limite: float) -> bool:
    """Recorre cada producto y lo mueve al primer camión donde f baja. Devuelve True si
    hizo algún cambio. Vecindario: n productos x K camiones. Corta si el reloj pasa
    `limite`."""
    w, C = ctx.inst.pesos, ctx.inst.capacidad
    cargas = [ctx.carga(c) for c in camiones]
    mejoro = False
    for a, A in enumerate(camiones):
        if time.perf_counter() > limite:
            break
        for i in list(A):
            for b, B in enumerate(camiones):
                if b == a or not B:
                    continue
                if cargas[b] + w[i] > C + TOL or not ctx.compatible_con(i, B):
                    continue
                A_nuevo = [x for x in A if x != i]
                B_nuevo = B + [i]
                delta = (ctx.costo(A_nuevo) + ctx.costo(B_nuevo)
                         - ctx.costo(A) - ctx.costo(B))
                if delta < -TOL:   # TOL: no aceptar mejoras que son sólo redondeo
                    A.remove(i)
                    B.append(i)
                    cargas[a] -= w[i]
                    cargas[b] += w[i]
                    mejoro = True
                    break
    return mejoro


def pasada_swap(ctx: Contexto, camiones: Solucion, limite: float) -> bool:
    """Prueba intercambiar cada par de productos de camiones distintos y aplica el
    primer intercambio que baja f. Devuelve True si hizo algún cambio. Vecindario: O(n²)
    pares. Corta si el reloj pasa `limite`."""
    w, C = ctx.inst.pesos, ctx.inst.capacidad
    cargas = [ctx.carga(c) for c in camiones]
    mejoro = False
    for a in range(len(camiones)):
        if time.perf_counter() > limite:
            break
        for b in range(a + 1, len(camiones)):
            A, B = camiones[a], camiones[b]
            for i in list(A):
                for j in list(B):
                    # ¿entran por peso? (A pierde i y gana j; B pierde j y gana i)
                    if (cargas[a] - w[i] + w[j] > C + TOL
                            or cargas[b] - w[j] + w[i] > C + TOL):
                        continue
                    if not (ctx.compatible_con(j, A, sale=i)
                            and ctx.compatible_con(i, B, sale=j)):
                        continue
                    A_nuevo = [x for x in A if x != i] + [j]
                    B_nuevo = [x for x in B if x != j] + [i]
                    delta = (ctx.costo(A_nuevo) + ctx.costo(B_nuevo)
                             - ctx.costo(A) - ctx.costo(B))
                    if delta < -TOL:
                        A.remove(i)
                        A.append(j)
                        B.remove(j)
                        B.append(i)
                        cargas[a] += w[j] - w[i]
                        cargas[b] += w[i] - w[j]
                        mejoro = True
                        break          # i ya no está en A: seguir con el próximo producto
    return mejoro


def busqueda_local(ctx: Contexto, camiones: Solucion, tiempo_max: float = float("inf"),
                   relocate: bool = True, swap: bool = True) -> Solucion:
    """Aplica pasadas de relocate y de swap hasta que ninguna mejora (óptimo local) o
    hasta que pasen tiempo_max segundos. relocate / swap = False apagan un operador."""
    camiones = [list(c) for c in camiones]
    limite = time.perf_counter() + tiempo_max
    mejoro = True
    while mejoro and time.perf_counter() < limite:
        mejoro = False
        if relocate and pasada_relocate(ctx, camiones, limite):
            mejoro = True
        camiones = [c for c in camiones if c]          # sacar los camiones vacíos
        if swap and pasada_swap(ctx, camiones, limite):
            mejoro = True
    return camiones
