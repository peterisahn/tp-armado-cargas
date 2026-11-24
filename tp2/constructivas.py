"""Las dos heurísticas constructivas del TP

Las dos recorren los productos de mayor a menor peso y ponen cada uno en un camión donde
entra (peso + compatibilidad). Sólo cambia cómo eligen el camión:

  - "bfd" Best Fit Decreasing: el camión que queda más lleno (si empatan, 
  el que suma más similitud).
  - "parecido" Más parecido: el camión con el que i suma más similitud (si 
  empatan, el que queda más lleno).

Si el producto no entra en ningún camión, se abre uno nuevo.

Ordenamos de pesos mayores a menores porque los productos grandes son 
los difíciles de ubicar; si quedan para el final no entran en ningún lado. 
Los chicos rellenan huecos.

Complejidad: ordenar O(n log n) + para cada producto se revisan los K camiones
y en cada uno sus b productos: O(n * K * b).
"""

from __future__ import annotations

from typing import List, Optional

from .modelo import Contexto

Solucion = List[List[int]]
CONSTRUCTIVAS = ("bfd", "parecido")


def construir(ctx: Contexto, criterio: str, orden: Optional[List[int]] = None,
              camiones: Optional[Solucion] = None) -> Solucion:
    """Ubica los productos de `orden` uno por uno según el criterio ("bfd" o "parecido").

    Por defecto ubica todos los productos, de mayor a menor peso, empezando sin camiones.
    El ILS la usa también para rearmar: le pasa los camiones que quedaron (`camiones`) y
    los productos sueltos (`orden`)."""
    if criterio not in CONSTRUCTIVAS:
        raise ValueError(f"criterio debe ser uno de {CONSTRUCTIVAS}")
    pesos = ctx.inst.pesos
    camiones = [list(c) for c in camiones] if camiones else []
    if orden is None:
        orden = sorted(range(ctx.inst.n), key=lambda i: -pesos[i])

    for i in orden:
        candidatos = [c for c in camiones if ctx.entra(i, c)]
        if not candidatos:
            camiones.append([i])                       # abrir un camión nuevo
            continue
        if criterio == "bfd":
            elegido = max(candidatos, key=lambda c: (ctx.carga(c), ctx.similitud_con(i, c)))
        else:
            elegido = max(candidatos, key=lambda c: (ctx.similitud_con(i, c), ctx.carga(c)))
        elegido.append(i)
    return camiones


def best_fit_decreasing(ctx: Contexto) -> Solucion:
    """Heurística 1: cada producto al camión donde queda más lleno."""
    return construir(ctx, "bfd")


def mas_parecido(ctx: Contexto) -> Solucion:
    """Heurística 2: cada producto al camión donde suma más similitud."""
    return construir(ctx, "parecido")
