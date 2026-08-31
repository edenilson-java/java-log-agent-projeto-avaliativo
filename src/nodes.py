from pathlib import Path
from time import perf_counter
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from src.config import load_config
from src.observability import emit_signals
from src.schemas import DiagnosticReport
from src.security import (
    contains_secret,
    evaluate_policy,
    redact_sensitive_text,
    sanitize_memory_context,
    sanitize_untrusted_content,
)
from src.state import AgentState
from src.tools import extract_log_events, read_log_file, write_diagnostic_report
from src.validation import validate_log_file

# Mensagens literais dos nós de controle acrescentados pela evolução.
LIMITE_MENSAGEM = (
    "Limite de passos atingido; execução encerrada de forma controlada."
)
CANCELAMENTO_MENSAGEM = (
    "Execução cancelada antes de qualquer leitura ou chamada externa."
)

# Usada quando o diagnóstico chega ausente ou inválido sem que a etapa
# anterior tenha reportado causa.
CAUSA_FALLBACK_PADRAO = (
    "Diagnóstico ausente ou inválido; a integração não reportou causa."
)

DIAGNOSTIC_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "Você é um especialista em Java e Spring Boot. Analise os erros "
            "extraídos do log e forneça um diagnóstico estruturado."
        ),
    ),
    (
        "user",
        (
            "Categoria Preliminar: {category}\n\n"
            "Evidências extraídas:\n{context_text}\n\n"
            "Forneça um diagnóstico detalhado."
        ),
    ),
])


def validar_entrada(state: AgentState) -> dict:
    """Valida o arquivo de log fornecido."""
    file_path = state.get("file_path", "")
    is_valid, errors = validate_log_file(file_path)

    if not is_valid:
        return {"validation_errors": errors}
    return {"validation_errors": []}


def gerar_resposta_erro(state: AgentState) -> dict:
    """Gera resposta de erro estruturada sem chamar ferramentas ou LLM."""
    errors = state.get("validation_errors", [])
    error_msg = state.get("error", "Erro de validação desconhecido.")

    if errors:
        error_msg = " | ".join(errors)

    return {
        "status": "error",
        "error": error_msg,
    }


def ler_log(state: AgentState) -> dict:
    """Lê o conteúdo do arquivo de log validado."""
    file_path = state.get("file_path")
    success, result = read_log_file(file_path)

    if not success:
        return {"error": result, "status": "error"}

    return {"log_content": result}


def extrair_eventos(state: AgentState) -> dict:
    """Extrai exceções e eventos relevantes do conteúdo do log."""
    log_content = state.get("log_content", "")

    if not log_content:
        return {
            "error": "Conteúdo do log vazio ou não lido.",
            "status": "error",
        }

    extracted = extract_log_events(log_content)

    # Coletar evidências (limitando para não exceder contexto)
    evidence = extracted["exceptions"][:5] + extracted["events"][:5]

    return {
        "exceptions": extracted["exceptions"],
        "extracted_events": extracted["events"],
        "evidence": evidence,
    }


def classificar_log(state: AgentState) -> dict:
    """Classifica o log com heurística determinística de categoria."""
    exceptions = state.get("exceptions", [])
    events = state.get("extracted_events", [])

    if exceptions or any("ERROR" in event for event in events):
        category = "Unknown"
        all_text = " ".join(exceptions + events).lower()

        if "sql" in all_text or "database" in all_text or "jdbc" in all_text:
            category = "Database"
        elif (
            "net" in all_text
            or "connection" in all_text
            or "timeout" in all_text
        ):
            category = "Network"
        elif (
            "bean" in all_text
            or "injection" in all_text
            or "context" in all_text
        ):
            category = "Configuration"
        elif "nullpointer" in all_text or "indexoutofbounds" in all_text:
            category = "Code"

        return {"category": category}

    return {"category": "Clean"}


