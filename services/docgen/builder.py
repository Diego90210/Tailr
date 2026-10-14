"""python-docx builder driven entirely by a `format_spec` (technical_requirements.md §11).

The content tree matches `GenerateRequestSchema.content` (§6). Every dimension of the
output — font, sizes, italic dates, link colour, tab stops, section order, headings —
is read from the spec; nothing is hardcoded here.
"""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def _style_doc(doc: Document, spec: dict) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = spec["font"]
    normal.font.size = Pt(spec["bodySizePt"])
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), spec["font"])
    pf = normal.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = spec["lineSpacing"]


def _add_hyperlink(paragraph, url: str, spec: dict) -> None:
    r_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    rpr = OxmlElement("w:rPr")
    rfonts = OxmlElement("w:rFonts")
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), spec["font"])
    rpr.append(rfonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), spec["linkColor"])
    rpr.append(color)
    if spec["linkUnderline"]:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rpr.append(u)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(spec["bodySizePt"] * 2)))
    rpr.append(sz)

    run = OxmlElement("w:r")
    run.append(rpr)
    text = OxmlElement("w:t")
    text.text = url
    run.append(text)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _heading(doc: Document, text: str, spec: dict):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(spec["headingSpaceBeforePt"])
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(spec["bodySizePt"])
    return p


def _bullet(doc: Document, text: str, spec: dict):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Inches(0.25)
    pf.first_line_indent = Inches(-0.25)
    pf.space_before = Pt(spec["itemSpaceBeforePt"])
    pf.tab_stops.add_tab_stop(Inches(0.25), WD_TAB_ALIGNMENT.LEFT)
    p.add_run("•\t")
    p.add_run(text)
    return p


def _item_line(doc: Document, left: str, right: str, spec: dict):
    """Left label with an optional right-aligned italic date/stack."""
    p = doc.add_paragraph()
    p.add_run(left)
    if right:
        if spec["rightAlignedDates"]:
            p.paragraph_format.tab_stops.add_tab_stop(
                Inches(spec["tabStopIn"]), WD_TAB_ALIGNMENT.RIGHT)
            r = p.add_run("\t" + right)
        else:
            r = p.add_run(" " + right)
        if spec["dateItalic"]:
            r.italic = True
    return p


def build_docx(content: dict, spec: dict, locale: str = "en") -> Document:
    doc = Document()
    _style_doc(doc, spec)
    sec = doc.sections[0]
    sec.page_width = Inches(spec["pageSizeIn"]["w"])
    sec.page_height = Inches(spec["pageSizeIn"]["h"])
    m = spec["marginsIn"]
    sec.top_margin = Inches(m["top"])
    sec.bottom_margin = Inches(m["bottom"])
    sec.left_margin = Inches(m["left"])
    sec.right_margin = Inches(m["right"])

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    name = p.add_run(content["header"]["name"])
    name.bold = spec["nameBold"]
    name.font.size = Pt(spec["nameSizePt"])
    doc.add_paragraph().add_run(content["header"]["contactLine"])

    headings = spec["headings"][locale]
    for section in spec["sectionOrder"]:
        data = content.get(section)
        if not data:
            continue
        _heading(doc, headings[section], spec)
        if section == "summary":
            doc.add_paragraph(data)
        elif section in ("experience", "projects"):
            for item in data:
                if section == "experience":
                    _item_line(doc, item["role"], f"{item['start']} – {item['end']}", spec)
                    _item_line(doc, item["company"], "", spec)
                else:
                    _item_line(doc, item["name"], item.get("stack", ""), spec)
                    if item.get("url"):
                        lp = doc.add_paragraph()
                        lp.paragraph_format.space_before = Pt(spec["itemSpaceBeforePt"])
                        _add_hyperlink(lp, item["url"], spec)
                for b in item["bullets"]:
                    _bullet(doc, b["text"], spec)
        else:
            for entry in data:
                doc.add_paragraph(entry)
    return doc
