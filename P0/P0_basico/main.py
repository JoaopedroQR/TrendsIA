import os
import httpx
from google import genai
from google.genai import types, errors
from dotenv import load_dotenv

TIMEOUT_MS = 15000

MODELOS = ['gemini-3.5-flash', 'gemini-3.5-flash-lite']

"""
[00:01] João: Pessoal, precisamos definir a data do lançamento da funcionalidade de relatórios. [00:15] Maria: A equipe de design já entregou as telas, mas o backend ainda precisa de mais 3 dias para ajustar as consultas do banco de dados. [00:40] Carlos: Se o backend precisa de 3 dias, acho seguro movermos a homologação para quinta-feira e o lançamento oficial para a próxima segunda-feira. [01:05] João: De acordo. Maria, você avisa o time de QA sobre a mudança na homologação? [01:15] Maria: Aviso sim. Vou atualizar o card no Jira também.
"""

def capturar_entrada():
    texto = input("Digite o texto para síntese: ").strip()

    if not texto:
        raise ValueError('A entrada não pode estar vazia.')

    return texto


def carregar_configuracao():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not api_key.strip():
        raise ValueError("A variável GEMINI_API_KEY não foi configurada.")

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=TIMEOUT_MS)

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

def chamar_modelo(client, prompt):

    for modelo in MODELOS:
        print(f"Testando modelo: {modelo}")

        try:
            interaction = client.interactions.create(
                model=modelo,
                input= prompt,
                timeout=20,
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
        texto = capturar_entrada()
        client = carregar_configuracao()
        prompt = preparar_solicitacao(texto)
        resposta = chamar_modelo(client, prompt)
        resultado = tratar_resposta(resposta)

        # 5. Exibição do resultado
        print("=== SÍNTESE DA REUNIÃO ===")
        print(resultado)

    except Exception as erro:
        print(f"Erro ao gerar a síntese: {erro}")


if __name__ == "__main__":
    main()