def gerar_resultado_sem_erros(state: AgentState) -> dict:
    """Gera um relatório padrão para logs sem erros relevantes."""
    file_path = state.get("file_path", "unknown")
    filename = Path(file_path).name if file_path else "unknown"

    diagnostic_dict = {
        "summary": "Nenhum erro relevante encontrado.",
        "probable_cause": "N/A",
        "severity": "low",
        "category": "Clean",
        "exception": None,
        "evidence": [
            "Nenhum evento de erro ou exceção foi detectado nas extrações."
        ],
        "recommendations": ["Continuar monitorando a aplicação."],
        "diagnostic_mode": "deterministic",
    }

    try:
        validated_diagnostic = DiagnosticReport(**diagnostic_dict)
        diagnostic = validated_diagnostic.model_dump()
    except ValidationError as exc:
        return {
            "error": f"Erro de validação Pydantic: {exc}",
            "status": "error",
        }

    return {
        "status": "success_no_errors",
        "diagnostic": diagnostic,
        "report_path": f"report_{filename}",
    }


def make_diagnosticar(llm=None):
    """
    Cria o nó de diagnóstico com o LLM injetado como dependência.

    Sem LLM fornecido, constrói um `ChatOpenAI` parametrizado pela
    configuração.
    """

    def diagnosticar(state: AgentState) -> dict:
        """Única chamada ao LLM: gera o diagnóstico estruturado."""
        category = state.get("category", "Unknown")
        evidence = state.get("evidence", [])

        context_text = "\n".join(evidence)

        # O contexto recuperado da execução anterior desta mesma thread entra
        # como texto adicional, não como um template diferente: o prompt
        # herdado da baseline continua byte a byte o mesmo. Na primeira
        # execução da thread o bloco é vazio e nada muda.
        bloco_memoria = formatar_memoria_para_prompt(
            state.get("memory_context")
        )
        if bloco_memoria:
            context_text = f"{context_text}\n\n{bloco_memoria}"

        # O limite protege a tentativa, não o sucesso: por isso é contada antes.
        tentativas = state.get("llm_attempts", 0) + 1

        try:
            model = llm
            if model is None:
                config = load_config()
                if not config.has_openai_key:
                    raise ValueError("OPENAI_API_KEY não configurada.")
                model = ChatOpenAI(
                    model=config.openai_model,
                    temperature=config.llm_temperature,
                    timeout=config.llm_timeout_seconds,
                    max_retries=0,
                )

            messages = DIAGNOSTIC_PROMPT.invoke({
                "category": category,
                "context_text": context_text,
            })
            structured_llm = model.with_structured_output(DiagnosticReport)
            result = structured_llm.invoke(messages)

            diag_dict = result.model_dump()
            diag_dict["diagnostic_mode"] = "llm"

            return {"diagnostic": diag_dict, "llm_attempts": tentativas}
        except Exception as exc:  # noqa: BLE001 - fronteira do LLM
            return {
                "error": f"Falha na geração do diagnóstico com LLM: {exc}",
                "llm_attempts": tentativas,
            }

    return diagnosticar


def validar_saida(state: AgentState) -> dict:
    """Valida se o diagnóstico foi gerado corretamente."""
    diagnostic = state.get("diagnostic")
    error = state.get("error")

    if error or not diagnostic:
        return {"status": "invalid_output"}

    try:
        DiagnosticReport(**diagnostic)
        return {"status": "success"}
    except ValidationError as exc:
        return {
            "error": f"Erro de validação Pydantic: {exc}",
            "status": "invalid_output",
        }


