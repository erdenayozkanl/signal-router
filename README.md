# SignalRouter — Explainable LLM Router

Model-selection policy engine with complexity classification, basic PII detection, privacy-aware routing, illustrative cost budgets, a circuit-breaker primitive, optional Ollama inference, a **safe simulation mode** and HTTP API.

## Quick start (Python 3.11+)

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py "Analyze the tradeoffs of microservice caching" --simulate
python main.py "How do I cache data?" --simulate
python main.py --serve
# POST http://127.0.0.1:8003/route {"prompt":"Explain rate limiting","simulate":true}
pytest -q
```

Container API: `docker compose up --build` (port 8003). The router supplies in-process sliding-window rate limiting, failover orchestration and latency metrics primitives; use provider adapters and a shared store for a distributed deployment.

**Simulation:** immediate, no external services or actual model output; `output` is null. This tests routing choices rather than fabricated answers.

## Real local generation

Install Ollama and run `ollama pull llama3.2:3b` and `ollama pull llama3.1:8b`. With Ollama running, `python main.py "Explain caching"` performs actual local inference. Different hardware may need smaller models; override `OLLAMA_SMALL_MODEL` and `OLLAMA_LARGE_MODEL`. Running large models consumes RAM.

## Important boundaries

- `cloud-*` is a **routing decision only**; cloud provider execution is deliberately unimplemented and fails explicitly.
- Costs are illustrative coefficients, **not current provider prices**, and tokens are roughly estimated.
- PII regexes are incomplete and must never be treated as comprehensive DLP.
- The circuit breaker is implemented and unit tested but **not wired into a persistent distributed gateway**.
- The classifier is an explainable heuristic, not an ML model or learned router.

## Production extension

Implement real multi-provider adapters, retry/failover with backoff and idempotency, telemetry (TTFB, p50/p95, spend), policy versioning, durable budgets, an evaluated routing dataset, load tests, tenant authorization, guardrails and golden tests. This starter is deliberately explicit about the capabilities it does and does not provide.
