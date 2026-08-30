import pytest
from pydantic import SecretStr, ValidationError

from src.config import AppConfig, load_config

# Ambiente vazio: a configuração precisa carregar inteira só com os padrões.
SEM_AMBIENTE: dict[str, str] = {}


# --------------------------------------------------------- padrões e carga


def test_carrega_sem_nenhuma_variavel_de_ambiente():
    config = load_config(SEM_AMBIENTE)

    assert config.openai_api_key is None
    assert config.has_openai_key is False
    assert config.openai_model == "gpt-4o-mini"
    assert config.max_steps == 32


def test_valores_do_ambiente_sobrepoem_os_padroes():
    config = load_config({"OPENAI_MODEL": "gpt-4o", "MAX_STEPS": "8"})

    assert config.openai_model == "gpt-4o"
    assert config.max_steps == 8


def test_variavel_vazia_equivale_a_ausente():
    config = load_config({"OPENAI_MODEL": "   ", "OPENAI_API_KEY": "  "})

    assert config.openai_model == "gpt-4o-mini"
    assert config.has_openai_key is False


def test_espacos_em_torno_do_valor_sao_removidos():
    config = load_config({"OPENAI_MODEL": "  gpt-4o  "})

    assert config.openai_model == "gpt-4o"


# ------------------------------------------------------ a chave não vaza


def test_chave_fica_encapsulada_e_nao_aparece_na_representacao():
    valor = "sk" + "-teste-" + "0123456789abcdef"
    config = load_config({"OPENAI_API_KEY": valor})

    assert config.has_openai_key is True
    assert valor not in repr(config)
    assert valor not in str(config)
    assert valor not in str(config.model_dump())
    # O valor só sai por chamada explícita.
    assert config.openai_api_key.get_secret_value() == valor


def test_chave_so_de_espacos_nao_conta_como_chave():
    config = AppConfig(openai_api_key=SecretStr("   "))

    assert config.has_openai_key is False


# ---------------------------------------------------- contrato do modelo


def test_modelo_e_imutavel():
    config = load_config(SEM_AMBIENTE)

    with pytest.raises(ValidationError):
        config.openai_model = "outro"


def test_campo_desconhecido_e_recusado():
    # Erro de digitação em variável de ambiente falha na carga, não silenciosamente.
    with pytest.raises(ValidationError):
        AppConfig(openai_modelo="gpt-4o")


def test_modelo_vazio_e_recusado():
    with pytest.raises(ValidationError):
        AppConfig(openai_model="   ")


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("max_steps", 0),
        ("max_steps", 257),
        ("max_log_size_bytes", 0),
        ("max_log_size_bytes", 10_000_001),
        ("llm_timeout_seconds", 0),
        ("llm_timeout_seconds", 121),
    ],
)
def test_limites_numericos_fora_da_faixa_sao_recusados(campo, valor):
    with pytest.raises(ValidationError):
        AppConfig(**{campo: valor})


def test_temperatura_e_tentativas_sao_fixas():
    config = load_config(SEM_AMBIENTE)

    assert config.llm_temperature == 0
    assert config.max_llm_attempts == 1


# ------------------------------------------------------------- caminhos


def test_caminhos_sao_absolutos_e_normalizados():
    config = load_config(SEM_AMBIENTE)

    for caminho in (config.allowed_log_root, config.output_root,
                    config.app_log_path, config.audit_log_path):
        assert caminho.is_absolute()
        assert ".." not in caminho.parts


def test_sinais_seguem_a_raiz_de_saida_declarada(tmp_path):
    config = load_config({"OUTPUT_ROOT": str(tmp_path)})

    assert config.output_root == tmp_path.resolve()
    assert config.app_log_path == (tmp_path / "agent-events.jsonl").resolve()
    assert config.audit_log_path == (tmp_path / "agent-audit.jsonl").resolve()


def test_caminho_de_sinal_pode_ser_apontado_isoladamente(tmp_path):
    destino = tmp_path / "outro" / "eventos.jsonl"
    config = load_config({"APP_LOG_PATH": str(destino)})

    assert config.app_log_path == destino.resolve()
