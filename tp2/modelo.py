from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from .instancia import TOL, Instancia

INF = float("inf")

CATEGORIAS = ("congelado", "refrigerado", "ambiente", "caliente")

# Ventanas de transporte por categoría (°C). Fuente: USDA FSIS (frío <= 40 °F = 4,4 °C;
# caliente >= 140 °F = 60 °C; freezer 0 °F = -18 °C).
VENTANAS_INOCUIDAD: Dict[str, Tuple[float, float]] = {
    "congelado": (-30.0, -18.0),
    "refrigerado": (0.0, 4.0),
    "ambiente": (0.0, 30.0),
    "caliente": (60.0, 80.0),
}

MODOS_TEMPERATURA = ("ninguno", "umbral", "zonas", "ventanas")


def categoria(t: float) -> str:
    """Categoría de conservación según la temperatura del producto."""
    if t <= -10:
        return "congelado"
    if t <= 10:
        return "refrigerado"
    # Entre 30 y 60 °C no hay temperatura de guarda segura: algo declarado a 40 °C o más
    # sólo puede ser comida caliente, que tiene que viajar a 60 °C o más.
    if t < 40:
        return "ambiente"
    return "caliente"


def inseguro(categorias: Sequence[str]) -> bool:
    """Vale True si el camión mezcla categorías sin una temperatura segura en común (según
    VENTANAS_INOCUIDAD). Es una métrica: sirve para juzgar cualquier solución con la misma
    vara, sin importar con qué modelo se armó."""
    lo = max(VENTANAS_INOCUIDAD[c][0] for c in categorias)
    hi = min(VENTANAS_INOCUIDAD[c][1] for c in categorias)
    return lo > hi + TOL


@dataclass
class Modelo:
    """Decisiones de modelado. Los defaults son el modelo elegido (igual que main.py)."""

    temperatura: str = "ventanas"   # uno de MODOS_TEMPERATURA
    delta: float = 20.0             # sólo para "umbral"
    theta: float = 0.2              # similitud mínima entre productos de un camión
    lam: float = 1.0                # peso normalizado de la similitud

    def __post_init__(self) -> None:
        if self.temperatura not in MODOS_TEMPERATURA:
            raise ValueError(f"temperatura debe ser una de {MODOS_TEMPERATURA}")
        if self.delta < 0 or self.lam < 0 or not (0 <= self.theta <= 1):
            raise ValueError("delta >= 0, lam >= 0 y 0 <= theta <= 1")

    def ventana(self, t: float) -> Tuple[float, float]:
        if self.temperatura == "ninguno":
            return (-INF, INF)
        if self.temperatura == "umbral":
            return (t - self.delta / 2, t + self.delta / 2)
        c = categoria(t)
        if self.temperatura == "zonas":
            k = float(CATEGORIAS.index(c))
            return (k, k)
        return VENTANAS_INOCUIDAD[c]

    def preparar(self, inst: Instancia) -> "Contexto":
        return Contexto(inst, self)

    def describir(self) -> str:
        t = self.temperatura + (f"(D={self.delta:g})" if self.temperatura == "umbral" else "")
        return f"temp={t} theta={self.theta:g} lam={self.lam:g}"


class Contexto:
    """El modelo aplicado a una instancia. Tiene todo lo que usan los algoritmos:
    compatibilidad, carga, similitud y el valor de f."""

    def __init__(self, inst: Instancia, modelo: Modelo):
        self.inst = inst
        self.theta = modelo.theta
        ventanas = [modelo.ventana(t) for t in inst.temperaturas]
        self.L = [lo for lo, _ in ventanas]
        self.U = [hi for _, hi in ventanas]
        # Mínima cantidad de camiones si sólo importara el peso: ceil(peso total / C).
        # (Se resta TOL para que un redondeo como 20.000000001 / 10 no sume un camión.)
        self.camiones_minimos = max(1, math.ceil(inst.peso_total / inst.capacidad - TOL))
        b = inst.n / self.camiones_minimos          # productos por camión lleno
        self.pares_camion_lleno = max(1.0, b * (b - 1) / 2)
        self.alpha = 1.0
        self.beta = modelo.lam / self.pares_camion_lleno

    # ---------------------------------------------------------------- reglas

    def compatibles(self, i: int, j: int) -> bool:
        """¿Pueden i y j viajar en el mismo camión? (ventanas que se cortan y s_ij >= theta)"""
        if max(self.L[i], self.L[j]) > min(self.U[i], self.U[j]) + TOL:
            return False
        return self.inst.similitudes[i][j] >= self.theta - TOL

    def carga(self, camion: Sequence[int]) -> float:
        return sum(self.inst.pesos[i] for i in camion)

    def compatible_con(self, i: int, camion: Sequence[int], sale: int = -1) -> bool:
        """¿Es i compatible con todos los productos del camión (salvo 'sale')?"""
        for j in camion:
            if j != sale and not self.compatibles(i, j):
                return False
        return True

    def entra(self, i: int, camion: Sequence[int]) -> bool:
        """¿Puede i subir a este camión? Primero el peso, después la compatibilidad."""
        if self.carga(camion) + self.inst.pesos[i] > self.inst.capacidad + TOL:
            return False
        return self.compatible_con(i, camion)

    def camion_valido(self, camion: Sequence[int]) -> bool:
        """Capacidad + todos los pares compatibles."""
        if self.carga(camion) > self.inst.capacidad + TOL:
            return False
        return all(self.compatibles(camion[a], camion[b])
                   for a in range(len(camion)) for b in range(a + 1, len(camion)))

    # ---------------------------------------------------------------- similitud y objetivo

    def similitud_con(self, i: int, camion: Sequence[int]) -> float:
        """Suma de s_ij entre i y los productos del camión (i todavía no está en él)."""
        s = self.inst.similitudes[i]
        return sum(s[j] for j in camion)

    def similitud(self, camion: Sequence[int]) -> float:
        """Suma de s_ij de todos los pares del camión."""
        s = self.inst.similitudes
        return sum(s[camion[a]][camion[b]]
                   for a in range(len(camion)) for b in range(a + 1, len(camion)))

    def costo(self, camion: Sequence[int]) -> float:
        """Lo que aporta un camión a f: alpha si se usa, menos beta por su similitud."""
        if not camion:
            return 0.0
        return self.alpha - self.beta * self.similitud(camion)

    def valor(self, camiones: Sequence[Sequence[int]]) -> float:
        """f = alpha*K - beta*S de una solución (suma de los costos de los camiones)."""
        return sum(self.costo(c) for c in camiones)
