"""Build the reviewed manuscript DOCX using bundled python-docx dependencies."""

import argparse
import re
from pathlib import Path

import latex2mathml.converter
import mathml2omml
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.paragraph import Paragraph
from lxml import etree
from PIL import Image

parser = argparse.ArgumentParser(__doc__)
parser.add_argument("--root", type=Path, required=True)
args = parser.parse_args()
root = args.root
doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.27)
section.page_height = Inches(11.69)
section.top_margin = section.bottom_margin = Inches(0.72)
section.left_margin = section.right_margin = Inches(0.78)
styles = doc.styles
for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Caption"):
    styles[name].font.name = "Times New Roman"
    styles[name].font.color.rgb = RGBColor(0, 0, 0)
styles["Normal"].font.size = Pt(10.5)
styles["Normal"].paragraph_format.line_spacing = 1.12
styles["Normal"].paragraph_format.space_after = Pt(5)
styles["Normal"].paragraph_format.widow_control = True
styles["Title"].font.size = Pt(18)
styles["Title"].font.bold = True
styles["Title"].paragraph_format.space_after = Pt(8)
for name, size in (("Heading 1", 13), ("Heading 2", 11.2)):
    styles[name].font.size = Pt(size)
    styles[name].font.bold = True
    styles[name].paragraph_format.space_before = Pt(10)
    styles[name].paragraph_format.space_after = Pt(5)
    styles[name].paragraph_format.keep_with_next = True
styles["Caption"].font.size = Pt(9)
styles["Caption"].font.italic = True
styles["Caption"].font.bold = False
styles["Caption"].paragraph_format.space_after = Pt(7)
for style in styles:
    for border in list(style.element.iter(qn("w:pBdr"))):
        border.getparent().remove(border)
    for fonts in style.element.iter(qn("w:rFonts")):
        for key in list(fonts.attrib):
            if "theme" in key.lower():
                del fonts.attrib[key]
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = footer.add_run()
r.font.size = Pt(9)
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), "PAGE")
r._r.addnext(fld)
doc.core_properties.title = (
    "Source Retention and Adaptive Expert Fusion for Low History EV Charging Forecasts"
)
doc.core_properties.author = "AIP491 G10 Research Team"
doc.core_properties.subject = "Teacher review manuscript with baseline verification and historical cohort expert fusion results"


def rich(paragraph: Paragraph, text: str) -> None:
    for part in re.split(r"(\[[^\]]+\]\([^\)]+\))", text):
        match = re.fullmatch(r"\[([^\]]+)\]\(([^\)]+)\)", part)
        if match:
            h = OxmlElement("w:hyperlink")
            h.set(
                qn("r:id"),
                paragraph.part.relate_to(match[2], RELATIONSHIP_TYPE.HYPERLINK, is_external=True),
            )
            run = OxmlElement("w:r")
            props = OxmlElement("w:rPr")
            u = OxmlElement("w:u")
            u.set(qn("w:val"), "single")
            props.append(u)
            run.append(props)
            t = OxmlElement("w:t")
            t.text = match[1]
            run.append(t)
            h.append(run)
            paragraph._p.append(h)
        else:
            paragraph.add_run(part)


def image_paragraph(path: Path, alt: str, maximum: float = 6.35) -> None:
    width, height = Image.open(path).size
    dpi = Image.open(path).info.get("dpi", (220, 220))[0]
    native_width = width / dpi
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    inline = run.add_picture(str(path), width=Inches(min(maximum, native_width)))
    inline._inline.docPr.set("descr", alt)
    paragraph.paragraph_format.space_after = Pt(2)


