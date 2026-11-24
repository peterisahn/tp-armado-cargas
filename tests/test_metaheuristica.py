"""Tests de la metaheurística (ILS).

Correr desde la raíz del repo:
    python3 -m unittest discover -s tests -t .
"""

import random
import unittest

from tests.test_modelo import instancia_azar
from tp2.busqueda_local import busqueda_local
from tp2.constructivas import construir
from tp2.metaheuristica import elegir_camiones_a_romper, ils, romper_y_rearmar
from tp2.modelo import Modelo
from tp2.solucion import validar


class TestILS(unittest.TestCase):
    def test_romper_y_rearmar_da_soluciones_validas(self):
        rng = random.Random(5)
        for _ in range(30):
            inst = instancia_azar(rng, rng.randint(4, 12))
            ctx = Modelo().preparar(inst)
            for criterio in ("bfd", "parecido"):
                sol = construir(ctx, criterio)
                for fraccion in (0.0, 0.25, 0.5, 1.0):
                    nueva = romper_y_rearmar(ctx, sol, fraccion, criterio, rng)
                    validar(inst, nueva)
                    self.assertTrue(all(ctx.camion_valido(c) for c in nueva))

    def test_ils_valido_y_no_peor_que_la_busqueda_local(self):
        rng = random.Random(9)
        for _ in range(6):
            inst = instancia_azar(rng, rng.randint(6, 14))
            ctx = Modelo().preparar(inst)
            for criterio in ("bfd", "parecido"):
                inicial = busqueda_local(ctx, construir(ctx, criterio))
                sol = ils(ctx, tiempo_max=0.2, semilla=0, constructiva=criterio)
                validar(inst, sol)
                self.assertTrue(all(ctx.camion_valido(c) for c in sol))
                self.assertLessEqual(ctx.valor(sol), ctx.valor(inicial) + 1e-9)

    def test_se_rompe_el_menos_cargado_y_una_fraccion(self):
        rng = random.Random(3)
        inst = instancia_azar(rng, 12)
        ctx = Modelo(temperatura="ninguno", theta=0.0).preparar(inst)
        for K in (2, 3, 6, 11):
            sol = [[i] for i in range(K)]
            menos = min(range(K), key=lambda k: ctx.carga(sol[k]))
            for fraccion, extra in ((0.25, K // 4), (0.5, K // 2)):
                rotos = elegir_camiones_a_romper(ctx, sol, fraccion, random.Random(K))
                self.assertIn(menos, rotos)
                self.assertEqual(len(rotos), min(K, 1 + extra))


if __name__ == "__main__":
    unittest.main()
