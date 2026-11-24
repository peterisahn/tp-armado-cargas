"""Generación de instancias con temperaturas y similitudes a partir de pesos de BPPLIB.

BPPLIB sólo trae pesos y capacidad. Para cada producto se sortea una
familia de supermercado según una mezcla típica de pedido online. La familia determina:
  - la temperatura de conservación
  - la similitud con los demás productos, a partir de una matriz de afinidad entre
    familias más un ruido chico.

Así los datos tienen la estructura que describe el enunciado: dos cortes de carne con
similitud cerca de 1, carne y jabón cerca de 0. Todo es reproducible con una
semilla.
"""

from __future__ import annotations

import random
from typing import List, Sequence, Tuple

# (nombre, proporción en el pedido, temperaturas posibles en °C)
FAMILIAS: List[Tuple[str, float, Tuple[float, ...]]] = [
    ("congelados", 0.10, (-18.0, -20.0)),
    ("carnes", 0.12, (2.0, 4.0)),
    ("lacteos", 0.14, (4.0,)),
    ("verduleria", 0.14, (4.0, 8.0)),
    ("panaderia", 0.08, (20.0,)),
    ("almacen", 0.20, (20.0, 22.0)),
    ("bebidas", 0.08, (20.0,)),
    ("limpieza", 0.10, (20.0,)),
    ("comidas_listas", 0.04, (65.0,)),
]
NOMBRES = [f[0] for f in FAMILIAS]

# Afinidad entre familias (simétrica). Diagonal 0.9; lo no listado vale AFINIDAD_BASE.
AFINIDAD_BASE = 0.25
_AFIN = {
    ("congelados", "carnes"): 0.6, ("congelados", "lacteos"): 0.5,
    ("carnes", "lacteos"): 0.4, ("carnes", "verduleria"): 0.3,
    ("lacteos", "verduleria"): 0.4, ("lacteos", "almacen"): 0.3,
    ("verduleria", "panaderia"): 0.5, ("verduleria", "almacen"): 0.4,
    ("panaderia", "almacen"): 0.6, ("panaderia", "bebidas"): 0.4,
    ("almacen", "bebidas"): 0.7, ("bebidas", "lacteos"): 0.3,
    ("comidas_listas", "panaderia"): 0.3,
}
for _f in NOMBRES:
    if _f != "limpieza":
        _AFIN[("limpieza", _f)] = 0.05     # limpieza con alimentos: casi incompatible
_AFIN[("limpieza", "bebidas")] = 0.10
for _f in NOMBRES:
    if _f not in ("limpieza", "comidas_listas", "panaderia"):
        _AFIN.setdefault(("comidas_listas", _f), 0.2)

RUIDO = 0.08  # desvío del ruido gaussiano sumado a la afinidad


def afinidad(f: str, g: str) -> float:
    if f == g:
        return 0.9
    return _AFIN.get((f, g), _AFIN.get((g, f), AFINIDAD_BASE))


def generar(pesos: Sequence[float], capacidad: float, semilla: int):
    """Devuelve (familias, temperaturas, similitudes) para los pesos dados, con la mezcla
    típica de un pedido (columna de proporciones de FAMILIAS)"""
    rng = random.Random(semilla)
    n = len(pesos)
    props = [f[1] for f in FAMILIAS]
    familias = rng.choices(NOMBRES, weights=props, k=n)
    temps_por_fam = {f[0]: f[2] for f in FAMILIAS}
    temperaturas = [rng.choice(temps_por_fam[f]) for f in familias]
    s = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = afinidad(familias[i], familias[j]) + rng.gauss(0.0, RUIDO)
            v = round(min(1.0, max(0.0, v)), 3)
            s[i][j] = s[j][i] = v
    return familias, temperaturas, s


def formatear_instancia(capacidad: float, pesos: Sequence[float],
                        temperaturas: Sequence[float], s: Sequence[Sequence[float]]) -> str:
    """Texto en el formato de entrada del enunciado"""
    n = len(pesos)
    lineas = [f"{n} {capacidad:g}"]
    lineas += [f"{w:g} {t:g}" for w, t in zip(pesos, temperaturas)]
    lineas += [" ".join(f"{x:g}" for x in fila) for fila in s]
    return "\n".join(lineas) + "\n"


def leer_bpplib(ruta: str) -> Tuple[float, List[float]]:
    """Lee una instancia BPPLIB (n, c y n pesos, un número por línea)"""
    with open(ruta, encoding="latin-1") as f:
        tok = f.read().split()
    n, c = int(tok[0]), float(tok[1])
    pesos = [float(x) for x in tok[2:2 + n]]
    if len(pesos) != n:
        raise ValueError(f"{ruta}: se esperaban {n} pesos")
    return c, pesos
