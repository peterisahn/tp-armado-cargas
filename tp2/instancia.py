"""Lectura de instancias y escritura de soluciones.

Formato de entrada:
    n C -> entero n (productos) y real C (capacidad de cada vehículo)
    w_0 t_0 -> n líneas: peso y temperatura de cada producto (reales)
    s_00 s_01 ... s_0n-1 -> n líneas: matriz de similitudes n x n (simétrica, s_ii = 1)

Formato de salida:
    una línea por vehículo usado, con los índices (desde 0) de sus productos
    separados por un espacio.

Sólo usa la biblioteca estándar de Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

# Tolerancia para comparar números reales (simetría, s_ii = 1, capacidad).
TOL = 1e-9


@dataclass
class Instancia:
    """Datos de una instancia. Los productos se indexan desde 0."""

    n: int
    capacidad: float
    pesos: List[float]
    temperaturas: List[float]
    similitudes: List[List[float]]

    @property
    def peso_total(self) -> float:
        return sum(self.pesos)


class FormatoInvalido(ValueError):
    """La instancia no respeta el formato o las condiciones del enunciado."""


def parsear_instancia(texto: str) -> Instancia:
    """Convierte el contenido de un archivo de entrada en una Instancia.

    Separa por espacios en blanco (tolera espacios o saltos de línea de más) y
    valida el formato. Lanza FormatoInvalido con un mensaje claro si algo no cierra.
    """
    tokens = texto.split()
    if len(tokens) < 2:
        raise FormatoInvalido("Falta la primera línea 'n C'.")

    try:
        n_real = float(tokens[0])
    except ValueError:
        raise FormatoInvalido(f"n debe ser un entero; se leyó {tokens[0]!r}.")
    if n_real != int(n_real) or n_real < 1:
        raise FormatoInvalido(f"n debe ser un entero positivo; se leyó {tokens[0]!r}.")
    n = int(n_real)

    capacidad = _a_real(tokens[1], "la capacidad C")
    if capacidad <= 0:
        raise FormatoInvalido(f"La capacidad debe ser positiva; se leyó {capacidad}.")

    esperados = 2 + 2 * n + n * n
    if len(tokens) != esperados:
        raise FormatoInvalido(
            f"Con n = {n} se esperan {esperados} números (2 + 2n + n²) y hay {len(tokens)}."
        )

    pesos: List[float] = []
    temperaturas: List[float] = []
    pos = 2
    for i in range(n):
        w = _a_real(tokens[pos], f"el peso del producto {i}")
        t = _a_real(tokens[pos + 1], f"la temperatura del producto {i}")
        if w <= 0:
            raise FormatoInvalido(f"El peso del producto {i} debe ser > 0; se leyó {w}.")
        if w > capacidad + TOL:
            raise FormatoInvalido(
                f"El producto {i} pesa {w} y no entra en ningún vehículo (C = {capacidad})."
            )
        pesos.append(w)
        temperaturas.append(t)
        pos += 2

    similitudes: List[List[float]] = []
    for i in range(n):
        fila = [_a_real(tokens[pos + j], f"s[{i}][{j}]") for j in range(n)]
        similitudes.append(fila)
        pos += n

    _validar_similitudes(similitudes)
    return Instancia(n, capacidad, pesos, temperaturas, similitudes)


def leer_instancia(ruta: str) -> Instancia:
    """Lee una instancia desde un archivo."""
    with open(ruta, encoding="utf-8") as f:
        return parsear_instancia(f.read())


def formatear_solucion(vehiculos: Sequence[Sequence[int]]) -> str:
    """Devuelve el texto de salida: una línea por vehículo no vacío.

    Los índices de cada línea se ordenan de menor a mayor para que la salida sea
    determinística
    """
    lineas = [" ".join(str(i) for i in sorted(v)) for v in vehiculos if len(v) > 0]
    return "\n".join(lineas) + "\n"


def escribir_solucion(ruta: str, vehiculos: Sequence[Sequence[int]]) -> None:
    """Escribe la solución en el formato del enunciado."""
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(formatear_solucion(vehiculos))


def parsear_solucion(texto: str) -> List[List[int]]:
    """Lee una salida (una línea por vehículo). Ignora líneas vacías."""
    vehiculos = []
    for nro, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            vehiculos.append([int(x) for x in linea.split()])
        except ValueError:
            raise FormatoInvalido(f"Línea {nro} de la solución: índices no enteros: {linea!r}.")
    return vehiculos


def leer_solucion(ruta: str) -> List[List[int]]:
    with open(ruta, encoding="utf-8") as f:
        return parsear_solucion(f.read())


# ---------------------------------------------------------------- auxiliares

def _a_real(token: str, que: str) -> float:
    try:
        return float(token)
    except ValueError:
        raise FormatoInvalido(f"No se pudo leer {que}: {token!r} no es un número.")


def _validar_similitudes(s: List[List[float]]) -> None:
    n = len(s)
    for i in range(n):
        if abs(s[i][i] - 1.0) > TOL:
            raise FormatoInvalido(f"La diagonal debe valer 1: s[{i}][{i}] = {s[i][i]}.")
        for j in range(n):
            if not (-TOL <= s[i][j] <= 1.0 + TOL):
                raise FormatoInvalido(f"s[{i}][{j}] = {s[i][j]} está fuera de [0, 1].")
            if j > i and abs(s[i][j] - s[j][i]) > TOL:
                raise FormatoInvalido(
                    f"La matriz no es simétrica: s[{i}][{j}] = {s[i][j]} y s[{j}][{i}] = {s[j][i]}."
                )
