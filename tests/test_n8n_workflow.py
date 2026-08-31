import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from src.api import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = PROJECT_ROOT / "docs" / "low-code" / "javalog-agent-n8n.json"
REPRODUCAO = PROJECT_ROOT / "docs" / "low-code" / "reproducao.md"
LOG_LIMPO = "examples/logs/application-clean.log"

TIPOS_ESPERADOS = [
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.respondToWebhook",
]

# Nos que executariam logica dentro do fluxo. A regra da etapa e que validacao,
# extracao, classificacao e diagnostico vivem na aplicacao, nao no orquestrador.
TIPOS_COM_LOGICA = [
    "n8n-nodes-base.code",
    "n8n-nodes-base.function",
    "n8n-nodes-base.functionItem",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.filter",
    "n8n-nodes-base.set",
    "n8n-nodes-base.itemLists",
    "n8n-nodes-base.executeCommand",
]


@pytest.fixture(scope="module")
def fluxo():
    return json.loads(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bruto():
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture
def client():
    return TestClient(app)


def no_por_tipo(fluxo, tipo):
    return next(n for n in fluxo["nodes"] if n["type"] == tipo)


# ------------------------------------------------------ estrutura do fluxo


def test_workflow_e_json_valido(fluxo):
    assert isinstance(fluxo, dict)
    assert isinstance(fluxo["nodes"], list)


def test_workflow_tem_exatamente_os_tres_nos_esperados(fluxo):
    assert [n["type"] for n in fluxo["nodes"]] == TIPOS_ESPERADOS


def test_workflow_declara_id_de_topo(fluxo):
    # `import:workflow` recusa o arquivo sem este campo, com violação de
    # restrição no banco: sem ele o fluxo não chega a existir na instância.
    assert fluxo["id"]


def test_url_usa_endereco_ipv4_explicito(fluxo):
    # `localhost` resolve primeiro para `::1` em Node 24; uma API ligada a
    # 127.0.0.1 recusa essa conexão.
    destino = urlparse(no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")
                       ["parameters"]["url"])

    assert destino.hostname == "127.0.0.1"
    assert destino.port == 8000


def test_workflow_nao_tem_no_que_execute_logica(fluxo):
    presentes = [n["type"] for n in fluxo["nodes"] if n["type"] in TIPOS_COM_LOGICA]

    assert presentes == []


def test_gatilho_e_um_webhook_que_aceita_post(fluxo):
    webhook = no_por_tipo(fluxo, "n8n-nodes-base.webhook")

    assert webhook["parameters"]["httpMethod"] == "POST"
    assert webhook["parameters"]["path"]


def test_saida_observavel_responde_ao_webhook(fluxo):
    webhook = no_por_tipo(fluxo, "n8n-nodes-base.webhook")
    resposta = no_por_tipo(fluxo, "n8n-nodes-base.respondToWebhook")

    # Sem `responseNode`, o webhook responderia sozinho e o no de resposta
    # nunca seria alcancado.
    assert webhook["parameters"]["responseMode"] == "responseNode"
    assert resposta["parameters"]["respondWith"] == "json"


def test_os_tres_nos_estao_encadeados_na_ordem(fluxo):
    conexoes = fluxo["connections"]

    assert conexoes["Webhook Trigger"]["main"][0][0]["node"] == "HTTP Request"
    assert conexoes["HTTP Request"]["main"][0][0]["node"] == "Respond to Webhook"
    assert "Respond to Webhook" not in conexoes


# --------------------------------------------- integracao com a aplicacao


def test_http_request_chama_o_endpoint_da_aplicacao(fluxo):
    requisicao = no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")

    assert requisicao["parameters"]["method"] == "POST"
    assert urlparse(requisicao["parameters"]["url"]).path == "/api/v1/analyze"


def test_http_request_encaminha_o_corpo_sem_alterar(fluxo):
    requisicao = no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")

    assert requisicao["parameters"]["sendBody"] is True
    assert requisicao["parameters"]["jsonBody"] == "={{ JSON.stringify($json.body) }}"


def test_endpoint_chamado_pelo_fluxo_existe_e_responde(client, fluxo):
    caminho = urlparse(
        no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")["parameters"]["url"]
    ).path

    resposta = client.post(caminho, json={"file_path": LOG_LIMPO})

    assert resposta.status_code == 200
    assert resposta.json()["correlation_id"]


def test_endpoint_do_fluxo_recusa_caminho_fora_do_diretorio(client, fluxo):
    caminho = urlparse(
        no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")["parameters"]["url"]
    ).path

    resposta = client.post(caminho, json={"file_path": "../../etc/passwd"})

    assert resposta.status_code == 400


# ------------------------------------------------- ausencia de credencial


def test_nenhum_no_declara_credencial(fluxo):
    assert [n["name"] for n in fluxo["nodes"] if "credentials" in n] == []


def test_json_nao_traz_chave_de_credencial(bruto):
    achados = re.findall(
        r"\"(credentials|apiKey|accessToken|password|secret|authorization)\"",
        bruto,
        re.IGNORECASE,
    )

    assert achados == []


def test_json_nao_traz_valor_que_pareca_segredo(bruto):
    padroes = [
        "sk" + r"[-_][A-Za-z0-9]{20,}",
        r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}",
        "Bea" + r"rer\s+[A-Za-z0-9._~+/=-]{20,}",
    ]

    for padrao in padroes:
        assert re.search(padrao, bruto, re.IGNORECASE) is None


