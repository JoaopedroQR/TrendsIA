# Sintetizador de Reuniões com Gemini

Aplicação que recebe a transcrição de uma reunião e gera, com a API do Google Gemini, uma síntese em texto corrido, destacando as principais ideias, as decisões tomadas e os encaminhamentos acordados.

O projeto conta com **fallback automático entre modelos**: se o primeiro modelo estiver indisponível (erro 503, 429, timeout etc.), a aplicação tenta o próximo da lista.

## Como funciona

O fluxo principal (`main.py`) segue estas etapas:

1. **Entrada:** solicita o texto da transcrição no terminal e valida que não está vazio.
2. **Configuração:** carrega a variável `GEMINI_API_KEY` do arquivo `.env` e inicializa o cliente do Gemini.
3. **Prompt:** monta a instrução pedindo uma síntese coesa, e não apenas tópicos mecânicos.
4. **Chamada ao modelo:** percorre a lista `MODELOS` e usa o primeiro que responder.
5. **Resposta:** valida o retorno e exibe a síntese no terminal.

## Pré-requisitos

- Python 3.10 ou superior
- Uma chave de API do Gemini (obtenha no [Google AI Studio](https://aistudio.google.com/apikey))

## Estrutura do projeto

```
.
├── main.py            # Código principal
├── requirements.txt   # Dependências
├── .env               # Chave da API (não versionar)
└── .gitignore
```

> **Atenção:** se os arquivos estiverem como `_env` e `_gitignore`, renomeie-os para `.env` e `.gitignore`. Alguns sistemas removem o ponto inicial no download ou upload.

## Instalação

1. Clone ou baixe o projeto e entre na pasta:

   ```bash
   cd nome-da-pasta-do-projeto
   ```

2. Crie e ative um ambiente virtual:

   ```bash
   # Linux / macOS
   python -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

## Configuração

Crie um arquivo `.env` na raiz do projeto com a sua chave:

```env
GEMINI_API_KEY=sua_chave_aqui
```

Nunca publique esse arquivo. Confirme que `.env` está listado no `.gitignore`.

### Ajustes opcionais no `main.py`

| Constante / parâmetro | Descrição | Valor atual |
|---|---|---|
| `MODELOS` | Lista de modelos em ordem de prioridade (fallback) | `gemini-3.5-flash`, `gemini-3.5-flash-lite` |
| `TIMEOUT_MS` | Timeout do cliente HTTP, em **milissegundos** | `15000` |
| `timeout` em `chamar_modelo` | Timeout da requisição individual | `20` |

Se estiver recebendo timeouts com prompts grandes, aumente esses valores.

## Execução

Com o ambiente virtual ativo, rode:

```bash
python main.py
```

Quando o programa pedir, cole a transcrição e pressione Enter:

```
Digite o texto para síntese: [00:01] João: Pessoal, precisamos definir a data do lançamento...
```

> **Dica:** o `input()` lê apenas **uma linha**. Se a transcrição tiver várias linhas, cole-a em uma única linha (como no exemplo) ou adapte a função `capturar_entrada()` para ler de um arquivo.

### Exemplo de transcrição

```
[00:01] João: Pessoal, precisamos definir a data do lançamento da funcionalidade de relatórios. [00:15] Maria: A equipe de design já entregou as telas, mas o backend ainda precisa de mais 3 dias para ajustar as consultas do banco de dados. [00:40] Carlos: Se o backend precisa de 3 dias, acho seguro movermos a homologação para quinta-feira e o lançamento oficial para a próxima segunda-feira. [01:05] João: De acordo. Maria, você avisa o time de QA sobre a mudança na homologação? [01:15] Maria: Aviso sim. Vou atualizar o card no Jira também.
```

### Saída esperada

```
Testando modelo: gemini-3.5-flash
=== SÍNTESE DA REUNIÃO ===
<texto da síntese gerado pelo modelo>
```

## Tratamento de erros

| Situação | Comportamento |
|---|---|
| Entrada vazia | Exibe erro e encerra |
| `GEMINI_API_KEY` ausente | Exibe erro de configuração e encerra |
| Timeout, 404, 429, 500, 503 ou 504 | Registra a falha e tenta o próximo modelo |
| Outros erros (ex.: 400, 401) | Interrompe e exibe a mensagem, sem esconder o problema |
| Todos os modelos falharam | Exibe "Nenhum dos modelos configurados conseguiu gerar uma síntese." |
| Resposta vazia do modelo | Exibe "O modelo não retornou uma síntese." |

## Solução de problemas

- **`A variável GEMINI_API_KEY não foi configurada`:** verifique se o `.env` está na mesma pasta de onde você executa o `python main.py` e se o nome da variável está correto.
- **`Request timed out`:** aumente `TIMEOUT_MS` e o `timeout` de `chamar_modelo`. Lembre-se de que `TIMEOUT_MS` é em milissegundos.
- **Erro 503 (alta demanda):** é temporário. O fallback tentará o próximo modelo; se todos falharem, aguarde alguns instantes e tente de novo.
- **Erro 404 no modelo:** o nome do modelo em `MODELOS` pode estar incorreto ou indisponível para a sua conta. Confira os nomes na documentação do Gemini.

## Dependências principais

- [`google-genai`](https://pypi.org/project/google-genai/): SDK oficial do Gemini
- [`python-dotenv`](https://pypi.org/project/python-dotenv/): leitura do arquivo `.env`
- [`httpx`](https://www.python-httpx.org/): cliente HTTP usado pelo SDK