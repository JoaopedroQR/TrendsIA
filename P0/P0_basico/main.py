import os
import json
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

CONFIG_PATH = Path(__file__).parent / "config.json"

def carregar_parametros():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as arquivo:
            config = json.load(arquivo)
    except FileNotFoundError as erro:
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_PATH}") from erro
    except json.JSONDecodeError as erro:
        raise ValueError(f"config.json inválido: {erro}") from erro

    obrigatorios = ["modelos", "timeout_milisegundos"]
    faltando = [chave for chave in obrigatorios if chave not in config]
    if faltando:
        raise ValueError(f"Chaves ausentes no config.json: {', '.join(faltando)}")

    return config



"""
[00:01] João: Pessoal, precisamos definir a data do lançamento da funcionalidade de relatórios. [00:15] Maria: A equipe de design já entregou as telas, mas o backend ainda precisa de mais 3 dias para ajustar as consultas do banco de dados. [00:40] Carlos: Se o backend precisa de 3 dias, acho seguro movermos a homologação para quinta-feira e o lançamento oficial para a próxima segunda-feira. [01:05] João: De acordo. Maria, você avisa o time de QA sobre a mudança na homologação? [01:15] Maria: Aviso sim. Vou atualizar o card no Jira também.
"""

def capturar_entrada():
    texto = input("Digite o texto para síntese: ").strip()

    if not texto:
        raise ValueError('A entrada não pode estar vazia.')

    return texto


def carregar_configuracao(config):
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not api_key.strip():
        raise ValueError("A variável GEMINI_API_KEY não foi configurada.")

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=config["timeout_milisegundos"])

        )
    except Exception as erro:
        raise RuntimeError(f'Não foi possível inicializar o cliente: {erro}') from erro
    

    return client

def preparar_solicitacao(texto):
    transcricao = texto

    prompt = f"""
    Você é um assistente especialista em síntese de reuniões.
    Analise a transcrição abaixo e gere um documento síntese
    fluido, focando nas principais ideias, decisões tomadas
    e encaminhamentos acordados.

    Não divida em apenas tópicos mecânicos; construa um texto
    coeso que explique o contexto e o desfecho.

    Transcrição:
    {transcricao}
    """

    return prompt


def _eh_timeout(erro):
    nome = type(erro).__name__.lower()
    return "timeout" in nome or "timed out" in str(erro).lower()

def chamar_modelo(client, prompt, config):

    for modelo in config["modelos"]:
        print(f"Testando modelo: {modelo}")

        try:
            interaction = client.interactions.create(
                model=modelo,
                input= prompt,
                timeout=config["timeout_segundos"],
                generation_config={
                    "temperature": config["temperatura"],
                    "max_output_tokens": config["max_output_tokens"],
                },
            )

            return interaction
        
        except Exception as erro:
            status = getattr(erro, "status_code", None) or getattr(erro, "code", None)

            if _eh_timeout(erro) or status in (404, 429, 500, 503, 504):
                print(f"Modelo {modelo} indisponível ({status}). Tentando o próximo...")
                continue

            raise
            

    raise RuntimeError(
        "Nenhum dos modelos configurados conseguiu gerar uma síntese."
    )

def tratar_resposta(interaction):
    resultado = interaction.output_text

    if not resultado or not resultado.strip():
        raise ValueError("O modelo não retornou uma síntese.")

    return resultado

# Fluxo principal
def main():
    try:
        config = carregar_parametros()
        texto = capturar_entrada()
        client = carregar_configuracao(config)
        prompt = preparar_solicitacao(texto)
        resposta = chamar_modelo(client, prompt, config)
        resultado = tratar_resposta(resposta)

        # 5. Exibição do resultado
        print("=== SÍNTESE DA REUNIÃO ===")
        print(resultado)

    except Exception as erro:
        print(f"Erro ao gerar a síntese: {erro}")


if __name__ == "__main__":
    main()
