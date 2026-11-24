"""Experimentos del TP2 (diseño y lectura en el informe, secciones 3 y 7).

Las 70 instancias están en instancias/experimentos/ (scripts/generar_instancias.py).

  MODELO (sección 3 del informe). Se resuelve siempre con Más parecido + búsqueda local
  (relocate y swap hasta que ninguna movida mejore): no usa el reloj, así que cada
  corrida da siempre el mismo resultado.
    M1  ¿Qué regla de temperatura?        4 reglas (θ = 0, λ = 1)
    M2  ¿Qué similitud mínima θ?          θ = 0 / 0,1 / 0,2 / 0,3 (ventanas, λ = 1)
    M3  ¿Cuánto pesa la similitud (λ)?    λ = 0 / 0,1 / 1 / 10 (ventanas, θ = 0,2)

  ALGORITMOS (sección 7 del informe), con el modelo elegido (ventanas, θ = 0,2, λ = 1).
    A1  ¿Qué combinación conviene?  2 constructivas × {sola, +relocate, +swap, +los dos}
                                    y el ILS (5 s, vaciando un cuarto) con cada constructiva
                                    y cada operador
    A2  Ajuste del ILS: ¿cuánto romper y cuánto tiempo darle?
                                    fracción 1/4, 1/2 y 3/4; f a los 1, 5 y 30 s
    A3  ¿Qué tan cerca del óptimo?   300 instancias chicas (10 a 14 productos) con el
                                    óptimo exacto por fuerza bruta; BFD, Más parecido,
                                    búsqueda local e ILS (1 s)
    A4  ¿Y un día grande?            18 instancias de 1000 productos (Falkenauer U1000):
                                    tiempo y f de la constructiva, la búsqueda local y el
                                    ILS a los 10 s, 1 min y 3 min

Uso:
    python3 scripts/experimentos.py modelo    # M1, M2 y M3   (≈ 1 min)
    python3 scripts/experimentos.py a1        # A1            (≈ 4 min)
    python3 scripts/experimentos.py a2        # A2            (≈ 12 min)
    python3 scripts/experimentos.py a3        # A3            (≈ 3 min)
    python3 scripts/experimentos.py a4        # A4            (≈ 7 min; necesita externos/BPPLIB)
    python3 scripts/experimentos.py informe   # tablas (resumen.md) y gráficos, sin correr
    python3 scripts/experimentos.py todo

Salida en resultados/experimentos/: modelo.csv, a1.csv ... a4.csv (una fila por corrida),
resumen.md (las tablas del informe) y a1.png ... a4.png. Los gráficos usan matplotlib, sólo
en este script (el programa no lo necesita). 9 procesos en paralelo, semilla fija.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics as st
import sys
import time
from multiprocessing import Pool

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from tp2 import generador  # noqa: E402
from tp2.busqueda_local import busqueda_local  # noqa: E402
from tp2.constructivas import construir  # noqa: E402
from tp2.instancia import Instancia, leer_instancia  # noqa: E402
from tp2.metaheuristica import ils  # noqa: E402
from tp2.metricas import metricas  # noqa: E402
from tp2.modelo import Modelo  # noqa: E402
from tp2.solucion import validar  # noqa: E402

INST = os.path.join(RAIZ, "instancias", "experimentos")
SALIDA = os.path.join(RAIZ, "resultados", "experimentos")
SEMILLA = 12345
PROCESOS = 9
ELEGIDO = dict(temperatura="ventanas", theta=0.2, lam=1.0)
ALIMENTOS = {"congelados", "carnes", "lacteos", "verduleria", "panaderia", "almacen",
             "comidas_listas"}      # bebidas no cuenta como alimento para "limpieza con comida"

# ---------------------------------------------------------------- configuraciones
M1 = [("Sin regla de temperatura", "ninguno"), ("Diferencia máxima de 20 °C", "umbral"),
      ("Separar por categorías", "zonas"), ("Ventanas de temperatura (elegida)", "ventanas")]
M2 = [0.0, 0.1, 0.2, 0.3]
M3 = [0.0, 0.1, 1.0, 10.0]

NOMBRE_C = {"bfd": "BFD", "parecido": "Más parecido"}
A1 = []   # (etiqueta, constructiva, búsqueda local: None / "relocate" / "swap" / "ambos", ils)
for _c in ("bfd", "parecido"):
    A1.append((f"{NOMBRE_C[_c]}", _c, None, False))
    for _op, _nom in (("relocate", "relocate"), ("swap", "swap"), ("ambos", "relocate + swap")):
        A1.append((f"{NOMBRE_C[_c]} + {_nom}", _c, _op, False))
for _c in ("bfd", "parecido"):
    for _op, _nom in (("relocate", "relocate"), ("swap", "swap"), ("ambos", "relocate + swap")):
        A1.append((f"ILS desde {NOMBRE_C[_c]}, con {_nom}", _c, _op, True))
TIEMPO_ILS = 5.0

A2_FRACCIONES = [0.25, 0.5, 0.75]
A2_TIEMPOS = [1.0, 5.0, 30.0]

A3_INSTANCIAS = 300            # instancias chicas: n entre 10 y 14, pesos 1..6, C = 10
A3_ILS = 1.0                   # segundos de ILS en cada una
A3_METODOS = ["BFD", "Más parecido", "Más parecido + búsqueda local", "ILS (1 s)"]

A4_INSTANCIAS = [f"Falkenauer_u1000_{k:02d}" for k in range(18)]   # 2 tandas de 9 procesos
A4_TIEMPOS = [10.0, 60.0, 180.0]


def indice():
    return list(csv.DictReader(open(os.path.join(INST, "indice.csv"))))


# ---------------------------------------------------------------- una corrida

def correr(t: dict) -> dict:
    """Resuelve una instancia con una configuración y devuelve las medidas."""
    inst = leer_instancia(os.path.join(INST, t["nombre"] + ".txt"))
    fam = open(os.path.join(INST, t["nombre"] + ".familias")).read().split()
    ctx = Modelo(temperatura=t["temperatura"], theta=t["theta"], lam=t["lam"]).preparar(inst)
    ops = t.get("ops", "ambos")
    relocate, swap = ops in ("relocate", "ambos"), ops in ("swap", "ambos")
    hist = [] if t.get("historia") else None

    inicio = time.perf_counter()
    if t.get("ils"):
        sol = ils(ctx, t["tiempo"], SEMILLA, t.get("fraccion", 0.25), t["constructiva"],
                  relocate, swap, historia=hist)
    else:
        sol = construir(ctx, t["constructiva"])
        if ops is not None:
            sol = busqueda_local(ctx, sol, relocate=relocate, swap=swap)
    segundos = time.perf_counter() - inicio

    validar(inst, sol)
    assert all(ctx.camion_valido(c) for c in sol)
    m = metricas(inst, sol)
    con_limpieza = [c for c in sol if any(fam[i] == "limpieza" for i in c)]
    con_comida = [c for c in con_limpieza if any(fam[i] in ALIMENTOS for i in c)]
    out = {k: v for k, v in t.items() if k != "historia"}
    out.update(K=len(sol), extra=len(sol) - int(t["opt"]),
               f=round(Modelo(**ELEGIDO).preparar(inst).valor(sol), 5),  # siempre la misma vara
               sim=round(m["similitud_media_par"], 5), inseguros=m["vehiculos_inseguros"],
               limpieza=len(con_limpieza), limpieza_comida=len(con_comida),
               segundos=round(segundos, 4))
    if hist is not None:
        out["historia"] = json.dumps([(round(a, 3), round(b, 5)) for a, b in hist])
    return out


def correr_todas(tareas: list, nombre: str) -> None:
    os.makedirs(SALIDA, exist_ok=True)
    print(f"{nombre}: {len(tareas)} corridas", flush=True)
    ini = time.time()
    with Pool(PROCESOS) as p:
        res = p.map(correr, tareas, chunksize=1)
    campos = list(dict.fromkeys(k for r in res for k in r))
    with open(os.path.join(SALIDA, nombre + ".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(res)
    print(f"{nombre}: listo en {time.time() - ini:.0f} s", flush=True)


def tareas_modelo() -> list:
    t = []
    for f in indice():
        base = dict(nombre=f["nombre"], coleccion=f["coleccion"], opt=f["opt_bpp"],
                    constructiva="parecido", ops="ambos")
        for etiqueta, regla in M1:
            t.append(dict(base, exp="M1", etiqueta=etiqueta, temperatura=regla, theta=0.0, lam=1.0))
        for th in M2:
            t.append(dict(base, exp="M2", etiqueta=f"{th:g}", temperatura="ventanas", theta=th, lam=1.0))
        for la in M3:
            t.append(dict(base, exp="M3", etiqueta=f"{la:g}", temperatura="ventanas", theta=0.2, lam=la))
    return t


def tareas_a1() -> list:
    t = []
    for f in indice():
        for etiqueta, c, ops, es_ils in A1:
            t.append(dict(ELEGIDO, nombre=f["nombre"], coleccion=f["coleccion"], opt=f["opt_bpp"],
                          exp="A1", etiqueta=etiqueta, constructiva=c, ops=ops, ils=es_ils,
                          tiempo=TIEMPO_ILS))
    return t


def tareas_a2() -> list:
    return [dict(ELEGIDO, nombre=f["nombre"], coleccion=f["coleccion"], opt=f["opt_bpp"],
                 exp="A2", etiqueta=f"{fr:g}", constructiva="parecido", ops="ambos", ils=True,
                 fraccion=fr, tiempo=max(A2_TIEMPOS), historia=True)
            for f in indice() for fr in A2_FRACCIONES]


# ---------------------------------------------------------------- A3: distancia al óptimo

def optimo_exacto(ctx, n: int) -> float:
    """Mejor f posible, por fuerza bruta: prueba todas las formas válidas de repartir los
    productos (cada producto va a un camión donde entra, o a uno nuevo)."""
    mejor = [math.inf]
    camiones = []

    def ubicar(i):
        if i == n:
            mejor[0] = min(mejor[0], ctx.valor(camiones))
            return
        for c in camiones:
            if ctx.entra(i, c):
                c.append(i)
                ubicar(i + 1)
                c.pop()
        camiones.append([i])
        ubicar(i + 1)
        camiones.pop()

    ubicar(0)
    return mejor[0]


def correr_a3(semilla: int) -> list:
    """Una instancia chica: el óptimo exacto y lo que da cada método."""
    import random
    rng = random.Random(semilla)
    n_prod = rng.randint(10, 14)
    pesos = [float(rng.randint(1, 6)) for _ in range(n_prod)]
    _, temps, s = generador.generar(pesos, 10.0, semilla)
    inst = Instancia(n_prod, 10.0, pesos, temps, s)
    ctx = Modelo(**ELEGIDO).preparar(inst)
    opt = optimo_exacto(ctx, n_prod)
    bfd, mp = construir(ctx, "bfd"), construir(ctx, "parecido")
    sols = [bfd, mp, busqueda_local(ctx, mp), ils(ctx, A3_ILS, SEMILLA)]
    return [dict(exp="A3", semilla=semilla, n=n_prod, metodo=m, f=round(ctx.valor(x), 6),
                 opt=round(opt, 6), dif=round(ctx.valor(x) - opt, 6))
            for m, x in zip(A3_METODOS, sols)]


# ---------------------------------------------------------------- A4: días de 1000 productos

def correr_a4(nombre: str) -> dict:
    from scripts.generar_instancias import BPP, optimos_bpplib
    import zlib
    archivo = nombre + ".txt"
    capacidad, pesos = generador.leer_bpplib(
        os.path.join(BPP, "1_Falkenauer", "Falkenauer", "Falkenauer U", archivo))
    _, temps, s = generador.generar(pesos, capacidad, zlib.crc32(nombre.encode()))
    inst = Instancia(len(pesos), capacidad, pesos, temps, s)
    ctx = Modelo(**ELEGIDO).preparar(inst)
    opt = optimos_bpplib()[archivo]
    t0 = time.perf_counter()
    mp = construir(ctx, "parecido")
    t1 = time.perf_counter()
    bl = busqueda_local(ctx, mp)
    t2 = time.perf_counter()
    hist = []
    sol = ils(ctx, max(A4_TIEMPOS), SEMILLA, historia=hist)
    validar(inst, sol)
    return dict(exp="A4", nombre=nombre, n=len(pesos), opt=opt,
                f_constructiva=round(ctx.valor(mp), 4), s_constructiva=round(t1 - t0, 3),
                f_bl=round(ctx.valor(bl), 4), s_bl=round(t2 - t0, 3),
                extra_bl=len(bl) - opt, extra_ils=len(sol) - opt,
                historia=json.dumps([(round(a, 3), round(b, 5)) for a, b in hist]))


def correr_lista(funcion, tareas: list, nombre: str) -> None:
    os.makedirs(SALIDA, exist_ok=True)
    print(f"{nombre}: {len(tareas)} corridas", flush=True)
    ini = time.time()
    with Pool(PROCESOS) as p:
        res = p.map(funcion, tareas, chunksize=1)
    filas = [x for r in res for x in (r if isinstance(r, list) else [r])]
    with open(os.path.join(SALIDA, nombre + ".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"{nombre}: listo en {time.time() - ini:.0f} s", flush=True)


# ---------------------------------------------------------------- tablas

def leer(nombre: str) -> list:
    filas = list(csv.DictReader(open(os.path.join(SALIDA, nombre + ".csv"))))
    for r in filas:
        for k in ("extra", "f", "sim", "inseguros", "limpieza", "limpieza_comida", "segundos", "K"):
            r[k] = float(r[k])
    return filas


def prueba_signo(gana: int, pierde: int) -> float:
    """Probabilidad (a dos colas) de un resultado así de desparejo si los dos métodos
    fueran iguales: como sacar `gana` caras en `gana + pierde` tiradas de una moneda."""
    n, k = gana + pierde, max(gana, pierde)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def p_texto(p: float) -> str:
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def n(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def por(filas: list, etiqueta: str) -> dict:
    return {r["nombre"]: r for r in filas if r["etiqueta"] == etiqueta}


def duelo(filas: list, a: str, b: str) -> str:
    """Una fila de tabla: cuántas instancias gana a contra b (en f) y la prueba del signo."""
    fa, fb = por(filas, a), por(filas, b)
    g = sum(1 for k in fa if fa[k]["f"] < fb[k]["f"] - 1e-9)
    p = sum(1 for k in fa if fa[k]["f"] > fb[k]["f"] + 1e-9)
    return f"| {a} contra {b} | {g} | {p} | {len(fa) - g - p} | {p_texto(prueba_signo(g, p))} |"


def tabla_modelo(filas: list) -> list:
    L = ["## Modelo (Más parecido + búsqueda local, 70 instancias)", ""]
    m1 = [r for r in filas if r["exp"] == "M1"]
    L += ["### M1 · ¿Qué regla de temperatura? (θ = 0, λ = 1)", "",
          "| regla | camiones de más (promedio) | camiones con carga insegura |", "|---|---|---|"]
    for etiqueta, _ in M1:
        r = [x for x in m1 if x["etiqueta"] == etiqueta]
        L.append(f"| {etiqueta} | {n(st.mean(x['extra'] for x in r))} | "
                 f"{n(100 * sum(x['inseguros'] for x in r) / sum(x['K'] for x in r), 1)} % |")
    m2 = [r for r in filas if r["exp"] == "M2"]
    L += ["", "### M2 · ¿Qué similitud mínima θ? (ventanas, λ = 1)", "",
          "| θ | camiones de más (promedio) | camiones con limpieza que también llevan comida | similitud media |",
          "|---|---|---|---|"]
    for th in M2:
        r = [x for x in m2 if x["etiqueta"] == f"{th:g}"]
        L.append(f"| {n(th, 1)} | {n(st.mean(x['extra'] for x in r))} | "
                 f"{n(100 * sum(x['limpieza_comida'] for x in r) / sum(x['limpieza'] for x in r), 1)} % | "
                 f"{n(st.mean(x['sim'] for x in r), 3)} |")
    m3 = [r for r in filas if r["exp"] == "M3"]
    L += ["", "### M3 · ¿Cuánto pesa la similitud? (ventanas, θ = 0,2)", "",
          "| λ | camiones de más (promedio) | similitud media |", "|---|---|---|"]
    for la in M3:
        r = [x for x in m3 if x["etiqueta"] == f"{la:g}"]
        L.append(f"| {n(la, 1)} | {n(st.mean(x['extra'] for x in r))} | {n(st.mean(x['sim'] for x in r), 3)} |")
    return L


def tabla_a1(filas: list) -> list:
    L = ["## A1 · ¿Qué combinación conviene? (70 instancias, modelo elegido; ILS 5 s)", "",
         "| combinación | f (promedio) | camiones de más | similitud | tiempo (s) | mejor f en |",
         "|---|---|---|---|---|---|"]
    mejor = {}
    for r in filas:
        mejor[r["nombre"]] = min(mejor.get(r["nombre"], math.inf), r["f"])
    for etiqueta, *_ in A1:
        r = [x for x in filas if x["etiqueta"] == etiqueta]
        gana = sum(1 for x in r if x["f"] <= mejor[x["nombre"]] + 1e-9)
        L.append(f"| {etiqueta} | {n(st.mean(x['f'] for x in r))} | {n(st.mean(x['extra'] for x in r))} | "
                 f"{n(st.mean(x['sim'] for x in r), 3)} | {n(st.mean(x['segundos'] for x in r))} | "
                 f"{gana} de {len(r)} |")
    L += ["", "**Duelos instancia por instancia (en f):**", "",
          "| duelo | gana | pierde | empata | prueba del signo (p) |", "|---|---|---|---|---|",
          duelo(filas, "Más parecido", "BFD"),
          duelo(filas, "Más parecido + swap", "Más parecido + relocate"),
          duelo(filas, "BFD + swap", "BFD + relocate"),
          duelo(filas, "Más parecido + relocate + swap", "BFD + relocate + swap"),
          duelo(filas, "ILS desde Más parecido, con relocate + swap", "Más parecido + relocate + swap"),
          duelo(filas, "ILS desde Más parecido, con relocate + swap", "ILS desde BFD, con relocate + swap")]
    return L


def f_a_los(historia: str, t: float):
    """Mejor f encontrada hasta el segundo t (None si todavía no había solución)."""
    h = [b for a, b in json.loads(historia) if a <= t]
    return h[-1] if h else None


def tabla_a2(filas: list) -> list:
    L = ["## A2 · Ajuste del ILS: ¿cuánto romper y cuánto tiempo? (70 instancias)", "",
         "f promedio a los 1, 5 y 30 s (más bajo es mejor). Cada vuelta vacía el camión menos "
         "cargado y, además, esa fracción de los camiones.", "",
         "| fracción que se vacía | " + " | ".join(f"f a los {t:g} s" for t in A2_TIEMPOS) + " |",
         "|---|" + "---|" * len(A2_TIEMPOS)]
    sin = 0
    for fr in A2_FRACCIONES:
        r = [x for x in filas if x["etiqueta"] == f"{fr:g}"]
        cel = []
        for t in A2_TIEMPOS:
            v = [f_a_los(x["historia"], t) for x in r]
            sin += sum(1 for x in v if x is None)
            v = [x if x is not None else f_a_los(y["historia"], math.inf) for x, y in zip(v, r)]
            cel.append(n(st.mean(v)))
        L.append(f"| {fr:g} | " + " | ".join(cel) + " |")
    if sin:
        L += ["", f"({sin} casos sin solución todavía a ese tiempo: se usó la primera que encontró.)"]
    L += ["", "**Duelos a los 30 s (en f):**", "", "| duelo | gana | pierde | empata | prueba del signo (p) |",
          "|---|---|---|---|---|"]
    final = [dict(x, f=f_a_los(x["historia"], math.inf)) for x in filas]
    for otra in ("0.5", "0.75"):
        a, b = por(final, "0.25"), por(final, otra)
        g = sum(1 for k in a if a[k]["f"] < b[k]["f"] - 1e-9)
        p = sum(1 for k in a if a[k]["f"] > b[k]["f"] + 1e-9)
        L.append(f"| un cuarto (0,25, elegida) contra {otra.replace('.', ',')} | {g} | {p} | {len(a) - g - p} | "
                 f"{p_texto(prueba_signo(g, p))} |")
    return L


A3_GRUPOS = [("el óptimo exacto", 0.0, 1e-6), ("a menos de medio camión", 1e-6, 0.5),
             ("a medio camión o más", 0.5, math.inf)]   # distancia en f (f se mide en camiones)


def tabla_a3(filas: list) -> list:
    L = [f"## A3 · ¿Qué tan cerca del óptimo? ({A3_INSTANCIAS} instancias de 10 a 14 productos, "
         "óptimo exacto por fuerza bruta)", "",
         "| método | " + " | ".join(g for g, *_ in A3_GRUPOS) + " | distancia promedio en f |",
         "|---|" + "---|" * (len(A3_GRUPOS) + 1)]
    for m in A3_METODOS:
        d = [float(x["dif"]) for x in filas if x["metodo"] == m]
        cel = [f"{n(100 * sum(1 for v in d if a <= v < b) / len(d), 0)} %" for _, a, b in A3_GRUPOS]
        L.append(f"| {m} | " + " | ".join(cel) + f" | {n(st.mean(d))} |")
    por_inst = {}
    for x in filas:
        por_inst.setdefault(x["semilla"], {})[x["metodo"]] = float(x["f"])
    g = sum(1 for v in por_inst.values() if v[A3_METODOS[3]] < v[A3_METODOS[2]] - 1e-9)
    p = sum(1 for v in por_inst.values() if v[A3_METODOS[3]] > v[A3_METODOS[2]] + 1e-9)
    L += ["", f"ILS contra búsqueda local: gana {g}, pierde {p}, empata {len(por_inst) - g - p} "
              f"(prueba del signo p = {p_texto(prueba_signo(g, p))})."]
    return L


def a4_resumen(filas: list) -> list:
    """[(etiqueta, segundos, f promedio)] de cada etapa, en orden."""
    etapas = [("Más parecido", st.mean(float(x["s_constructiva"]) for x in filas),
               st.mean(float(x["f_constructiva"]) for x in filas)),
              ("+ búsqueda local", st.mean(float(x["s_bl"]) for x in filas),
               st.mean(float(x["f_bl"]) for x in filas))]
    for t in A4_TIEMPOS:
        etapas.append((f"ILS a los {t:g} s", t, st.mean(f_a_los(x["historia"], t) for x in filas)))
    return etapas


def tabla_a4(filas: list) -> list:
    L = [f"## A4 · ¿Y un día grande? ({len(filas)} instancias Falkenauer U1000: 1000 productos, "
         f"óptimo de {min(int(x['opt']) for x in filas)} a {max(int(x['opt']) for x in filas)} camiones)", "",
         "| etapa | tiempo desde el inicio (s) | f promedio |", "|---|---|---|"]
    for e, s, f in a4_resumen(filas):
        L.append(f"| {e} | {n(s, 1)} | {n(f, 1)} |")
    L += ["", f"Camiones de más: búsqueda local {n(st.mean(float(x['extra_bl']) for x in filas), 1)}, "
              f"ILS a los 3 min {n(st.mean(float(x['extra_ils']) for x in filas), 1)}."]
    return L


def graficos_a3_a4(a3: list, a4: list) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tinta, gris = "#14203A", "#7A849A"
    # A3: de cada 100 instancias, en cuántas cada método llega al óptimo (barras apiladas al 100 %)
    colores = ["#1E3A6B", "#7C9CCF", "#D8E0EE"]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    for fila, m in enumerate(A3_METODOS[::-1]):
        d = [float(x["dif"]) for x in a3 if x["metodo"] == m]
        izq = 0.0
        for (g, a, b), c in zip(A3_GRUPOS, colores):
            v = 100 * sum(1 for x in d if a <= x < b) / len(d)
            ax.barh(fila, v, left=izq, color=c, height=0.62, edgecolor="white", linewidth=2,
                    label=g if fila == 0 else None)
            oscuro = c == colores[0]
            if v >= 7 or (oscuro and v >= 3):
                ax.text(izq + v / 2, fila, f"{v:.0f}%" if v < 7 else f"{v:.0f} %", ha="center",
                        va="center", fontsize=9 if v >= 7 else 7.5, color="white" if oscuro else tinta,
                        fontweight="bold" if oscuro else None)
            elif v > 0 and izq + v >= 99.9:       # el último segmento, si es angosto: afuera
                ax.text(101, fila, f"{v:.0f} %", ha="left", va="center", fontsize=8.5, color=gris)
            izq += v
    ax.set_yticks(range(len(A3_METODOS)))
    ax.set_yticklabels(A3_METODOS[::-1], fontsize=9.5, color=tinta)
    ax.set_xlim(0, 107)
    ax.set_xticks([])
    ax.spines[["top", "right", "bottom", "left"]].set_visible(False)
    ax.tick_params(left=False)
    ax.legend(ncol=3, frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.42, 1.0),
              handlelength=1.2, columnspacing=1.2)
    fig.tight_layout()
    fig.savefig(os.path.join(SALIDA, "a3.png"), dpi=200)
    plt.close(fig)

    # A4: cascada. La barra sube o baja hasta el f de esa etapa, y ese f es el número que se
    # muestra; abajo, el tiempo acumulado.
    etapas = a4_resumen(a4)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    previo = 0.0
    for k, (e, s, f) in enumerate(etapas):
        abajo, alto = min(previo, f), abs(f - previo)
        color = "#9AA5B8" if k == 0 else "#3B6FB6" if k == 1 else "#E8590C"
        ax.bar(k, alto, bottom=abajo, color=color, width=0.62)
        ax.text(k, abajo - 4 if k else f + 3, n(f, 1).replace("-", "−"), ha="center",
                va="top" if k else "bottom", fontsize=9.5, color=tinta, fontweight="bold")
        if k < len(etapas) - 1:
            ax.plot([k + 0.31, k + 0.69], [f, f], color=gris, lw=0.8, ls=":")
        previo = f
    ax.axhline(0, color=gris, lw=0.8)
    nombres = ["Más parecido\n" + f"a los {n(etapas[0][1], 1)} s",
               "+ búsqueda local\n" + f"a los {n(etapas[1][1], 1)} s",
               "ILS\na los 10 s", "ILS\na 1 min", "ILS\na 3 min"]
    ax.set_xticks(range(len(etapas)))
    ax.set_xticklabels(nombres, fontsize=8.5, color=tinta)
    ax.set_ylabel("f promedio (más bajo es mejor)", fontsize=9, color=tinta)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace("-", "−")))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=8.5, colors=gris)
    ax.set_ylim(min(e[2] for e in etapas) - 22, etapas[0][2] + 15)
    ax.set_xlim(-0.5, len(etapas) - 0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(SALIDA, "a4.png"), dpi=200)
    plt.close(fig)


def graficos(a1: list, a2: list) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker

    # A1: f promedio de cada combinación (barras horizontales)
    etiquetas = [e for e, *_ in A1]
    valores = [st.mean(x["f"] for x in a1 if x["etiqueta"] == e) for e in etiquetas]
    colores = ["#9aa5b8" if "ILS" not in e and "+" not in e else
               "#3b6fb6" if "ILS" not in e else "#e8590c" for e in etiquetas]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    y = range(len(etiquetas))[::-1]
    ax.barh(list(y), valores, color=colores)
    ax.set_yticks(list(y))
    ax.set_yticklabels(etiquetas, fontsize=9)
    for yy, v in zip(y, valores):
        ax.text(v + 0.3, yy, n(v, 1), va="center", fontsize=8)
    ax.set_xlabel("f promedio en 70 instancias (más bajo es mejor)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SALIDA, "a1.png"), dpi=160)
    plt.close(fig)

    # A2: f promedio contra tiempo, una línea por fracción
    ts = [0.5, 1, 2, 3, 5, 8, 12, 20, 30]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    nombres = {0.25: "vaciar un cuarto (elegida)", 0.5: "vaciar la mitad", 0.75: "vaciar tres cuartos"}
    for fr, color in zip(A2_FRACCIONES, ("#e8590c", "#3b6fb6", "#9aa5b8")):
        r = [x for x in a2 if x["etiqueta"] == f"{fr:g}"]
        ys = []
        for t in ts:
            v = [f_a_los(x["historia"], t) for x in r]
            v = [a if a is not None else f_a_los(x["historia"], math.inf) for a, x in zip(v, r)]
            ys.append(st.mean(v))
        ax.plot(ts, ys, marker="o", color=color, label=nombres[fr])
    ax.set_xscale("log")
    ax.set_xticks(ts)
    ax.set_xticklabels([f"{t:g}".replace(".", ",") for t in ts])
    ax.axhline(st.mean(x["f"] for x in a1 if x["etiqueta"] == "Más parecido + relocate + swap"),
               color="#c63d50", ls="--", lw=1.2, label="búsqueda local sola (sin ILS)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    ax.set_xlabel("segundos")
    ax.set_ylabel("f promedio (más bajo es mejor)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SALIDA, "a2.png"), dpi=160)
    plt.close(fig)


def informe() -> None:
    L = ["# Resultados de los experimentos", "",
         "Generado por `python3 scripts/experimentos.py informe`. Diseño y lectura en "
         "el informe (secciones 3 y 7).", "",
         "- **camiones de más** = camiones usados − óptimo del bin packing sin reglas (BPPLIB).",
         "- **similitud media** = promedio de s_ij entre los productos que viajan juntos (0 a 1).",
         "- **f** = α·K − β·S con el modelo elegido; se mide en camiones (bajar f en 1 = ahorrar un camión).",
         "- **prueba del signo**: probabilidad de un resultado así de desparejo si los dos métodos "
         "fueran iguales (p < 0,05: no es casualidad).", ""]
    L += tabla_modelo(leer("modelo")) + [""]
    a1, a2 = leer("a1"), leer("a2")
    L += tabla_a1(a1) + ["", "![A1](a1.png)", ""] + tabla_a2(a2) + ["", "![A2](a2.png)", ""]
    a3, a4 = (list(csv.DictReader(open(os.path.join(SALIDA, x + ".csv")))) for x in ("a3", "a4"))
    L += tabla_a3(a3) + ["", "![A3](a3.png)", ""] + tabla_a4(a4) + ["", "![A4](a4.png)", ""]
    open(os.path.join(SALIDA, "resumen.md"), "w", encoding="utf-8").write("\n".join(L))
    graficos(a1, a2)
    graficos_a3_a4(a3, a4)
    print("\n".join(L))


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que in ("modelo", "todo"):
        correr_todas(tareas_modelo(), "modelo")
    if que in ("a1", "todo"):
        correr_todas(tareas_a1(), "a1")
    if que in ("a2", "todo"):
        correr_todas(tareas_a2(), "a2")
    if que in ("a3", "todo"):
        correr_lista(correr_a3, list(range(A3_INSTANCIAS)), "a3")
    if que in ("a4", "todo"):
        correr_lista(correr_a4, A4_INSTANCIAS, "a4")
    if que in ("informe", "todo"):
        informe()