def test_autenticacao_declarada_como_ausente(fluxo):
    requisicao = no_por_tipo(fluxo, "n8n-nodes-base.httpRequest")

    assert requisicao["parameters"]["authentication"] == "none"


# ------------------------------------------- honestidade da documentacao


def test_reproducao_separa_o_comprovado_do_nao_comprovado():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "## O que foi comprovado" in texto
    assert "## O que NÃO foi comprovado" in texto


def test_reproducao_distingue_execucao_local_de_deploy():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    # Nenhum teste estrutural comprova um evento histórico: o que se verifica
    # aqui é que a página continua declarando os limites da evidência.
    assert "**Deploy**" in texto
    assert "**Disponibilidade contínua**" in texto
    assert "Limitações da evidência registrada" in texto


def test_reproducao_registra_a_execucao_com_dados_verificaveis():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    for campo in (
        "Identificador da execução no n8n",
        "Código HTTP devolvido pelo webhook",
        "URL local do webhook",
        "Payload enviado",
    ):
        assert campo in texto


# --------------------------------------- pre-requisitos e reprodutibilidade


def test_reproducao_declara_os_pre_requisitos_de_runtime():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "Node.js" in texto
    assert re.search(r"npm\s*/\s*npx|npm e npx", texto)
    assert "Python 3.12" in texto


def test_reproducao_fixa_a_versao_do_n8n_em_todos_os_comandos():
    texto = REPRODUCAO.read_text(encoding="utf-8")
    invocacoes = re.findall(r"npx(?:\.cmd)? +(\S+)", texto)

    assert invocacoes, "nenhuma invocacao de npx documentada"
    assert set(invocacoes) == {"n8n@2.36.8"}


PAYLOAD = '{"file_path":"examples/logs/application-clean.log"}'
README = PROJECT_ROOT / "README.md"


def blocos_powershell(texto):
    return [b for lang, b in re.findall(r"```(powershell)\n(.*?)```", texto, re.DOTALL)]


def test_reproducao_traz_sequencias_para_powershell_e_bash():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    # PowerShell precisa de `npx.cmd`, `$env:` e `curl.exe`; o alias `curl` do
    # PowerShell é `Invoke-WebRequest` e não aceita estes argumentos.
    assert "```powershell" in texto
    assert "npx.cmd n8n@2.36.8" in texto
    assert "$env:N8N_USER_FOLDER" in texto
    assert "curl.exe" in texto

    assert "```bash" in texto
    assert "export N8N_USER_FOLDER=" in texto


def test_chamada_powershell_envia_json_valido():
    """Envia o JSON por stdin para não depender do parser de argumentos nativos."""
    for documento in (REPRODUCAO, README):
        texto = documento.read_text(encoding="utf-8")
        chamadas = [b for b in blocos_powershell(texto) if "curl.exe" in b]

        assert chamadas, f"{documento.name}: nenhuma chamada PowerShell"
        for bloco in chamadas:
            assert PAYLOAD in bloco
            assert '\\"' not in bloco
            assert "--data-binary" in bloco
            assert " -d " not in bloco


def test_reproducao_cobre_os_tres_comandos_do_n8n_nas_duas_sequencias():
    texto = REPRODUCAO.read_text(encoding="utf-8")
    blocos = re.findall(r"```(powershell|bash)\n(.*?)```", texto, re.DOTALL)

    def completo(bloco):
        return "N8N_USER_FOLDER" in bloco and all(
            re.search(rf"npx(?:\.cmd)? n8n@2\.36\.8 {c}", bloco)
            for c in ("import:workflow", "publish:workflow", "start")
        )

    for linguagem in ("powershell", "bash"):
        assert any(completo(b) for lang, b in blocos if lang == linguagem)


def test_reproducao_exige_o_mesmo_diretorio_de_dados_dedicado():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "N8N_USER_FOLDER" in texto
    assert re.search(r"mesmo\s+`N8N_USER_FOLDER`", texto)
    assert re.search(r"dedicado, fora do reposit[óo]rio", texto)


def test_reproducao_declara_que_nao_exige_conta_nem_servico_externo():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert re.search(r"não é necessária conta no n8n Cloud", texto, re.IGNORECASE)
    assert re.search(r"não é necessário Docker", texto, re.IGNORECASE)


def test_reproducao_usa_endereco_ipv4_da_aplicacao():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "127.0.0.1:8000" in texto
    assert "localhost:8000" not in texto


def test_reproducao_separa_dependencia_da_aplicacao_da_do_rf09():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "### Para a aplicação" in texto
    assert "### Para reproduzir a automação" in texto
    assert re.search(r"n8n \*\*não é\s*\n?dependência\*\*", texto)


def test_reproducao_nao_apresenta_node_como_versao_minima():
    texto = REPRODUCAO.read_text(encoding="utf-8")

    assert "24.19.0" in texto
    assert re.search(r"versões testadas, não versões mínimas", texto)
