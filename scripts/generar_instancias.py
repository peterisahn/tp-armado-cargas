"""Genera las instancias de experimentación a partir de BPPLIB.

Uso (desde la raíz del repo):
    python3 scripts/generar_instancias.py

Escribe en instancias/experimentos/ las 70 instancias de los experimentos:
  - <nombre>.txt         instancia en el formato del enunciado
  - <nombre>.familias    familia de cada producto (una por línea), para trazabilidad
  - indice.csv           nombre, colección, n, C, óptimo del BPP clásico (BPPLIB), semilla

El óptimo de BPPLIB sale de externos/BPPLIB-main/Instances/Solutions/Solutions.xlsx (se
lee con openpyxl, sólo en este script). Es la mínima cantidad de vehículos sin
temperatura ni similitud: ninguna solución de nuestro problema puede usar menos.
"""

from __future__ import annotations

import csv
import os
import sys
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from tp2.generador import formatear_instancia, generar, leer_bpplib  # noqa: E402

BPP = os.path.join(RAIZ, "externos", "BPPLIB-main", "Instances", "BPP")
XLSX = os.path.join(RAIZ, "externos", "BPPLIB-main", "Instances", "Solutions", "Solutions.xlsx")
SALIDA = os.path.join(RAIZ, "instancias", "experimentos")

# 70 instancias de cuatro colecciones con distinta cantidad de productos por camión:
#   Schwerin (n = 100, productos chicos: ~5,5 por camión), Falkenauer U120 y U250
#   (n = 120 y 250, productos grandes: ~2,5 por camión) y Random de n = 200 (dos tipos).
_SCH = "4_Schwerin/Schwerin"
_FAL = "1_Falkenauer/Falkenauer/Falkenauer U"
_RND = "6_Randomly_Generated/Randomly_Generated"
SELECCION = (
    [("Schwerin", f"{_SCH}/Schwerin_1/Schwerin1_BPP{k}.txt") for k in range(1, 21)]
    + [("Schwerin", f"{_SCH}/Schwerin_2/Schwerin2_BPP{k}.txt") for k in range(1, 6)]
    + [("Falkenauer_U120", f"{_FAL}/Falkenauer_u120_{k:02d}.txt") for k in range(20)]
    + [("Falkenauer_U250", f"{_FAL}/Falkenauer_u250_{k:02d}.txt") for k in range(5)]
    + [("Random_200_1000", f"{_RND}/BPP_200_1000_0.1_0.7_{k}.txt") for k in range(10)]
    + [("Random_200_150", f"{_RND}/BPP_200_150_0.2_0.8_{k}.txt") for k in range(10)]
)


def optimos_bpplib() -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    opt = {}
    for ws in wb.worksheets:
        for fila in ws.iter_rows(min_row=2, values_only=True):
            if fila and fila[0] and fila[3] == "Solved":
                opt[str(fila[0])] = int(fila[2])
    return opt


def main() -> None:
    os.makedirs(SALIDA, exist_ok=True)
    opt = optimos_bpplib()
    filas = []
    for coleccion, rel in SELECCION:
        archivo = os.path.basename(rel)
        nombre = os.path.splitext(archivo)[0]
        capacidad, pesos = leer_bpplib(os.path.join(BPP, rel))
        semilla = zlib.crc32(nombre.encode())
        familias, temps, s = generar(pesos, capacidad, semilla)
        with open(os.path.join(SALIDA, nombre + ".txt"), "w") as f:
            f.write(formatear_instancia(capacidad, pesos, temps, s))
        with open(os.path.join(SALIDA, nombre + ".familias"), "w") as f:
            f.write("\n".join(familias) + "\n")
        filas.append([nombre, coleccion, len(pesos), f"{capacidad:g}", opt[archivo], semilla])
        print(f"{nombre}: n={len(pesos)} C={capacidad:g} óptimo BPP={opt[archivo]}")
    with open(os.path.join(SALIDA, "indice.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nombre", "coleccion", "n", "C", "opt_bpp", "semilla"])
        w.writerows(filas)


if __name__ == "__main__":
    main()
