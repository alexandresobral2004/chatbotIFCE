"""Guarda de arquitetura: a regra de dependência (interno não importa externo) não pode regredir."""
import ast
import asyncio
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FORBIDDEN_IN_CORE = ("adapters", "typesafe_sdk")  # o core fala com portas, nunca com adapters nem SDKs
COMPOSITION_ROOT_DIRS = {"di"}                       # pode escolher adapters

# Débitos conhecidos: arquivos do core que ainda importam adapters. Deve ficar vazio; NÃO adicione
# arquivos novos aqui, corrija a dependência (porta em ports/ + adapter que a implementa).
KNOWN_DEBT: set = set()


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_core_never_imports_adapters_or_vendor_sdks():
    offenders = []
    for path in (BACKEND / "core").rglob("*.py"):
        if COMPOSITION_ROOT_DIRS & set(path.relative_to(BACKEND / "core").parts):
            continue
        if str(path.relative_to(BACKEND)) in KNOWN_DEBT:
            continue
        for module in _imports(path):
            if module.split(".")[0] in FORBIDDEN_IN_CORE:
                offenders.append(f"{path.relative_to(BACKEND)} importa {module}")
    assert not offenders, "o core depende de adapters/SDKs:\n  " + "\n  ".join(offenders)


def test_typesafe_adapter_translates_port_questions_to_sdk_questions(monkeypatch):
    from types import SimpleNamespace

    from adapters.typesafe_adapter import TypeSafeAdapter
    from ports.judge_port import JudgePort, YesNoQuestion

    captured = {}

    async def fake_judge(self, state, questions):
        captured["state"], captured["questions"] = state, questions
        return SimpleNamespace(nouls={qid: SimpleNamespace(noul=0.75) for qid in questions})

    monkeypatch.setattr(TypeSafeAdapter, "judge", fake_judge)
    adapter = TypeSafeAdapter(api_key="chave-de-teste")
    assert isinstance(adapter, JudgePort) and adapter.is_configured

    result = asyncio.run(adapter.probabilities(
        {"x": 1},
        {
            "com_criterio": YesNoQuestion("A é verdadeira?", if_true="sim significa A", if_false="não significa B"),
            "sem_criterio": YesNoQuestion("B é verdadeira?"),
        },
    ))

    assert result == {"com_criterio": 0.75, "sem_criterio": 0.75}
    assert captured["state"] == {"x": 1}
    with_criteria = captured["questions"]["com_criterio"]
    assert with_criteria.instructions == "A é verdadeira?"
    assert dict(with_criteria.criteria) == {"true": "sim significa A", "false": "não significa B"}
    assert captured["questions"]["sem_criterio"].criteria is None