def tratar_saida_invalida(state: AgentState) -> dict:
    """
    Fallback determinístico quando o LLM falha ou a saída é inválida.

    O `error` público é zerado — o fallback é um desfecho de sucesso —, e a
    causa técnica segue em `fallback_reason`, de onde os sinais a leem.
    """
    causa = (
        state.get("error")
        or state.get("fallback_reason")
        or CAUSA_FALLBACK_PADRAO
    )
    exceptions = state.get("exceptions", [])
    evidence = state.get("evidence", [])
    category = state.get("category", "Unknown")

    main_exception = exceptions[0] if exceptions else "Unknown Exception"

    diagnostic = {
        "summary": (
            "Diagnóstico gerado em modo fallback devido a falha na IA "
            "ou ausência de chave."
        ),
        "probable_cause": f"Exceção principal detectada: {main_exception}",
        "severity": "high" if exceptions else "medium",
        "category": category,
        "exception": main_exception,
        "evidence": evidence if evidence else [
            "Nenhuma evidência clara extraída."
        ],
        "recommendations": [
            "Verificar a stack trace completa no arquivo de log original.",
            "Configurar chave de API válida para diagnóstico avançado com IA.",
        ],
        "diagnostic_mode": "fallback",
    }

    return {
        "status": "success_fallback",
        "diagnostic": diagnostic,
        "error": "",
        "fallback_reason": causa,
    }


def escrever_relatorio(state: AgentState) -> dict:
    """Escreve o relatório Markdown usando a ferramenta segura."""
    diagnostic = state.get("diagnostic")
    file_path = state.get("file_path", "unknown.log")
    filename = Path(file_path).name

    if not diagnostic:
        return {
            "error": "Nenhum diagnóstico disponível para gerar relatório.",
            "status": "error",
        }

    md_content = f"# Relatório de Diagnóstico: {filename}\n\n"
    md_content += (
        f"**Modo de Diagnóstico:** "
        f"{diagnostic.get('diagnostic_mode', 'unknown')}\n"
    )
    md_content += f"**Status:** {state.get('status', 'unknown')}\n\n"

    md_content += f"## Resumo\n{diagnostic.get('summary', '')}\n\n"
    md_content += "## Detalhes\n"
    md_content += f"- **Categoria:** {diagnostic.get('category', '')}\n"
    md_content += f"- **Severidade:** {diagnostic.get('severity', '')}\n"
    md_content += (
        f"- **Exceção Principal:** {diagnostic.get('exception', '')}\n\n"
    )

    md_content += f"## Causa Provável\n{diagnostic.get('probable_cause', '')}\n\n"

    md_content += "## Evidências\n"
    for ev in diagnostic.get("evidence", []):
        md_content += f"- `{ev}`\n"
    md_content += "\n"

    md_content += "## Recomendações\n"
    for rec in diagnostic.get("recommendations", []):
        md_content += f"- {rec}\n"

    report_filename = f"report_{filename}"

    success, result = write_diagnostic_report(report_filename, md_content)

    if not success:
        return {"error": result, "status": "error"}

    return {"report_path": result}


# ---------------------------------------------------------------------------
# Nós de controle acrescentados pela evolução (E02).
#
# O mini-projeto entrava direto na validação. A evolução abre e fecha a
# execução por nós próprios, o que dá três coisas que o fluxo original não
# tinha: identificadores de correlação, contagem de passos e um ponto único
# de término por onde TODAS as rotas passam.
# ---------------------------------------------------------------------------


def inicializar_execucao(state: AgentState) -> dict:
    """
    Abre a execução: correlação, marco de tempo e contagem de passos.

    Os identificadores só são gerados se ainda não existirem, para que uma
    chamada vinda da API ou do MCP possa impor os seus.
    """
    return {
        "correlation_id": state.get("correlation_id") or str(uuid4()),
        "audit_id": state.get("audit_id") or str(uuid4()),
        "started_at": state.get("started_at") or perf_counter(),
        "current_step": state.get("current_step", 0) + 1,
        "llm_attempts": state.get("llm_attempts", 0),
        "status": "running",
        "node_history": ["inicializar_execucao"],
    }


def cancelar_execucao(state: AgentState) -> dict:
    """Encerra a pedido, antes de ler arquivo ou chamar qualquer serviço."""
    return {
        "status": "cancelled",
        "error": CANCELAMENTO_MENSAGEM,
        "blocked_reason": "cancel_requested",
        "node_history": ["cancelar_execucao"],
    }


