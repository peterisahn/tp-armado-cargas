# TD V - Diseño de Algoritmos: TP2 Bin Packing

Repositorio con el modelado, la implementación, la experimentación y el análisis comparativo de algoritmos para resolver un problema de armado de cargas para entregas de supermercado, desarrollado para la materia Tecnología Digital V - Diseño de Algoritmos de la Universidad Torcuato Di Tella (2026).

## Descripción del problema

El proyecto aborda una extensión del problema clásico de Bin Packing, incorporando restricciones de compatibilidad térmica y similitud entre productos.

El objetivo consiste en minimizar la cantidad de vehículos utilizados para realizar las entregas, respetando sus capacidades y las condiciones de conservación de los productos, y favoreciendo la agrupación de productos similares.

Dada la complejidad computacional del problema, se desarrollaron diferentes estrategias heurísticas para obtener soluciones de buena calidad en tiempos razonables.

## Contenido

- **Modelado del problema**:
  - Función objetivo que combina la cantidad de vehículos utilizados y la similitud entre productos.
  - Restricciones de capacidad, compatibilidad térmica y similitud mínima.
  - Normalización de los parámetros de la función objetivo y ajuste mediante experimentación.

- **Heurísticas constructivas**:
  - Best Fit Decreasing (BFD): asignación de productos priorizando el aprovechamiento de la capacidad de los vehículos.
  - Más parecido: asignación de productos priorizando la similitud con los productos ya cargados.

- **Búsqueda local**:
  - Relocate: reasignación de un producto a otro vehículo.
  - Swap: intercambio de productos entre vehículos.
  - Combinación de ambos operadores para mejorar las soluciones iniciales.

- **Metaheurística**:
  - Iterated Local Search (ILS): estrategia de perturbación, reconstrucción y búsqueda local para escapar de óptimos locales y obtener mejores soluciones.

- **Generación de instancias**:
  - Utilización de instancias de referencia de BPPLIB.
  - Generación sintética de temperaturas y similitudes a partir de familias de productos de supermercado.

- **Experimentación**:
  - Evaluación y ajuste de los parámetros del modelo.
  - Comparación de 14 combinaciones de algoritmos sobre 70 instancias.
  - Ajuste de los parámetros de perturbación y tiempo de ejecución del ILS.
  - Comparación con soluciones óptimas obtenidas mediante fuerza bruta.
  - Evaluación del rendimiento sobre instancias de hasta 1000 productos.

- **Testing y validación**:
  - Tests automáticos para verificar el funcionamiento de los algoritmos.
  - Validación de la factibilidad de las soluciones y evaluación de sus métricas.

## Desafíos abordados

- Equilibrar la minimización de vehículos con la similitud entre los productos transportados.
- Modelar las restricciones de temperatura mediante ventanas de compatibilidad térmica.
- Generar instancias representativas ante la ausencia de datos reales de temperatura y similitud.
- Mejorar la eficiencia de los algoritmos mediante el precálculo de compatibilidades y la evaluación incremental de la función objetivo.
- Evitar el estancamiento en óptimos locales y mantener tiempos de ejecución razonables para instancias de gran tamaño.

## Principales resultados

- El modelo seleccionado permitió evitar cargas térmicamente incompatibles y reducir considerablemente las combinaciones de productos de limpieza y alimentos.
- La búsqueda local mejoró significativamente las soluciones obtenidas por las heurísticas constructivas.
- El ILS mejoró las soluciones de búsqueda local en las 70 instancias evaluadas.
- En instancias pequeñas, el ILS alcanzó el óptimo exacto en el 73 % de los casos.
- En instancias de 1000 productos, la búsqueda local obtuvo buenas soluciones en menos de 6 segundos en el entorno experimental utilizado.

## Lenguajes y tecnologías

- Python
- Matplotlib
- OpenPyXL
- Unittest
- BPPLIB (biblioteca de instancias de referencia)

## Requisitos

- Python 3.9 o superior.
- El programa principal utiliza únicamente la biblioteca estándar.
- Para la experimentación y generación de instancias:

```bash
pip install matplotlib openpyxl
```

## Cómo ejecutar

Desde la carpeta raíz del repositorio:

```bash
python3 main.py <archivo_instancia> <archivo_salida> [opciones]
```

Ejemplo con la instancia del enunciado:

```bash
python3 main.py instancias/ejemplo_enunciado.txt salida.txt --alpha 1 --beta 1
```

El programa guarda la solución en el archivo de salida y muestra la cantidad de
camiones utilizados, la cota inferior por peso, la similitud, el valor de la
función objetivo, la factibilidad y el tiempo de ejecución.

### Parámetros

