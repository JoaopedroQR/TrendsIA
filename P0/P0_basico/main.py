import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# 1. Instancia o cliente (lê automaticamente a variável GEMINI_API_KEY)
client = genai.Client(api_key = os.getenv("MINHA_CHAVE_API"))

texto = input("Digite o texto para síntese: ")

# 2. Exemplo de transcrição bruta para teste
transcricao = "" + texto
# [00:01] João: Pessoal, precisamos definir a data do lançamento da funcionalidade de relatórios. [00:15] Maria: A equipe de design já entregou as telas, mas o backend ainda precisa de mais 3 dias para ajustar as consultas do banco de dados. [00:40] Carlos: Se o backend precisa de 3 dias, acho seguro movermos a homologação para quinta-feira e o lançamento oficial para a próxima segunda-feira. [01:05] João: De acordo. Maria, você avisa o time de QA sobre a mudança na homologação? [01:15] Maria: Aviso sim. Vou atualizar o card no Jira também.


# 3. Construção da instrução (Prompt)
prompt = f"""
Você é um assistente especialista em síntese de reuniões.
Analise a transcrição abaixo e gere um documento síntese fluido, focando nas principais ideias, decisões tomadas e encaminhamentos acordados.
Não divida em apenas tópicos mecânicos; construa um texto coeso que explique o contexto e o desfecho.

Transcrição:
{transcricao}
"""

# 4. Chamada ao modelo programaticamente
interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input= prompt
)

# 5. Exibição do resultado
print("=== SÍNTESE DA REUNIÃO ===")
print(interaction.output_text)