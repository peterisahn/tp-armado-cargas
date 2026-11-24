"""Tests de las heurísticas constructivas y la búsqueda local.

Correr desde la raíz del repo:
    python3 -m unittest discover -s tests -t .
"""

import random
import unittest

from tests.test_modelo import instancia_azar, particiones
from tp2.busqueda_local import busqueda_local
from tp2.constructivas import construir
from tp2.instancia import parsear_instancia
from tp2.modelo import Modelo
from tp2.solucion import validar

EJEMPLO = ("4 10\n4 4\n5 4\n3 20\n6 -18\n"
           "1 .9 .1 .3\n.9 1 .2 .3\n.1 .2 1 .1\n.3 .3 .1 1\n")
MODELOS = (Modelo("ventanas", theta=0.2, lam=1), Modelo("zonas", theta=0),
           Modelo("ninguno", theta=0.3, lam=2))


def optimo_K(ctx):
    """Mínima cantidad de camiones válida, por fuerza bruta (sólo para n chico)."""
    return min(len(p) for p in particiones(list(range(ctx.inst.n)))
               if all(ctx.camion_valido(c) for c in p))


class TestConstructivas(unittest.TestCase):
    def test_validas_y_nunca_menos_camiones_que_el_optimo(self):
        rng = random.Random(3)
        for _ in range(40):
            inst = instancia_azar(rng, rng.randint(2, 7))
            for modelo in MODELOS:
                ctx = modelo.preparar(inst)
                opt = optimo_K(ctx)
                for criterio in ("bfd", "parecido"):
                    sol = construir(ctx, criterio)
                    validar(inst, sol)
                    self.assertTrue(all(ctx.camion_valido(c) for c in sol))
                    self.assertGreaterEqual(len(sol), opt)

    def test_ejemplo_del_enunciado(self):
        # Orden por peso: 3 (congelado) abre un camión; 1 no puede ir con él y abre otro;
        # 0 va con 1 (entra y s = 0,9); 2 no entra con 0 y 1 (12 > 10) y abre el tercero.
        ctx = Modelo().preparar(parsear_instancia(EJEMPLO))
        for criterio in ("bfd", "parecido"):
            sol = sorted(sorted(c) for c in construir(ctx, criterio))
            self.assertEqual(sol, [[0, 1], [2], [3]])


class TestBusquedaLocal(unittest.TestCase):
    def test_valida_y_nunca_empeora(self):
        rng = random.Random(5)
        for _ in range(40):
            inst = instancia_azar(rng, rng.randint(3, 10))
            for modelo in MODELOS:
                ctx = modelo.preparar(inst)
                for criterio in ("bfd", "parecido"):
                    inicial = construir(ctx, criterio)
                    for ops in (dict(), dict(swap=False), dict(relocate=False)):
                        sol = busqueda_local(ctx, inicial, **ops)
                        validar(inst, sol)
                        self.assertTrue(all(ctx.camion_valido(c) for c in sol))
                        self.assertLessEqual(ctx.valor(sol), ctx.valor(inicial) + 1e-9)

    def test_relocate_vacia_un_camion(self):
        # Tres productos iguales y compatibles, uno por camión: relocate los junta en uno.
        inst = parsear_instancia("3 10\n1 4\n1 4\n1 4\n1 .9 .9\n.9 1 .9\n.9 .9 1\n")
        ctx = Modelo().preparar(inst)
        sol = busqueda_local(ctx, [[0], [1], [2]], swap=False)
        self.assertEqual(len(sol), 1)

    def test_swap_mejora_lo_que_relocate_no_puede(self):
        # Dos camiones llenos (C = 2) con los productos cruzados: ningún relocate entra,
        # sólo un swap junta a los parecidos (0 con 1, 2 con 3).
        inst = parsear_instancia("4 2\n1 4\n1 4\n1 4\n1 4\n"
                                 "1 .9 .3 .3\n.9 1 .3 .3\n.3 .3 1 .9\n.3 .3 .9 1\n")
        ctx = Modelo().preparar(inst)
        solo_relocate = busqueda_local(ctx, [[0, 2], [1, 3]], swap=False)
        con_swap = busqueda_local(ctx, [[0, 2], [1, 3]])
        self.assertEqual(sorted(sorted(c) for c in solo_relocate), [[0, 2], [1, 3]])
        self.assertEqual(sorted(sorted(c) for c in con_swap), [[0, 1], [2, 3]])


if __name__ == "__main__":
    unittest.main()
