# TP2 — Armado de cargas para entregas de supermercado

TD5 Diseño de Algoritmos (UTDT), segundo semestre 2026.

## Requisitos

- **Python 3.9 o superior.** No hace falta instalar nada: sólo se usa la biblioteca
  estándar.

## Cómo ejecutar

Desde la carpeta raíz del repo:

```bash
python3 main.py <archivo_instancia> <archivo_salida> [opciones]
```

Ejemplo con la instancia del enunciado:

```bash
python3 main.py instancias/ejemplo_enunciado.txt salida.txt --alpha 1 --beta 1
```

El programa escribe la solución en `salida.txt` y muestra por pantalla la cantidad de
camiones (y el mínimo posible por peso), la similitud, el valor de la función objetivo, si
la solución respeta el modelo y el tiempo.

### Parámetros

| parámetro | obligatorio | descripción | default |
|---|---|---|---|
| `archivo_instancia` | sí | instancia en el formato del enunciado | — |
| `archivo_salida` | sí | dónde escribir la solución | — |
| `--algoritmo NOMBRE` | no | `ils` (metaheurística Iterated Local Search), `bfd` (constructiva 1 sola: Best Fit Decreasing), `parecido` (constructiva 2 sola: Más parecido) o `bl` (constructiva + búsqueda local hasta un óptimo local) | `ils` |
| `--constructiva C` | no | sólo `bl` e `ils`: con qué constructiva se arranca (y, en `ils`, se rearma): `bfd` o `parecido` | `parecido` |
| `--operadores OPS` | no | sólo `bl` e `ils`: operadores de búsqueda local, separados por coma: `relocate`, `swap` o `relocate,swap` | `relocate,swap` |
| `--fraccion F` | no | sólo `ils`: en cada vuelta se vacía el camión menos cargado y, además, esta fracción de los camiones, al azar (0,25 = un cuarto; elegido en el experimento A2) | `0.25` |
| `--tiempo S` | no | segundos máximos de ejecución (`ils`; en `bl`, tope para la búsqueda local) | `10` |
| `--semilla N` | no | semilla aleatoria (resultados reproducibles) | `0` |
| `--temperatura MODO` | no | `ventanas` (inocuidad, recomendado), `zonas`, `umbral` o `ninguno` | `ventanas` |
| `--delta D` | no | rango máximo de temperatura por vehículo, sólo con `--temperatura umbral` | `20` |
| `--theta T` | no | similitud mínima entre dos productos de un mismo vehículo (0 = sin restricción) | `0.2` |
| `--lam L` | no | peso normalizado de la similitud: α = 1 y β = L / (pares de un camión lleno) | `1` |
| `--alpha A`, `--beta B` | no | fijan α y β a mano (reemplazan la normalización) | — |
| `--evaluar` | no | no resuelve: lee la solución que ya está en `archivo_salida`, la valida y muestra sus métricas | — |

Función objetivo (enunciado, pág. 2): `α·K − β·Σ_k Σ_{i<j ∈ B_k} s_ij`. Los valores por
defecto son el modelo elegido en el ítem 1; la justificación está en el informe (sección 3).

### Experimentos

El diseño y la lectura de cada experimento están en el informe (secciones 3 y 7).

```bash
python3 scripts/experimentos.py modelo     # M1–M3: temperatura, θ y λ (sección 3 del informe)
python3 scripts/experimentos.py a1         # A1: las 14 combinaciones de algoritmos (7.1)
python3 scripts/experimentos.py a2         # A2: cuánto rompe el ILS y cuánto tiempo (7.2)
python3 scripts/experimentos.py a3         # A3: distancia al óptimo exacto (7.3)
python3 scripts/experimentos.py a4         # A4: 1000 productos (7.4); necesita externos/BPPLIB
python3 scripts/experimentos.py informe    # tablas (resumen.md) y gráficos; necesita las corridas de A1 a A4
python3 scripts/experimentos.py todo       # todo lo anterior (≈ 25 min; necesita externos/BPPLIB)
python3 scripts/generar_instancias.py      # vuelve a generar las 70 instancias desde BPPLIB (ya están en instancias/)
```

`scripts/experimentos.py` usa `matplotlib` para los gráficos y `scripts/generar_instancias.py`
usa `openpyxl` para leer los óptimos de BPPLIB. El programa principal no los necesita.

Los scripts que leen BPPLIB necesitan la biblioteca en `externos/`, que **no está en el
repo** por tamaño (74 MB): descargar https://github.com/mdelorme2/BPPLIB (Code → Download
ZIP) y descomprimirla como `externos/BPPLIB-main/`. Las
instancias ya generadas están en `instancias/`, así que el programa, los tests y los
experimentos M1–M3 y A1–A3 corren sin descargar nada. Los resultados se guardan en
`resultados/experimentos/` (CSV, tablas y gráficos).

## Formatos

**Entrada** (enunciado, pág. 2): primera línea `n C`; después `n` líneas con el peso y la
temperatura de cada producto; después la matriz de similitudes `n × n` (simétrica, con 1
en la diagonal). Los números pueden ser reales. Si el archivo no cumple el formato, el
programa termina con un mensaje que explica qué está mal.

**Salida** (enunciado, pág. 3): una línea por vehículo usado, con los índices (desde 0) de
sus productos separados por un espacio.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

## Estructura

```
main.py                 programa principal (parámetros, ejecución, medidas)
tp2/instancia.py        lectura y validación de instancias; escritura y lectura de soluciones
tp2/modelo.py           el modelo: qué puede ir junto (ventanas, θ), carga, similitud y f
tp2/constructivas.py    las dos constructivas: Best Fit Decreasing y Más parecido
tp2/busqueda_local.py   búsqueda local: relocate y swap
tp2/metaheuristica.py   Iterated Local Search (romper y rearmar)
tp2/solucion.py         validación de soluciones (cada producto una vez, capacidad)
tp2/metricas.py         medidas para comparar soluciones (seguridad, similitud, etc.)
tp2/generador.py        generación de temperaturas y similitudes por familias de productos
scripts/                generación de instancias y experimentos
tests/                  tests automáticos
instancias/             ejemplo del enunciado y las 70 instancias de los experimentos (experimentos/)
resultados/             se crea al correr los experimentos (CSV, tablas, gráficos)
externos/BPPLIB-main/   biblioteca BPPLIB descomprimida (no incluida; ver Experimentos)
```

