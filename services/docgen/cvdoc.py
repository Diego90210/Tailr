"""SPIKE-01 core: content tree -> .docx / HTML replica fixtures for the fidelity comparison.

ponytail: this exists to answer one question (option A vs B fidelity). The production
builder lives in `builder.py`, the spec in `format_specs.py` and the measurement in
`measure.py`; this module re-exports them and keeps the HTML replica + fixture corpus
used by the spike comparison.
"""
from __future__ import annotations

from copy import deepcopy

from builder import build_docx
from format_specs import DEFAULT_FORMAT_SPEC
from measure import measure
from preview import build_html  # re-exported for run_spike.py; the replica lives in preview.py

# ---------------------------------------------------------------- fixtures

def _exp(company, role, start, end, *bullets):
    return {"company": company, "role": role, "start": start, "end": end,
            "bullets": [{"text": b, "factIds": ["fx"]} for b in bullets]}

def _proj(name, stack, url, *bullets):
    p = {"name": name, "bullets": [{"text": b, "factIds": ["fx"]} for b in bullets]}
    if stack:
        p["stack"] = stack
    if url:
        p["url"] = url
    return p

FIXTURES = {
    # 1 — short, early-career, ES. Target: clearly under one page.
    "01_junior_short": {
        "header": {"name": "Lucía Fernández",
                   "contactLine": "lucia.fernandez@mail.com · +34 600 111 222 · Madrid, ES"},
        "summary": "Técnica de soporte con 2 años de experiencia resolviendo incidencias "
                   "SaaS y documentando procesos para equipos de producto.",
        "experience": [
            _exp("Nubia Software", "Soporte técnico nivel 2", "2023", "actualidad",
                 "Resolviste el 85% de los tickets de primer nivel en menos de 4 horas.",
                 "Mantuviste la base de conocimiento con 40 artículos reutilizables."),
        ],
        "projects": [],
        "education": ["Grado Medio en Sistemas Informáticos, IES Clara Campoamor, 2022"],
        "certifications": [],
        "skills": ["SQL básico", "Jira", "Zendesk", "Linux"],
        "languages": ["Español (nativo)", "Inglés B2"],
    },
    # 2 — standard mid-level, EN. Target: comfortable one page.
    "02_mid_standard": {
        "header": {"name": "Daniel Ortega",
                   "contactLine": "daniel.ortega@mail.com · +1 415 555 0132 · Austin, TX"},
        "summary": "Backend engineer with 5 years building billing and payments services "
                   "in Go and Python, with a track record of reducing incident volume.",
        "experience": [
            _exp("Ledgerly", "Senior Backend Engineer", "2022", "present",
                 "Rebuilt the invoicing pipeline in Go, cutting p95 generation time from 6s to 800ms.",
                 "Led the migration of 14 cron jobs to a durable job queue with zero data loss.",
                 "Introduced structured on-call runbooks that reduced mean time to recovery by 35%."),
            _exp("Bluecart", "Backend Engineer", "2019", "2022",
                 "Built REST APIs in Python/Django serving 12M requests per day.",
                 "Owned the Postgres schema for orders; designed indexes that halved slow-query rate."),
        ],
        "projects": [
            _proj("invoice-diff", "Go, Postgres", "https://github.com/example/invoice-diff",
                  "CLI that diffs two billing runs and reports drift with fact-level provenance."),
        ],
        "education": ["B.S. Computer Science, UT Austin, 2019"],
        "certifications": ["AWS Certified Developer – Associate, 2021"],
        "skills": ["Go", "Python", "Postgres", "Django", "Kafka", "Docker", "Terraform"],
        "languages": ["English (native)", "Spanish (native)"],
    },
    # 3 — dense senior, EN. Target: near the 92-98% band (RF-14.2).
    "03_senior_full": {
        "header": {"name": "Mariana Costa",
                   "contactLine": "mariana.costa@mail.com · +55 11 99999 0000 · São Paulo, BR · "
                                  "linkedin.com/in/mcosta · github.com/mcosta"},
        "summary": "Staff frontend engineer specialising in design systems and performance, "
                   "8 years shipping product in TypeScript and React, with 3 years mentoring "
                   "small teams through migrations of large codebases.",
        "experience": [
            _exp("Olist", "Staff Frontend Engineer", "2022", "present",
                 "Led the rebuild of the merchant console (React 18, TypeScript), reducing "
                 "LCP from 4.1s to 1.6s for the top 5 merchant flows.",
                 "Designed the Atlas design system: 46 components, adopted by 7 squads, "
                 "cutting new-screen build time roughly in half.",
                 "Introduced visual regression tests in CI that blocked 31 layout bugs before production."),
            _exp("QuintoAndar", "Senior Frontend Engineer", "2019", "2022",
                 "Migrated a 620-file Flow codebase to TypeScript with incremental strictness, "
                 "zero rollbacks over 5 releases.",
                 "Built the pricing experiment framework used to run 24 A/B tests per quarter.",
                 "Mentored 4 engineers; two were promoted to senior within 18 months."),
            _exp("Gympass", "Frontend Engineer", "2017", "2019",
                 "Shipped the booking flow in React/Redux used by 1.2M monthly active users.",
                 "Cut bundle size 38% by code-splitting routes and replacing moment with date-fns."),
        ],
        "projects": [
            _proj("a11y-lint", "TypeScript, ESLint", "https://github.com/example/a11y-lint",
                  "ESLint plugin catching 19 accessibility regressions in JSX, used in 3 companies."),
            _proj("cv-engine", "Python, python-docx", None,
                  "Deterministic one-page CV generator with real font metrics for pagination."),
        ],
        "education": ["B.S. Information Systems, USP, 2016"],
        "certifications": ["Meta Front-End Developer Professional Certificate, 2021",
                           "Google Cloud Associate Cloud Engineer, 2023"],
        "skills": ["TypeScript", "React", "Next.js", "Design systems", "Performance",
                   "Accessibility", "Testing Library", "Playwright", "GraphQL", "Node.js"],
        "languages": ["Portuguese (native)", "English (fluent)", "Spanish (advanced)"],
    },
    # 4 — overfull, deliberately > 1 page. Target: the loop must compress (TR-FMT-1).
    "04_staff_overfull": {
        "header": {"name": "Aleksander Nowak",
                   "contactLine": "a.nowak@mail.com · +48 600 700 800 · Warsaw, PL · "
                                  "linkedin.com/in/anowak · github.com/anowak · nowak.dev"},
        "summary": "Platform engineer with 10 years across infrastructure, developer experience "
                   "and reliability. Comfortable owning systems from Terraform module to on-call "
                   "rotation, currently focused on internal developer platforms and cost control.",
        "experience": [
            _exp("Allegro", "Platform Lead", "2021", "present",
                 "Led a 6-person platform team serving 900 developers with a self-service "
                 "Kubernetes environment; median environment provisioning went from 3 days to 22 minutes.",
                 "Designed the golden-path CI templates adopted by 140 repositories, "
                 "reducing pipeline configuration drift to near zero.",
                 "Drove a FinOps programme that cut cloud spend 23% (~$1.4M/yr) without "
                 "dropping SLOs, by rightsizing stateful workloads and buying reserved capacity.",
                 "Introduced SLO-based alerting; pages per week fell from 41 to 9 across 5 services.",
                 "Ran the incident review practice for 18 months: 32 reviews, 71 actions, 92% closure rate."),
            _exp("CD Projekt", "Senior SRE", "2018", "2021",
                 "Owned edge and matchmaking infrastructure peaking at 1.9M concurrent users.",
                 "Built a load-test harness in Go that reproduced a 2020 launch incident and "
                 "validated the fix before relaunch.",
                 "Migrated 60 services from EC2 autoscaling groups to ECS with blue/green deploys.",
                 "Wrote the onboarding runbook still used to ramp new SREs in under 2 weeks."),
            _exp("Samsung R&D", "Software Engineer", "2015", "2018",
                 "Developed firmware update services in C++ for TV platform, 40M devices.",
                 "Automated release verification, removing 2 days of manual QA per release."),
        ],
        "projects": [
            _proj("k8s-cost-exporter", "Go, Prometheus", "https://github.com/example/k8s-cost-exporter",
                  "Exporter joining request and pricing data; adopted by 3 companies for showback.",
                  "Scrapes in under 400ms for 12k pods."),
            _proj("terraform-modules", "Terraform", None,
                  "Set of opinionated modules for VPC, EKS and RDS used as the org standard."),
            _proj("runbook-bot", "Python, Slack API", None,
                  "Slack bot paging the right rotation from alert annotations; 1.1k actions/month."),
        ],
        "education": ["M.Sc. Computer Science, Warsaw University of Technology, 2015",
                      "B.Sc. Computer Science, WUT, 2013"],
        "certifications": ["CKA – Certified Kubernetes Administrator, 2022",
                           "AWS Certified Solutions Architect – Professional, 2021",
                           "HashiCorp Terraform Associate, 2020"],
        "skills": ["Kubernetes", "Terraform", "Go", "Python", "AWS", "GCP", "Prometheus",
                   "Grafana", "ArgoCD", "Istio", "Postgres", "Redis", "Kafka", "Linux",
                   "Cost optimisation", "Incident management", "SLO design"],
        "languages": ["Polish (native)", "English (fluent)", "German (B1)"],
    },
    # 5 — ES, skills-heavy with long bullets. Target: sits just under the limit.
    "05_latam_es_ats": {
        "header": {"name": "Valentina Ríos",
                   "contactLine": "v.rios@mail.com · +52 55 1234 5678 · CDMX, MX · linkedin.com/in/vrios"},
        "summary": "Data analyst con 4 años traduciendo datos operativos en decisiones de "
                   "abastecimiento para retail, combinando SQL profundo, modelos en Python y "
                   "comunicación directa con áreas de negocio.",
        "experience": [
            _exp("FEMSA Digital", "Data Analyst", "2022", "actualidad",
                 "Construí el tablero de disponibilidad de 2,400 tiendas en Looker, adoptado "
                 "por 60 usuarios y reduciendo los reportes manuales semanales de 6 horas a 40 minutos.",
                 "Modele la demanda de 12,000 SKU con Prophet y reglas de recálculo, "
                 "bajando el quiebre de stock 9% en pilotos de 3 regiones.",
                 "Automatice la validación de ingesta con tests de expectativa; los fallos "
                 "de calidad se detectan en minutos en lugar del día siguiente."),
            _exp("Kavak", "Junior Data Analyst", "2020", "2022",
                 "Escribí consultas SQL sobre 2TB de datos de inventario para el equipo de pricing.",
                 "Documenté 30 métricas con definiciones compartidas, eliminando disputas "
                 "de números en juntas de seguimiento."),
        ],
        "projects": [],
        "education": ["Ingeniería en Sistemas Computacionales, Tec de Monterrey, 2020"],
        "certifications": ["Google Data Analytics Professional Certificate, 2021"],
        "skills": ["SQL (intermedio-avanzado)", "Python (pandas, Prophet)", "Looker",
                   "dbt básico", "BigQuery", "Excel avanzado", "Airflow", "Git",
                   "Comunicación de datos", "A/B testing"],
        "languages": ["Español (nativo)", "Inglés B2", "Portugués A2"],
    },
}

def fixture_content(name: str) -> dict:
    return deepcopy(FIXTURES[name])