def gerar_resposta_limite(state: AgentState) -> dict:
    """Encerra por limite de passos, evitando execução indefinida."""
    return {
        "status": "error",
        "error": LIMITE_MENSAGEM,
        "blocked_reason": "max_steps",
        "node_history": ["gerar_resposta_limite"],
    }


def finalizar_execucao(state: AgentState) -> dict:
    """
    Ponto único de término, por onde passam todas as rotas.

    Calcula a latência, grava a memória da thread e emite os dois sinais.
    Não altera o status: quem decide o desfecho é o nó anterior.
    """
    started_at = state.get("started_at")
    latencia = (
        (perf_counter() - started_at) * 1000.0
        if isinstance(started_at, (int, float))
        else 0.0
    )
    saida = {
        "latency_ms": round(latencia, 3),
        "memory_context": build_memory_context(state),
        "node_history": ["finalizar_execucao"],
    }

    # A latência já calculada entra nos sinais desta mesma execução.
    erros = emit_signals({**state, **saida})
    if erros:
        saida["observability_errors"] = [
            *state.get("observability_errors", []),
            *erros,
        ]
    return saida


# ---------------------------------------------------------------------------
# Branches paralelas e ponto de junção (E02).
#
# As duas análises partem do mesmo conteúdo e não se enxergam. Cada uma
# escreve a própria contribuição em `parallel_findings`, campo anotado com
# reducer — sem ele o LangGraph recusaria a escrita concorrente.
# ---------------------------------------------------------------------------


def analisar_excecoes(state: AgentState) -> dict:
    """Branch paralela: extrai as exceções Java do conteúdo lido."""
    log_content = state.get("log_content", "")
    exceptions = extract_log_events(log_content)["exceptions"]
    return {
        "exceptions": exceptions,
        "parallel_findings": [
            {"source": "excecoes", "findings": exceptions},
        ],
        "node_history": ["analisar_excecoes"],
    }


def analisar_eventos(state: AgentState) -> dict:
    """Branch paralela: extrai as linhas ERROR e WARN do conteúdo lido."""
    log_content = state.get("log_content", "")
    events = extract_log_events(log_content)["events"]
    return {
        "extracted_events": events,
        "parallel_findings": [
            {"source": "eventos", "findings": events},
        ],
        "node_history": ["analisar_eventos"],
    }


def consolidar_analises(state: AgentState) -> dict:
    """
    Fan-in: reúne as duas contribuições, monta as evidências e classifica.

    A classificação reaproveita `classificar_log`, herdada do mini-projeto,
    em vez de reimplementar a heurística.
    """
    por_origem = {
        item["source"]: item["findings"]
        for item in state.get("parallel_findings", [])
    }
    exceptions = por_origem.get("excecoes", [])
    events = por_origem.get("eventos", [])

    # Mesmo recorte de evidências do mini-projeto: até 5 de cada origem.
    evidence = exceptions[:5] + events[:5]

    categoria = classificar_log(
        {"exceptions": exceptions, "extracted_events": events}
    )

    return {
        "evidence": evidence,
        "category": categoria["category"],
        "node_history": ["consolidar_analises"],
    }


# ---------------------------------------------------------------------------
# Memória curta por thread (E04).
#
# O que atravessa duas invocações da mesma thread é um resumo pequeno e
# fechado — categoria, resumo, status e no máximo duas evidências truncadas —,
# nunca o estado inteiro. O log bruto e a stack trace completa ficam de fora
# por decisão, não por esquecimento: o que não é reaproveitado não pode vazar
# para um prompt, e um limite fixo impede que o contexto cresça a cada
# execução até dominar a janela do modelo.
# ---------------------------------------------------------------------------

MEMORY_MAX_EVIDENCIAS = 2
MEMORY_EVIDENCIA_MAX_CARACTERES = 160
MEMORY_RESUMO_MAX_CARACTERES = 240
MEMORY_TRUNCAMENTO_SUFIXO = "..."


