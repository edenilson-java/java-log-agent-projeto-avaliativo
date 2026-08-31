from typing import Any

from langchain_core.runnables import RunnableConfig

from src.schemas import DiagnosticReport


class FakeLLM:
    """
    LLM determinístico para testes, injetado por create_graph(llm=...).

    Implementa o contrato usado em produção:
    with_structured_output(schema) seguido de invoke(messages).
    """

    def __init__(
        self,
        should_fail: bool = False,
        invalid_output: bool = False,
    ):
        self.should_fail = should_fail
        self.invalid_output = invalid_output

    def with_structured_output(self, schema):
        return self

    def invoke(
        self,
        input_data: Any,
        config: RunnableConfig | None = None,
    ) -> Any:
        if self.should_fail:
            raise ValueError("Simulated LLM API failure")

        if self.invalid_output:
            class FakeResult:
                def model_dump(self):
                    return {"wrong_field": "This should fail validation"}

            return FakeResult()

        return DiagnosticReport(
            summary="Fake LLM diagnostic summary",
            probable_cause="Fake LLM probable cause",
            severity="high",
            category="Code",
            exception="FakeException",
            evidence=["Fake evidence 1"],
            recommendations=["Fake recommendation 1"],
            diagnostic_mode="llm",
        )
