"""Tests de lectura, escritura, validación y evaluación.

Correr desde la raíz del repo:
    python3 -m unittest discover -s tests -t .
"""

import os
import subprocess
import sys
import tempfile
import unittest

from tp2.instancia import (FormatoInvalido, formatear_solucion, leer_instancia,
                           parsear_instancia, parsear_solucion)
from tp2.modelo import Modelo
from tp2.solucion import SolucionInvalida, validar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EJEMPLO = os.path.join(RAIZ, "instancias", "ejemplo_enunciado.txt")


class TestLectura(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        inst = leer_instancia(EJEMPLO)
        self.assertEqual(inst.n, 4)
        self.assertEqual(inst.capacidad, 10.0)
        self.assertEqual(inst.pesos, [4, 5, 3, 6])
        self.assertEqual(inst.temperaturas, [4, 4, 20, -18])
        self.assertAlmostEqual(inst.similitudes[0][1], 0.9)
        self.assertAlmostEqual(inst.similitudes[3][2], 0.1)

    def test_tolera_espacios_y_saltos_de_linea(self):
        inst = parsear_instancia("2   7.5\n\n 1.5 4\n2 -18\n1 0.5\n0.5   1\n\n")
        self.assertEqual((inst.n, inst.capacidad, inst.pesos), (2, 7.5, [1.5, 2.0]))

    def test_errores_de_formato(self):
        casos = {
            "vacio": "",
            "n_no_entero": "2.5 10\n",
            "faltan_numeros": "2 10\n1 4\n2 4\n1 0.5\n",
            "peso_negativo": "1 10\n-1 4\n1\n",
            "peso_mayor_que_C": "1 10\n11 4\n1\n",
            "no_simetrica": "2 10\n1 4\n2 4\n1 0.3\n0.4 1\n",
            "diagonal_distinta_de_1": "2 10\n1 4\n2 4\n0.9 0.3\n0.3 1\n",
            "fuera_de_rango": "2 10\n1 4\n2 4\n1 1.5\n1.5 1\n",
            "texto": "2 10\n1 a\n2 4\n1 0.3\n0.3 1\n",
        }
        for nombre, texto in casos.items():
            with self.subTest(nombre):
                with self.assertRaises(FormatoInvalido):
                    parsear_instancia(texto)


class TestSalida(unittest.TestCase):
    def test_formato_y_vehiculos_vacios(self):
        self.assertEqual(formatear_solucion([[1, 0], [], [3, 2]]), "0 1\n2 3\n")

    def test_ida_y_vuelta(self):
        sol = [[0, 1], [2, 3]]
        self.assertEqual(parsear_solucion(formatear_solucion(sol)), sol)


class TestValidacionYEvaluacion(unittest.TestCase):
    def setUp(self):
        self.inst = leer_instancia(EJEMPLO)

    def test_las_8_soluciones_factibles_del_ejemplo(self):
        # (solución, K, similitud total) calculados a mano / por fuerza bruta.
        esperado = [
            ([[0, 1], [2, 3]], 2, 1.0),
            ([[0, 3], [1, 2]], 2, 0.5),
            ([[0, 1], [2], [3]], 3, 0.9),
            ([[0], [1], [2, 3]], 3, 0.1),
            ([[0], [1, 2], [3]], 3, 0.2),
            ([[0, 2], [1], [3]], 3, 0.1),
            ([[0, 3], [1], [2]], 3, 0.3),
            ([[0], [1], [2], [3]], 4, 0.0),
        ]
        ctx = Modelo("ninguno", theta=0).preparar(self.inst)
        ctx.alpha, ctx.beta = 1.0, 1.0
        for sol, K, sim in esperado:
            with self.subTest(sol=sol):
                validar(self.inst, sol)
                self.assertAlmostEqual(sum(ctx.similitud(c) for c in sol), sim)
                self.assertAlmostEqual(ctx.valor(sol), K - sim)
        self.assertEqual(ctx.camiones_minimos, 2)

    def test_soluciones_invalidas(self):
        casos = {
            "excede_capacidad": [[0, 1, 2], [3]],      # 4 + 5 + 3 = 12 > 10
            "producto_repetido": [[0, 1], [1, 2, 3]],
            "falta_producto": [[0, 1], [2]],
            "indice_inexistente": [[0, 1], [2, 3, 7]],
        }
        for nombre, sol in casos.items():
            with self.subTest(nombre):
                with self.assertRaises(SolucionInvalida):
                    validar(self.inst, sol)

    def test_minimo_por_peso_con_redondeo(self):
        inst = parsear_instancia("3 1\n0.1 0\n0.2 0\n0.7 0\n1 0 0\n0 1 0\n0 0 1\n")
        # 0.1 + 0.2 + 0.7 da 0.9999999999999999: no tiene que sumar un camión
        self.assertEqual(Modelo().preparar(inst).camiones_minimos, 1)


class TestProgramaPrincipal(unittest.TestCase):
    def test_evaluar_una_solucion(self):
        with tempfile.TemporaryDirectory() as tmp:
            sol = os.path.join(tmp, "sol.txt")
            with open(sol, "w") as f:
                f.write("0\n1\n2\n3\n")
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "main.py"), EJEMPLO, sol,
                                "--evaluar"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("K=4", r.stdout)

    def test_todos_los_algoritmos_corren(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "sol.txt")
            for alg in ("bfd", "parecido", "bl", "ils"):
                for cons in ("bfd", "parecido"):
                    with self.subTest(alg=alg, constructiva=cons):
                        r = subprocess.run([sys.executable, os.path.join(RAIZ, "main.py"), EJEMPLO,
                                            out, "--algoritmo", alg, "--constructiva", cons,
                                            "--tiempo", "0.2"], capture_output=True, text=True)
                        self.assertEqual(r.returncode, 0, r.stderr)
                        self.assertIn("respeta el modelo: sí", r.stdout)

    def test_ils_con_modelo_recomendado(self):
        # Con ventanas de temperatura el congelado (3) viaja solo y el ambiente (2) puede
        # ir con los refrigerados (0, 1) si entra: 4 + 5 = 9, y 9 + 3 > 10.
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "sol.txt")
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "main.py"), EJEMPLO, out,
                                "--tiempo", "1"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("respeta el modelo: sí", r.stdout)
            with open(out) as f:
                sol = parsear_solucion(f.read())
            self.assertIn([3], sol)
            self.assertIn([0, 1], sol)

    def test_error_claro_si_la_instancia_es_invalida(self):
        with tempfile.TemporaryDirectory() as tmp:
            mala = os.path.join(tmp, "mala.txt")
            with open(mala, "w") as f:
                f.write("2 10\n1 4\n")
            r = subprocess.run([sys.executable, os.path.join(RAIZ, "main.py"), mala,
                                os.path.join(tmp, "o.txt")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Error", r.stderr)


if __name__ == "__main__":
    unittest.main()
