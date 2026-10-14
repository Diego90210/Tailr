"""format_spec rows: the global default read by the builder (technical_requirements.md §11.1).

A `format_spec` is a plain dict (`GenerateRequestSchema.formatSpec` is `z.record(z.any())`),
so the builder can be exercised with any variation of these keys.
"""

DEFAULT_FORMAT_SPEC = {
    "font": "Cambria",
    "nameSizePt": 15,
    "nameBold": True,
    "bodySizePt": 11,
    "dateItalic": True,
    "linkColor": "0563C1",
    "linkUnderline": True,
    "marginsIn": {"top": 0.3, "bottom": 0.3, "left": 0.5, "right": 0.5},
    "lineSpacing": 1.13,
    "headingSpaceBeforePt": 8,
    "itemSpaceBeforePt": 3,
    # pageSizeIn is not user-configurable yet; the docs leave A4 vs Letter open (RF-14.4).
    # Letter is implied by tabStopIn 7.5 == usable width of Letter with 0.5in margins.
    "pageSizeIn": {"w": 8.5, "h": 11.0},
    "sectionOrder": ["summary", "experience", "projects", "education",
                     "certifications", "skills", "languages"],
    "headings": {
        "en": {"summary": "PROFESSIONAL PROFILE", "experience": "EXPERIENCE",
               "projects": "PROJECTS", "education": "EDUCATION",
               "certifications": "CERTIFICATIONS", "skills": "SKILLS",
               "languages": "LANGUAGES"},
        "es": {"summary": "PERFIL PROFESIONAL", "experience": "EXPERIENCIA",
               "projects": "PROYECTOS", "education": "EDUCACIÓN",
               "certifications": "CERTIFICACIONES", "skills": "HABILIDADES",
               "languages": "IDIOMAS"},
    },
    "rightAlignedDates": True,
    "tabStopIn": 7.5,
}
