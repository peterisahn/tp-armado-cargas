"""Tests del modelo y el generador.

Correr desde la raíz del repo:
    python3 -m unittest discover -s tests -t .
"""

import math
import random
import unittest

from tp2.generador import formatear_instancia, generar
from tp2.instancia import Instancia, parsear_instancia
from tp2.modelo import Modelo, categoria, inseguro


def particiones(xs):
    if not xs:
        yield []
        return
    f, r = xs[0], xs[1:]
    for p in particiones(r):
        for i in range(len(p)):
            yield p[:i] + [[f] + p[i]] + p[i + 1:]
        yield [[f]] + p


def instancia_azar(rng, n, C=10.0):
    w = [float(rng.randint(1, 7)) for _ in range(n)]
    t = [rng.choice([-18.0, 4.0, 8.0, 20.0, 65.0]) for _ in range(n)]
    s = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s[i][j] = s[j][i] = round(rng.random(), 3)
    return Instancia(n, C, w, t, s)


class TestVentanas(unittest.TestCase):
    def test_categorias_y_seguridad(self):
        self.assertEqual([categoria(t) for t in (-18, 4, 20, 65)],
                         ["congelado", "refrigerado", "ambiente", "caliente"])
        self.assertEqual(categoria(45), "caliente")   # 30-60 °C: sólo comida que se enfría
        self.assertFalse(inseguro(["refrigerado", "ambiente"]))   # secos viajan refrigerados
        self.assertTrue(inseguro(["congelado", "refrigerado"]))
        self.assertTrue(inseguro(["caliente", "ambiente"]))

    def test_variantes_sobre_el_ejemplo(self):
        # productos: 0 y 1 a 4 °C, 2 a 20 °C, 3 a -18 °C
        inst = parsear_instancia("4 100\n4 4\n5 4\n3 20\n6 -18\n"
                                 "1 .9 .1 .3\n.9 1 .2 .3\n.1 .2 1 .1\n.3 .3 .1 1\n")
        casos = {
            "ninguno": [True, True, True],
            "zonas": [True, False, False],
            "ventanas": [True, True, False],
        }
        for modo, esperado in casos.items():
            ctx = Modelo(modo, theta=0).preparar(inst)
            got = [ctx.camion_valido(v) for v in ([0, 1], [0, 1, 2], [0, 3])]
            self.assertEqual(got, esperado, modo)
        ctx = Modelo("umbral", delta=20, theta=0).preparar(inst)
        self.assertTrue(ctx.camion_valido([0, 1, 2]))   # 4..20: rango 16
        self.assertFalse(ctx.camion_valido([2, 3]))     # -18..20: rango 38

    def test_theta(self):
        inst = parsear_instancia("3 100\n1 4\n1 4\n1 4\n1 .5 .1\n.5 1 .5\n.1 .5 1\n")
        ctx = Modelo("ventanas", theta=0.2).preparar(inst)
        self.assertTrue(ctx.camion_valido([0, 1]))
        self.assertFalse(ctx.camion_valido([0, 2]))


class TestModelo(unittest.TestCase):
    def test_de_a_pares_alcanza(self):
        # Si todos los pares de un camión son compatibles, existe una temperatura común:
        # camion_valido (que mira de a pares) coincide con max(L) <= min(U).
        rng = random.Random(7)
        for _ in range(200):
            inst = instancia_azar(rng, rng.randint(2, 6), C=100.0)
            for modelo in (Modelo("ventanas", theta=0), Modelo("umbral", delta=20, theta=0)):
                ctx = modelo.preparar(inst)
                todos = list(range(inst.n))
                hay_temperatura = max(ctx.L[i] for i in todos) <= min(ctx.U[i] for i in todos)
                self.assertEqual(ctx.camion_valido(todos), hay_temperatura)

    def test_beta_normalizado(self):
        inst = instancia_azar(random.Random(1), 12, C=10.0)
        ctx = Modelo("ninguno", lam=1.0).preparar(inst)
        b = inst.n / math.ceil(inst.peso_total / inst.capacidad)
        self.assertAlmostEqual(ctx.beta, 1.0 / max(1.0, b * (b - 1) / 2))
        self.assertEqual(ctx.alpha, 1.0)

    def test_valor_es_alpha_K_menos_beta_S(self):
        inst = instancia_azar(random.Random(2), 8)
        ctx = Modelo("ninguno", theta=0).preparar(inst)
        sol = [[0, 1, 2], [3], [4, 5, 6, 7]]
        S = sum(inst.similitudes[a][b] for c in sol for x, a in enumerate(c) for b in c[x + 1:])
        self.assertAlmostEqual(ctx.valor(sol), ctx.alpha * 3 - ctx.beta * S)


class TestGenerador(unittest.TestCase):
    def test_reproducible_y_valido(self):
        pesos = [float(x) for x in range(1, 31)]
        a = generar(pesos, 100.0, semilla=42)
        b = generar(pesos, 100.0, semilla=42)
        self.assertEqual(a, b)
        _, temps, s = a
        inst = parsear_instancia(formatear_instancia(100.0, pesos, temps, s))  # valida formato
        self.assertEqual(inst.n, 30)


if __name__ == "__main__":
    unittest.main()
