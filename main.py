"""Programa principal del TP2.

Uso:
    python3 main.py <input> <output> [opciones]
    python3 main.py <input> <solucion> --evaluar [opciones]

- Lee la instancia de <input> (formato del enunciado, pág. 2).
- La resuelve con el algoritmo elegido, respetando el modelo (temperatura y similitud
  mínima), y escribe la solución en <output> (pág. 3).
- Con --evaluar, en cambio, lee una solución que ya está en <solucion>, la valida y
  muestra sus medidas.

Por defecto usa el modelo elegido (informe, sección 3): ventanas de temperatura de
inocuidad, similitud mínima theta = 0.2, alpha = 1 y beta = lam / pares de un camión lleno con
lam = 1; y el algoritmo ILS. Todos los parámetros están en el README.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Callable, Dict, List

from tp2.busqueda_local import busqueda_local
from tp2.constructivas import CONSTRUCTIVAS, construir
from tp2.instancia import FormatoInvalido, escribir_solucion, leer_instancia, leer_solucion
from tp2.metaheuristica import ils
from tp2.metricas import metricas
from tp2.modelo import MODOS_TEMPERATURA, Contexto, Modelo
from tp2.solucion import SolucionInvalida, validar

Solucion = List[List[int]]


def solucion_bfd(ctx: Contexto, args: argparse.Namespace) -> Solucion:
    """Constructiva 1 sola: Best Fit Decreasing."""
    return construir(ctx, "bfd")


def solucion_parecido(ctx: Contexto, args: argparse.Namespace) -> Solucion:
    """Constructiva 2 sola: Más parecido."""
    return construir(ctx, "parecido")


def solucion_bl(ctx: Contexto, args: argparse.Namespace) -> Solucion:
    """La constructiva elegida (--constructiva) + búsqueda local hasta un óptimo local."""
    return busqueda_local(ctx, construir(ctx, args.constructiva), args.tiempo,
                          args.relocate, args.swap)


def solucion_ils(ctx: Contexto, args: argparse.Namespace) -> Solucion:
    """Metaheurística: Iterated Local Search con romper y rearmar."""
    return ils(ctx, args.tiempo, args.semilla, args.fraccion, args.constructiva,
               args.relocate, args.swap)


# Algoritmos disponibles: nombre -> función(contexto, args) -> solución.
ALGORITMOS: Dict[str, Callable[[Contexto, argparse.Namespace], Solucion]] = {
    "bfd": solucion_bfd,
    "parecido": solucion_parecido,
    "bl": solucion_bl,
    "ils": solucion_ils,
}


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TP2 TD5: armado de cargas para supermercado.")
    p.add_argument("input", help="archivo de la instancia")
    p.add_argument("output", help="archivo donde escribir la solución (o leerla, con --evaluar)")
    p.add_argument("--algoritmo", choices=list(ALGORITMOS), default="ils")
    p.add_argument("--constructiva", choices=CONSTRUCTIVAS, default="parecido",
                   help="bl e ils: con qué constructiva arrancar (default parecido)")
    p.add_argument("--operadores", default="relocate,swap",
                   help="bl e ils: operadores de búsqueda local, separados por coma "
                        "(default relocate,swap)")
    p.add_argument("--tiempo", type=float, default=10.0, help="segundos máximos (default 10)")
    p.add_argument("--semilla", type=int, default=0, help="semilla aleatoria (default 0)")
    p.add_argument("--fraccion", type=float, default=0.25,
                   help="ils: parte de los camiones que se vacía en cada vuelta, además del "
                        "menos cargado (default 0.25 = un cuarto)")
    m = p.add_argument_group("modelo (ver el informe, sección 3)")
    m.add_argument("--temperatura", choices=MODOS_TEMPERATURA, default="ventanas")
    m.add_argument("--delta", type=float, default=20.0, help="rango máximo para --temperatura umbral")
    m.add_argument("--theta", type=float, default=0.2, help="similitud mínima entre productos de un camión")
    m.add_argument("--lam", type=float, default=1.0, help="peso normalizado de la similitud (beta/alpha)")
    m.add_argument("--alpha", type=float, default=None, help="fija alpha a mano (ignora la normalización)")
    m.add_argument("--beta", type=float, default=None, help="fija beta a mano (ignora la normalización)")
    p.add_argument("--evaluar", action="store_true",
                   help="no resolver: validar y evaluar la solución que está en <output>")
    return p


def main(argv: List[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        modelo = Modelo(args.temperatura, args.delta, args.theta, args.lam)
        if (args.alpha is not None and args.alpha < 0) or (args.beta is not None and args.beta < 0):
            raise ValueError("alpha y beta deben ser >= 0 (enunciado, pág. 2)")
        if not 0 <= args.fraccion <= 1 or args.tiempo <= 0:
            raise ValueError("--fraccion debe estar entre 0 y 1 y --tiempo > 0")
        ops = {x.strip() for x in args.operadores.split(",") if x.strip()}
        if not ops <= {"relocate", "swap"}:
            raise ValueError("--operadores acepta relocate, swap o los dos (relocate,swap)")
        args.relocate, args.swap = "relocate" in ops, "swap" in ops
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    try:
        inst = leer_instancia(args.input)
        ctx = modelo.preparar(inst)
        if args.alpha is not None:
            ctx.alpha = args.alpha
        if args.beta is not None:
            ctx.beta = args.beta
        if args.evaluar:
            camiones = leer_solucion(args.output)
            segundos = 0.0
        else:
            inicio = time.perf_counter()
            camiones = ALGORITMOS[args.algoritmo](ctx, args)
            segundos = time.perf_counter() - inicio
            escribir_solucion(args.output, camiones)
        validar(inst, camiones)
    except (OSError, FormatoInvalido, SolucionInvalida) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    m = metricas(inst, camiones)
    respeta = all(ctx.camion_valido(c) for c in camiones)
    print(f"instancia: n={inst.n}, C={inst.capacidad:g} · modelo: {modelo.describir()}")
    print(f"alpha={ctx.alpha:g}, beta={ctx.beta:.6g}")
    print(f"camiones K={m['K']} (mínimo por peso: {ctx.camiones_minimos})")
    print(f"similitud total={m['similitud_total']:.4f} · media por par={m['similitud_media_par']:.3f}")
    print(f"objetivo f={ctx.valor(camiones):.4f}")
    print(f"respeta el modelo: {'sí' if respeta else 'NO'} · camiones con mezcla insegura: "
          f"{m['vehiculos_inseguros']}")
    if not args.evaluar:
        print(f"tiempo={segundos:.2f} s · solución escrita en {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