| parámetro | obligatorio | descripción | default |
|---|---|---|---|
| `archivo_instancia` | sí | Archivo de entrada | — |
| `archivo_salida` | sí | Archivo de salida | — |
| `--algoritmo NOMBRE` | no | `bfd`, `parecido`, `bl` (búsqueda local) o `ils` (Iterated Local Search) | `ils` |
| `--constructiva C` | no | Constructiva utilizada en BL e ILS: `bfd` o `parecido` | `parecido` |
| `--operadores OPS` | no | Operadores de búsqueda local: `relocate`, `swap` o `relocate,swap` | `relocate,swap` |
| `--fraccion F` | no | Fracción de camiones vaciados aleatoriamente en ILS, además del menos cargado | `0.25` |
| `--tiempo S` | no | Límite de tiempo en segundos para BL o ILS | `10` |
| `--semilla N` | no | Semilla aleatoria | `0` |
| `--temperatura MODO` | no | Modelo térmico: `ventanas`, `zonas`, `umbral` o `ninguno` | `ventanas` |
| `--delta D` | no | Rango máximo de temperatura en el modo `umbral` | `20` |
| `--theta T` | no | Similitud mínima entre productos de un mismo vehículo | `0.2` |
| `--lam L` | no | Parámetro de normalización del peso de la similitud | `1` |
| `--alpha A`, `--beta B` | no | Pesos explícitos de la función objetivo | — |
| `--evaluar` | no | Valida y evalúa una solución existente sin resolver la instancia | — |

Función objetivo: `α·K − β·Σ_k Σ_{i<j ∈ B_k} s_ij`.

Los valores por defecto corresponden al modelo y los parámetros seleccionados
mediante la experimentación, cuya justificación se encuentra en el informe.

## Experimentos

```bash
python3 scripts/experimentos.py modelo    # Ajuste de temperatura, θ y λ
python3 scripts/experimentos.py a1        # Comparación de algoritmos
python3 scripts/experimentos.py a2        # Ajuste de parámetros del ILS
python3 scripts/experimentos.py a3        # Comparación con el óptimo exacto
python3 scripts/experimentos.py a4        # Instancias de 1000 productos
python3 scripts/experimentos.py informe   # Generación de tablas y gráficos
python3 scripts/experimentos.py todo      # Ejecución completa (≈ 25 min)
```

Los resultados se guardan en `resultados/experimentos/` en formato CSV,
junto con las tablas y los gráficos generados.

El comando `informe` requiere haber ejecutado previamente los experimentos
A1–A4. El tiempo de ejecución depende del equipo utilizado.

### Instalación de BPPLIB

Las 70 instancias utilizadas en los experimentos M1–M3, A1 y A2 ya están
incluidas en el repositorio. A3 genera sus propias instancias.

Para ejecutar A4 o regenerar las instancias desde BPPLIB:

1. Descargar [BPPLIB](https://github.com/mdelorme2/BPPLIB)
   (Code → Download ZIP).
2. Descomprimir el repositorio en `externos/BPPLIB-main/`.
3. Crear la carpeta `Instances/BPP/` dentro de BPPLIB.
4. Descomprimir `Instances/Benchmarks/1_Falkenauer.rar` dentro de
   `Instances/BPP/`.

Para A4, la estructura necesaria es:

```text
externos/
└── BPPLIB-main/
    └── Instances/
        ├── BPP/
        │   └── 1_Falkenauer/
        │       └── Falkenauer/
        │           └── Falkenauer U/
        └── Solutions/
```

Para regenerar las 70 instancias originales:

```bash
python3 scripts/generar_instancias.py
```

La regeneración requiere también las instancias correspondientes de Schwerin.

## Formatos

**Entrada:** primera línea con la cantidad de productos `n` y la capacidad `C`;
luego `n` líneas con el peso y la temperatura de cada producto, seguidas
de una matriz de similitudes `n × n`, simétrica y con diagonal igual a 1.

**Salida:** una línea por vehículo utilizado, con los índices de los productos
(desde 0) separados por espacios.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

## Estructura

```text
main.py                 Programa principal
tp2/instancia.py        Lectura y escritura de instancias y soluciones
tp2/modelo.py           Restricciones y función objetivo
tp2/constructivas.py    Best Fit Decreasing y Más parecido
tp2/busqueda_local.py   Operadores Relocate y Swap
tp2/metaheuristica.py   Iterated Local Search
tp2/solucion.py         Validación de soluciones
tp2/metricas.py         Métricas de evaluación
tp2/generador.py        Generación sintética de instancias
scripts/                Generación de instancias y experimentación
tests/                  Tests automáticos
instancias/             Instancias de entrada
resultados/             Resultados, tablas y gráficos
externos/               Biblioteca BPPLIB (no incluida)
```