def truncar_para_memoria(texto: object, limite: int) -> str:
    """
    Reduz um texto ao limite, contando o sufixo dentro do orçamento.

    O sufixo entra no total: um limite de 160 devolve no máximo 160
    caracteres, e não 163. Espaços em branco repetidos são colapsados antes
    da contagem, para que uma stack trace indentada não gaste o orçamento com
    recuo.
    """
    normalizado = " ".join(str(texto).split())
    if len(normalizado) <= limite:
        return normalizado

    corte = max(limite - len(MEMORY_TRUNCAMENTO_SUFIXO), 0)
    return normalizado[:corte] + MEMORY_TRUNCAMENTO_SUFIXO


def build_memory_context(state: AgentState) -> dict:
    """
    Monta o contexto que a próxima execução da mesma thread poderá recuperar.

    O resumo vem do diagnóstico quando existe; nas rotas que terminam sem
    diagnóstico — erro, cancelamento, bloqueio — vem da mensagem de erro, de
    modo que a thread também se lembre de ter falhado.
    """
    diagnostic = state.get("diagnostic") or {}
    resumo = diagnostic.get("summary") or state.get("error") or ""
    evidencias_brutas = list(state.get("evidence") or [])

    return {
        "category": state.get("category") or "Unknown",
        "summary": truncar_para_memoria(resumo, MEMORY_RESUMO_MAX_CARACTERES),
        "status": state.get("status") or "unknown",
        "evidence": [
            truncar_para_memoria(item, MEMORY_EVIDENCIA_MAX_CARACTERES)
            for item in evidencias_brutas[:MEMORY_MAX_EVIDENCIAS]
        ],
    }


def formatar_memoria_para_prompt(memory_context: dict | None) -> str:
    """
    Converte o contexto recuperado em texto para o prompt de diagnóstico.

    Devolve string vazia quando não há memória — é a primeira execução da
    thread. Assim o prompt da primeira invocação continua idêntico ao da
    baseline, e o contexto só aparece quando de fato foi recuperado.
    """
    if not memory_context:
        return ""

    linhas = [
        "Contexto recuperado da execução anterior desta mesma thread:",
        f"- Categoria anterior: {memory_context.get('category', 'Unknown')}",
        f"- Status anterior: {memory_context.get('status', 'unknown')}",
        f"- Resumo anterior: {memory_context.get('summary', '')}",
    ]
    linhas.extend(
        f"- Evidência anterior: {item}"
        for item in memory_context.get("evidence", [])
    )
    return "\n".join(linhas)


# Governança e limites de autonomia.


def verificar_seguranca(state: AgentState) -> dict:
    """Aplica a política e redige os dados que seguem adiante.
    Conteúdo hostil encerra o fluxo sem modelo nem escrita."""
    conteudo = state.get("log_content", "")
    decisao = evaluate_policy(conteudo)

    # Redige todos os campos derivados antes de expor o estado.
    campos_derivados = ("evidence", "exceptions", "extracted_events")
    redigidos = {
        campo: [redact_sensitive_text(item) for item in state.get(campo, [])]
        for campo in campos_derivados
    }
    conteudo_seguro = sanitize_untrusted_content(conteudo)
    memoria = sanitize_memory_context(state.get("memory_context"))
    achados = [
        {
            "source": item["source"],
            "findings": [redact_sensitive_text(f) for f in item["findings"]],
        }
        for item in state.get("parallel_findings", [])
    ]

    houve_redacao = (
        contains_secret(conteudo)
        or any(redigidos[c] != list(state.get(c, [])) for c in campos_derivados)
        or memoria != state.get("memory_context")
    )

    saida: dict = {
        **redigidos,
        "log_content": conteudo_seguro,
        "parallel_findings": achados,
        "security_flags": list(decisao.flags),
        "requires_human": decisao.requires_human,
        "redacted": houve_redacao,
        "node_history": ["verificar_seguranca"],
    }
    if memoria is not None:
        saida["memory_context"] = memoria

    if not decisao.allowed:
        saida["status"] = "blocked"
        saida["blocked_reason"] = ",".join(decisao.flags)
        saida["error"] = decisao.message

    return saida
