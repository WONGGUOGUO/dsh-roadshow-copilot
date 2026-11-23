"""Build a Word roadshow report from a JSON spec.

Usage: python build_report.py <session_dir> [--spec report_spec.json]

Spec schema (all fields optional except projects):
{
  "title": "...", "subtitle": "...",
  "meta": {"时间": "...", "主办": "...", "形式": "...", "记录方式": "..."},
  "overview": "3-6 句会议综述",
  "projects": [{
      "name": "项目名", "company": "公司", "tagline": "一句话定位",
      "tags": ["赛道"],
      "highlights": ["要点1", "要点2"],
      "market": "...", "model": "...", "traction": "...",
      "financing": {"round": "A轮", "amount": "5000万", "valuation": "5亿", "use": "..."},
      "landing": "落地诉求",
      "contact": {"person": "", "phone": "", "wechat": "", "qr": "path/to/qr.jpg"},
      "qa": [["投资人问题", "项目方回答"]],
      "images": ["keyframes/f_120000.jpg"]
  }],
  "observations": ["..."],
  "followups": [{"item": "...", "owner": "...", "due": "..."}]
}
"""
import argparse
import json
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x59, 0x59, 0x59)


def set_cn_font(run, name="微软雅黑", size=None, bold=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_cn_font(r, size=15 if level == 1 else 12.5, bold=True, color=ACCENT)
    return p


def add_body(doc, text, size=10.5, bold=False, color=None, indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.3
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    r = p.add_run(text)
    set_cn_font(r, size=size, bold=bold, color=color)
    return p


def add_bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(it)
        set_cn_font(r, size=10.5)


def add_kv_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        if not v:
            continue
        cells = table.add_row().cells
        cells[0].width = Cm(3.2); cells[1].width = Cm(12.5)
        pk = cells[0].paragraphs[0]; rk = pk.add_run(k)
        set_cn_font(rk, size=10, bold=True)
        pv = cells[1].paragraphs[0]; rv = pv.add_run(str(v))
        set_cn_font(rv, size=10)
    doc.add_paragraph()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--spec", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    spec_path = args.spec or os.path.join(args.session, "report_spec.json")
    spec = json.load(open(spec_path, encoding="utf-8-sig"))

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.0); sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.2); sec.right_margin = Cm(2.2)

    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run(spec.get("title", "路演会议纪要"))
    set_cn_font(r, size=20, bold=True, color=ACCENT)
    if spec.get("subtitle"):
        st = doc.add_paragraph(); st.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = st.add_run(spec["subtitle"]); set_cn_font(r, size=11, color=MUTED)

    meta = spec.get("meta") or {}
    if meta:
        add_kv_table(doc, list(meta.items()))

    if spec.get("overview"):
        add_heading(doc, "一、会议综述")
        add_body(doc, spec["overview"])

    projects = spec.get("projects") or []
    if projects:
        add_heading(doc, "二、项目速览" if not spec.get("overview") else "二、路演项目")
        table = doc.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        hdr = ["项目", "一句话定位", "融资需求", "联系方式"]
        for i, h in enumerate(hdr):
            r = table.rows[0].cells[i].paragraphs[0].add_run(h)
            set_cn_font(r, size=9.5, bold=True)
        for p in projects:
            fin = p.get("financing") or {}
            contact = p.get("contact") or {}
            row = table.add_row().cells
            vals = [p.get("name", ""), p.get("tagline", ""),
                    " / ".join(x for x in [fin.get("amount"), fin.get("valuation")] if x),
                    " ".join(x for x in [contact.get("person"), contact.get("phone")] if x)]
            for i, v in enumerate(vals):
                rr = row[i].paragraphs[0].add_run(v)
                set_cn_font(rr, size=9.5)

        for idx, p in enumerate(projects, 1):
            add_heading(doc, f"{idx}. {p.get('name','')}", level=2)
            if p.get("company"):
                add_body(doc, p["company"], size=10, color=MUTED)
            if p.get("tagline"):
                add_body(doc, p["tagline"], size=11, bold=True)
            if p.get("tags"):
                add_body(doc, "标签：" + " · ".join(p["tags"]), size=9.5, color=MUTED)
            for label, key in [("核心亮点", "highlights"), ("市场", "market"),
                               ("商业模式", "model"), ("进展", "traction")]:
                val = p.get(key)
                if not val:
                    continue
                if isinstance(val, list):
                    add_body(doc, label, size=10.5, bold=True)
                    add_bullets(doc, val)
                else:
                    add_body(doc, f"{label}：{val}")
            fin = p.get("financing") or {}
            rows = [(k, fin.get(k)) for k in ["round", "amount", "valuation", "use"] if fin.get(k)]
            if rows:
                add_body(doc, "融资需求", size=10.5, bold=True)
                add_kv_table(doc, [("轮次", fin.get("round")), ("金额", fin.get("amount")),
                                   ("估值", fin.get("valuation")), ("用途", fin.get("use"))])
            if p.get("landing"):
                add_body(doc, f"落地诉求：{p['landing']}")
            if p.get("qa"):
                add_body(doc, "投资人问答", size=10.5, bold=True)
                for q, a in p["qa"]:
                    add_body(doc, f"问：{q}", size=10)
                    add_body(doc, f"答：{a}", size=10, indent=0.5)
            contact = p.get("contact") or {}
            if contact:
                add_body(doc, "联系方式", size=10.5, bold=True)
                add_kv_table(doc, [("联系人", contact.get("person")), ("手机", contact.get("phone")),
                                   ("微信", contact.get("wechat")), ("其他", contact.get("other"))])
                qr = contact.get("qr")
                if qr:
                    qp = qr if os.path.isabs(qr) else os.path.join(args.session, qr)
                    if os.path.exists(qp):
                        doc.add_picture(qp, width=Cm(4.2))
                        cap = doc.add_paragraph(); cr = cap.add_run("扫码对接")
                        set_cn_font(cr, size=9, color=MUTED)
            for img in p.get("images") or []:
                ip = img if os.path.isabs(img) else os.path.join(args.session, img)
                if os.path.exists(ip):
                    doc.add_picture(ip, width=Cm(15.5))

    if spec.get("observations"):
        add_heading(doc, "三、观察与判断" if projects else "二、观察与判断")
        add_bullets(doc, spec["observations"])

    if spec.get("followups"):
        add_heading(doc, "四、后续跟进" if projects else "三、后续跟进")
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Grid Accent 1"
        for i, h in enumerate(["事项", "负责人", "时间"]):
            r = table.rows[0].cells[i].paragraphs[0].add_run(h)
            set_cn_font(r, size=9.5, bold=True)
        for f in spec["followups"]:
            row = table.add_row().cells
            for i, k in enumerate(["item", "owner", "due"]):
                rr = row[i].paragraphs[0].add_run(f.get(k, ""))
                set_cn_font(rr, size=9.5)

    out = args.out or os.path.join(args.session, "路演会议纪要.docx")
    doc.save(out)
    print(out)


if __name__ == "__main__":
    main()
