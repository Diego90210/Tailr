"""SPIKE-03: structured-output reliability.

20 real prompts through `openai/gpt-oss-120b` strict JSON-schema mode,
validated with pydantic. Gate: failure rate > 5% ⇒ repair step or change model.

Usage: python scripts/spike03_structured.py
Report: scripts/spike_output/spike03_report.json
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spike02_groq import JDAnalysis, JD_SCHEMA, OUT, chat  # noqa: E402

GAP_S = 6.0  # ~10 calls/min * ~900 tok ≈ 8K TPM ceiling; 429 retry as backstop


def posting_text() -> str:
    """20 synthetic-but-real postings: ES/EN, all seniorities, varied shapes."""
    posts = [
        # 1 — EN senior frontend (the SPIKE-02 sample, kept as baseline)
        "Senior Frontend Engineer (Madrid, hybrid, 3 days on-site). Must: 5+ years TypeScript, React, Next.js, Vitest, GitHub Actions CI/CD. Nice: next-intl i18n, Tailwind, WCAG 2.2. English C1.",
        # 2 — ES junior fullstack
        "Buscamos Full-Stack Junior para startup de logistica en Valencia. Requisitos: 1-2 anios con Node.js y React, conocimientos de SQL. Se valora practicas previas. Jornada completa, presencial.",
        # 3 — very short
        "Backend dev, Go, remote EU, senior. Salary 70-85k.",
        # 4 — bullet-heavy, messy
        "JOB DESCRIPTION\n- Python\n- Kubernetes\n- Terraform\n- 4+ years\n- On-call rotation\n- Nice: AWS, Helm\n- English: full professional\n- Salary: 55k-70k EUR",
        # 5 — ES with accents + tables feel
        "Ingeniero/a de Datos (híbrido, Barcelona). Experiencia mínima de 3 años en ETL con dbt y Python. Domina SQL avanzado y modelado dimensional. Deseable: experiencia con BigQuery y orquestación con Airflow. Inglés B2.",
        # 6 — mid mobile
        "Mobile Engineer (Flutter) - Remote LatAm. 3 years mobile, Dart, REST integrations, store releases (Play/App Store). Nice: CI with Fastlane, offline-first architecture. English working level.",
        # 7 — lead with management flavour
        "Engineering Lead - Fintech, Berlin or remote DE. Must: 7+ years backend (Java/Spring or Kotlin), led teams of 4-8, event-driven architecture (Kafka), mentoring, stakeholder comms. Nice: payments domain, PCI-DSS. German not required.",
        # 8 — long rambling posting
        "We are a fast-growing scale-up in the health-tech space looking for a versatile Software Engineer to join our growing platform team. You will work closely with product designers, data scientists and fellow engineers to deliver features end to end. Our stack is TypeScript across the board: Node.js services, React frontends, PostgreSQL, Redis, and a sprinkle of GraphQL. We practice trunk-based development, keep our CI green, and hold ourselves to high standards of testing and observability. On the people side, we run blameless postmortems, generous learning budgets and a genuinely flexible hybrid setup (2 office days per week in Rotterdam). Requirements: 4+ years professional software engineering, strong TypeScript, production experience with relational databases, comfort with containerized deployments. Bonus points: Kubernetes, Terraform, prior fintech or health-tech exposure, experience with GDPR-sensitive data. Compensation: 65-80k EUR plus equity.",
        # 9 — ES, short, mid data analyst
        "Analista de Datos Junior/Mid - Madrid, presencial. SQL, Power BI, Python básico. 2 años de experiencia. Sector retail.",
        # 10 — QA/SDET
        "SDET - Remote (UK timezone overlap). Must: 5+ years in test automation, Playwright or Cypress, TypeScript, API testing with REST, CI pipelines. Nice: performance testing (k6), security testing basics, BDD with Cucumber.",
        # 11 — platform/SRE
        "Plataforma / SRE en Madrid (hibrido). 5+ anos con Linux, Kubernetes en produccion, Prometheus/Grafana, scripting Bash o Python. Turno de guardia rotativo. Deseable experiencia con GCP y IaC con Terraform.",
        # 12 — very senior staff, dense
        "Staff Software Engineer, Distributed Systems. Requirements: 10+ years building high-throughput low-latency services; deep expertise in Go or Rust; distributed consensus and replication (Raft/Paxos); storage engines (LSM trees, RocksDB); profiling and capacity planning; experience mentoring senior engineers and leading cross-team technical design reviews; publications or open-source contributions valued.",
        # 13 — EN junior with typo-ish noise
        "junor front-end role, react + typescript, we are a small agency in Lisbon doing e-commerce projects. you will build component libraries and maintain existing clients sites. 1-2 yrs exp ok. portugese nice to have, english required.",
        # 14 — ES marketing-flavoured tech
        "Desarrollador/a WordPress con PHP para agencia de marketing digital en Sevilla. Imprescindible: PHP 8, WooCommerce, Git y conocimientos de SEO técnico. Deseable: experiencia con Elementor y optimización de Core Web Vitals. Contrato indefinido, híbrido 2 días.",
        # 15 — data engineer EN
        "Data Engineer (Mid/Senior) - Remote EU. Must: 4+ years Python, SQL at scale, building and maintaining batch & streaming pipelines (Spark or Flink), dbt, data quality tests, cloud (AWS or GCP). Nice: Iceberg/Delta Lake, Kafka, Airflow orchestration, Sigma in analytics culture.",
        # 16 — odd format: Q&A style
        "Who we are: climate startup, 30 people, Amsterdam.\nWhat you'll do: own our billing service end to end.\nWhat you need: 5+ yrs Java or Kotlin, Postgres, event-driven systems, curiosity about the energy market.\nWhat is nice: Spring Boot, refunds logic, Stripe.",
        # 17 — ES senior backend con requisitos de seguridad
        "Senior Backend Engineer (Java) - Remoto España. Experiencia mínima de 6 años en Java 17 y Spring Boot, diseño de APIs REST y gRPC, PostgreSQL y Kafka. Seguridad: OAuth2/OIDC y buenas prácticas OWASP. Metodología Scrum, inglés B2 para reuniones con equipo internacional.",
        # 18 — ecommerce mid fullstack
        "Full-Stack Engineer (Mid) at an e-commerce company in Amsterdam. React + Node.js, GraphQL, MongoDB, AWS. 3+ years shipping features across the stack. Nice: A/B testing, performance optimisation, Shopify ecosystem.",
        # 19 — tiny, underspecified
        "Need a dev. C# and SQL. Office in Porto, 3 days/week. Mid level.",
        # 20 — ES lead devops, long bullet mix
        "Lead DevOps Engineer (remoto España/B Portugal). 6+ años gestionando infraestructura en la nube (AWS obligatorio), experiencia liderando equipos pequeños, definición de estrategias de CI/CD con GitHub Actions o GitLab CI, IaC con Terraform, seguridad de la cadena de suministro (SBOM, escaneo de imágenes). Deseable: certificación AWS Solutions Architect, experiencia en entornos regulados (ISO 27001). Oferta: 75-90k + variable.",
    ]
    assert len(posts) == 20, len(posts)
    return posts


def strict_rf():
    return {
        "type": "json_schema",
        "json_schema": {"name": "jd_analysis", "strict": True, "schema": JD_SCHEMA},
    }


def one_call(text: str) -> dict:
    for attempt in range(3):
        r, meta, latency = chat(
            [
                {"role": "system", "content": "You extract job-posting analysis data."},
                {"role": "user", "content": text},
            ],
            response_format=strict_rf(),
            max_tokens=1000,  # gpt-oss burns ~230 reasoning tokens before the JSON; 400 truncated it
        )
        if r.status_code != 429:
            break
        time.sleep(float(r.headers.get("retry-after") or 5))
    row = {"status": r.status_code, "latency_s": round(latency, 3)}
    if r.status_code != 200:
        row["error"] = r.text[:300]
        row["valid"] = False
        return row
    content = r.json()["choices"][0]["message"]["content"]
    try:
        JDAnalysis.model_validate_json(content)
        row["valid"] = True
    except Exception as e:  # pydantic ValidationError — the metric we're measuring
        row["valid"] = False
        row["error"] = str(e)[:400]
    usage = r.json().get("usage", {})
    row["total_tokens"] = usage.get("total_tokens")
    row["reasoning_tokens"] = usage.get("completion_tokens_details", {}).get("reasoning_tokens")
    return row


def main():
    rows = []
    for i, text in enumerate(posting_text()):
        row = one_call(text)
        row["i"] = i
        rows.append(row)
        print(f"[{i:02d}] {'OK  ' if row['valid'] else 'FAIL'} status={row['status']} {row['latency_s']}s tok={row.get('total_tokens')}")
        time.sleep(GAP_S)

    failures = [r for r in rows if not r["valid"]]
    http_errors = [r for r in rows if r["status"] != 200]
    rate = len(failures) / len(rows)
    report = {
        "model": "openai/gpt-oss-120b",
        "mode": "strict json_schema",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "calls": len(rows),
        "schema_failures": len(failures),
        "http_errors": len(http_errors),
        "failure_rate": rate,
        "gate_5pct": "PASS" if rate <= 0.05 else "FAIL",
        "latency_s": {
            "min": min(r["latency_s"] for r in rows),
            "max": max(r["latency_s"] for r in rows),
            "avg": round(sum(r["latency_s"] for r in rows) / len(rows), 3),
        },
        "tokens_avg": round(sum(r.get("total_tokens") or 0 for r in rows) / len(rows)),
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "spike03_report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    print(f"report -> {path}")
    assert not http_errors, f"transport errors: {http_errors}"


if __name__ == "__main__":
    main()
