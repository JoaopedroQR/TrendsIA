"""
Testes da lógica local, sem chamadas reais ao LLM.

Como executar (na mesma pasta do código principal):
    python -m unittest test_sintese -v
    # ou, se tiver pytest:
    pytest test_sintese.py -v

IMPORTANTE: ajuste MODULO abaixo para o nome do seu arquivo (sem .py).
Ex.: se o código está em main.py, use MODULO = "main".
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

MODULO = "main"  # <-- troque pelo nome do seu arquivo

# Se o SDK do Gemini / dotenv não estiverem instalados, usa stubs só para importar.
for nome in ("google", "google.genai", "google.genai.types", "dotenv"):
    try:
        importlib.import_module(nome)
    except ImportError:
        sys.modules[nome] = MagicMock()

app = importlib.import_module(MODULO)

CONFIG_VALIDO = {
    "modelos": ["modelo-a", "modelo-b"],
    "timeout_milisegundos": 30000,
    "timeout_segundos": 30,
    "temperatura": 0.3,
    "max_output_tokens": 1024,
}


class ErroFake(Exception):
    """Simula um erro da API com status HTTP."""

    def __init__(self, mensagem="erro", status_code=None):
        super().__init__(mensagem)
        self.status_code = status_code


class TestCarregarParametros(unittest.TestCase):
    def _com_arquivo(self, conteudo):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        tmp.write(conteudo)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return Path(tmp.name)

    def test_config_valido(self):
        caminho = self._com_arquivo(json.dumps(CONFIG_VALIDO))
        with patch.object(app, "CONFIG_PATH", caminho):
            self.assertEqual(app.carregar_parametros(), CONFIG_VALIDO)

    def test_arquivo_inexistente(self):
        with patch.object(app, "CONFIG_PATH", Path("/nao/existe/config.json")):
            with self.assertRaises(FileNotFoundError):
                app.carregar_parametros()

    def test_json_invalido(self):
        caminho = self._com_arquivo("{ isso não é json")
        with patch.object(app, "CONFIG_PATH", caminho):
            with self.assertRaisesRegex(ValueError, "inválido"):
                app.carregar_parametros()

    def test_chave_obrigatoria_ausente(self):
        caminho = self._com_arquivo(json.dumps({"modelos": ["x"]}))
        with patch.object(app, "CONFIG_PATH", caminho):
            with self.assertRaisesRegex(ValueError, "timeout_milisegundos"):
                app.carregar_parametros()


class TestCapturarEntrada(unittest.TestCase):
    def test_entrada_valida_remove_espacos(self):
        with patch("builtins.input", return_value="  olá reunião  "):
            self.assertEqual(app.capturar_entrada(), "olá reunião")

    def test_entrada_vazia(self):
        with patch("builtins.input", return_value=""):
            with self.assertRaises(ValueError):
                app.capturar_entrada()

    def test_entrada_apenas_espacos(self):
        with patch("builtins.input", return_value="   \t "):
            with self.assertRaises(ValueError):
                app.capturar_entrada()


class TestPrepararSolicitacao(unittest.TestCase):
    def test_prompt_contem_transcricao_e_instrucoes(self):
        transcricao = "[00:01] João: Vamos lançar na segunda."
        prompt = app.preparar_solicitacao(transcricao)
        self.assertIn(transcricao, prompt)
        self.assertIn("síntese", prompt)
        self.assertIn("Transcrição:", prompt)


class TestCarregarConfiguracao(unittest.TestCase):
    def test_sem_api_key(self):
        with patch.object(app, "load_dotenv"), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
                app.carregar_configuracao(CONFIG_VALIDO)

    def test_api_key_em_branco(self):
        with patch.object(app, "load_dotenv"), patch.dict(os.environ, {"GEMINI_API_KEY": "   "}, clear=True):
            with self.assertRaises(ValueError):
                app.carregar_configuracao(CONFIG_VALIDO)

    def test_cliente_criado_com_chave(self):
        with patch.object(app, "load_dotenv"), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "chave-falsa"}, clear=True), \
             patch.object(app.genai, "Client") as client_cls:
            client = app.carregar_configuracao(CONFIG_VALIDO)

        self.assertIs(client, client_cls.return_value)
        self.assertEqual(client_cls.call_args.kwargs["api_key"], "chave-falsa")

    def test_falha_ao_inicializar_cliente(self):
        with patch.object(app, "load_dotenv"), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "chave-falsa"}, clear=True), \
             patch.object(app.genai, "Client", side_effect=Exception("boom")):
            with self.assertRaisesRegex(RuntimeError, "inicializar o cliente"):
                app.carregar_configuracao(CONFIG_VALIDO)


class TestTratarResposta(unittest.TestCase):
    def test_resposta_valida(self):
        interaction = SimpleNamespace(output_text="Síntese pronta.")
        self.assertEqual(app.tratar_resposta(interaction), "Síntese pronta.")

    def test_resposta_vazia(self):
        with self.assertRaises(ValueError):
            app.tratar_resposta(SimpleNamespace(output_text="   "))

    def test_resposta_none(self):
        with self.assertRaises(ValueError):
            app.tratar_resposta(SimpleNamespace(output_text=None))


class TestChamarModelo(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()

    def test_sucesso_no_primeiro_modelo(self):
        esperado = SimpleNamespace(output_text="ok")
        self.client.interactions.create.return_value = esperado

        resultado = app.chamar_modelo(self.client, "prompt", CONFIG_VALIDO)

        self.assertIs(resultado, esperado)
        self.assertEqual(self.client.interactions.create.call_count, 1)
        self.assertEqual(self.client.interactions.create.call_args.kwargs["model"], "modelo-a")

    def test_fallback_quando_primeiro_modelo_indisponivel(self):
        esperado = SimpleNamespace(output_text="ok")
        self.client.interactions.create.side_effect = [ErroFake("indisponível", 503), esperado]

        resultado = app.chamar_modelo(self.client, "prompt", CONFIG_VALIDO)

        self.assertIs(resultado, esperado)
        modelos_usados = [c.kwargs["model"] for c in self.client.interactions.create.call_args_list]
        self.assertEqual(modelos_usados, ["modelo-a", "modelo-b"])

    def test_todos_os_modelos_falham(self):
        self.client.interactions.create.side_effect = ErroFake("limite", 429)
        with self.assertRaisesRegex(RuntimeError, "Nenhum dos modelos"):
            app.chamar_modelo(self.client, "prompt", CONFIG_VALIDO)
        self.assertEqual(self.client.interactions.create.call_count, 2)

    def test_erro_nao_recuperavel_e_propagado(self):
        self.client.interactions.create.side_effect = ErroFake("requisição inválida", 400)
        with self.assertRaises(ErroFake):
            app.chamar_modelo(self.client, "prompt", CONFIG_VALIDO)
        # Não deve tentar o segundo modelo
        self.assertEqual(self.client.interactions.create.call_count, 1)

    def test_timeout_aciona_fallback(self):
        class ReadTimeout(Exception):
            pass

        esperado = SimpleNamespace(output_text="ok")
        self.client.interactions.create.side_effect = [ReadTimeout("demorou"), esperado]
        self.assertIs(app.chamar_modelo(self.client, "prompt", CONFIG_VALIDO), esperado)


class TestEhTimeout(unittest.TestCase):
    def test_detecta_pelo_nome_da_classe(self):
        class TimeoutError_(Exception):
            pass
        self.assertTrue(app._eh_timeout(TimeoutError_()))

    def test_detecta_pela_mensagem(self):
        self.assertTrue(app._eh_timeout(Exception("Request timed out")))

    def test_erro_comum(self):
        self.assertFalse(app._eh_timeout(Exception("outro erro")))


class TestMain(unittest.TestCase):
    """Fluxo completo com tudo simulado."""

    def test_fluxo_feliz_imprime_sintese(self):
        with patch.object(app, "carregar_parametros", return_value=CONFIG_VALIDO), \
             patch.object(app, "capturar_entrada", return_value="transcrição"), \
             patch.object(app, "carregar_configuracao", return_value=MagicMock()), \
             patch.object(app, "chamar_modelo", return_value=SimpleNamespace(output_text="Resumo final")), \
             patch("builtins.print") as fake_print:
            app.main()

        saidas = " ".join(str(c.args[0]) for c in fake_print.call_args_list)
        self.assertIn("SÍNTESE DA REUNIÃO", saidas)
        self.assertIn("Resumo final", saidas)

    def test_erro_e_tratado_sem_quebrar(self):
        with patch.object(app, "carregar_parametros", side_effect=ValueError("config ruim")), \
             patch("builtins.print") as fake_print:
            app.main()  # não deve levantar exceção

        self.assertIn("Erro ao gerar a síntese", fake_print.call_args.args[0])


if __name__ == "__main__":
    unittest.main()