lines = (root / "manuscript.md").read_text().splitlines()
i = 0
equation = 0
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue
    if line.startswith("# "):
        doc.add_paragraph(line[2:], "Title")
        i += 1
        continue
    if line.startswith("## "):
        paragraph = doc.add_paragraph(line[3:], "Heading 1")
        if line[3:] == "References":
            paragraph.paragraph_format.page_break_before = True
        i += 1
        continue
    if line.startswith("### "):
        doc.add_paragraph(line[4:], "Heading 2")
        i += 1
        continue
    if line.startswith("$$"):
        equation += 1
        mathml = latex2mathml.converter.convert(line.removeprefix("$$").removesuffix("$$"))
        omml = mathml2omml.convert(mathml).replace(
            "<m:oMath>",
            '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">',
            1,
        )
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(7)
        math = etree.fromstring(omml.encode())
        namespaces = {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
        for nary in math.findall(".//m:nary", namespaces):
            properties = nary.find("m:naryPr", namespaces)
            for limit in ("sub", "sup"):
                value = nary.find("m:" + limit, namespaces)
                if value is not None and not "".join(value.itertext()).strip():
                    hidden = OxmlElement("m:" + limit + "Hide")
                    hidden.set(qn("m:val"), "1")
                    properties.append(hidden)
        for upper in math.findall(".//m:limUpp", namespaces):
            limit = upper.find("m:lim", namespaces)
            if limit is not None and "".join(limit.itertext()) == "^":
                accent = OxmlElement("m:acc")
                properties = OxmlElement("m:accPr")
                character = OxmlElement("m:chr")
                character.set(qn("m:val"), "\u0302")
                properties.append(character)
                accent.append(properties)
                accent.append(upper.find("m:e", namespaces))
                upper.getparent().replace(upper, accent)
        for accent in math.findall(".//m:accPr/m:chr", namespaces):
            if accent.get(qn("m:val")) == "^":
                accent.set(qn("m:val"), "\u0302")
        doc.paragraphs[-2].paragraph_format.keep_with_next = True
        paragraph._p.append(math)
        i += 1
        continue
    match = re.fullmatch(r"!\[([^\]]*)\]\(([^\)]+)\)", line)
    if match:
        image_paragraph(root / match[2], match[1])
        i += 1
        continue
    if line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            values = [x.strip() for x in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r"[-: ]+", v) for v in values):
                rows.append(values)
            i += 1
        table = doc.add_table(rows=0, cols=len(rows[0]))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        total = 6.65
        widths = (
            ([2.65] + [(total - 2.65) / (len(rows[0]) - 1)] * (len(rows[0]) - 1))
            if len(rows[0]) == 4
            else [total / len(rows[0])] * len(rows[0])
        )
        if len(rows[0]) == 4 and rows[0][0] == "History":
            widths = [0.8, 1.45, 3.0, 1.4]
        if len(rows[0]) == 5:
            widths = (
                [2.0, 1.16, 1.16, 1.16, 1.16]
                if rows[0][0] == "Model family"
                else [1.2, 1.55, 0.7, 1.15, 2.05]
            )
        if len(rows[0]) == 6:
            widths = [1.35, 0.5, 1.1, 1.3, 1.2, 1.2]
        for column, width in zip(table.columns, widths):
            column.width = Inches(width)
        for j, row in enumerate(rows):
            cells = table.add_row().cells
            for k, text in enumerate(row):
                cell = cells[k]
                cell.width = Inches(widths[k])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                props = cell._tc.get_or_add_tcPr()
                borders = OxmlElement("w:tcBorders")
                for side in ("top", "left", "bottom", "right"):
                    edge = OxmlElement("w:" + side)
                    edge.set(qn("w:val"), "single")
                    edge.set(qn("w:sz"), "4")
                    edge.set(qn("w:color"), "D9D9D9")
                    borders.append(edge)
                props.append(borders)
                margins = OxmlElement("w:tcMar")
                for side in ("top", "left", "bottom", "right"):
                    node = OxmlElement("w:" + side)
                    node.set(qn("w:w"), "70")
                    node.set(qn("w:type"), "dxa")
                    margins.append(node)
                props.append(margins)
                if j == 0 or j % 2 == 0:
                    shade = OxmlElement("w:shd")
                    shade.set(qn("w:fill"), "E4EDF4" if j == 0 else "F5F7FA")
                    props.append(shade)
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.line_spacing = 1.05
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.alignment = (
                    WD_ALIGN_PARAGRAPH.LEFT if k == 0 else WD_ALIGN_PARAGRAPH.CENTER
                )
                run = paragraph.add_run(text)
                run.font.size = Pt(9.2)
                run.bold = j == 0
                paragraph.paragraph_format.keep_with_next = j == 0
            trpr = cells[0]._tc.getparent().get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if j == 0:
                trpr.append(OxmlElement("w:tblHeader"))
        doc.add_paragraph().paragraph_format.space_after = Pt(1)
        continue
    paragraph = doc.add_paragraph(
        style="Caption" if line.startswith(("Figure ", "Table ")) else "Normal"
    )
    rich(paragraph, line)
    i += 1
doc.save(root / "source-retention-review.docx")
print(root / "source-retention-review.docx")
