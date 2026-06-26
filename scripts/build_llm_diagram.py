#!/usr/bin/env python3
"""Render LLM provider architecture diagram as PNG, PDF, and SVG."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "img" / "devops-open-agent-icon.png"
OUT_PNG = ROOT / "img" / "llm-provider-diagram.png"
OUT_PDF = ROOT / "img" / "llm-provider-diagram.pdf"
OUT_SVG = ROOT / "img" / "llm-provider-diagram.svg"
TMP_PDF = ROOT / "img" / ".llm-provider-diagram-tmp.pdf"

W, H = 1200, 640

PROVIDERS = [
    ("Ollama", "Local / self-hosted LLM", "O", (0.13, 0.83, 0.93)),
    ("OpenAI", "GPT-4o / GPT-4o-mini", "AI", (0.06, 0.73, 0.51)),
    ("Anthropic", "Claude Sonnet / Opus", "A", (0.96, 0.62, 0.04)),
    ("OpenRouter", "100+ models · one API key", "OR", (0.55, 0.36, 0.96)),
]


def draw_diagram(pdf_path: Path) -> None:
    c = canvas.Canvas(str(pdf_path), pagesize=(W, H))
    c.setTitle("DevOps Open Agent LLM Provider Architecture")

    c.setFillColorRGB(0.04, 0.07, 0.13)
    c.roundRect(0, 0, W, H, 24, fill=1, stroke=0)

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, H - 42, "DevOps Open Agent — LLM Provider Architecture")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 14)
    c.drawCentredString(W / 2, H - 68, "One platform · Shared LLM layer · Your choice of provider")

    box_x, box_y, box_w, box_h = 70, 155, 220, 250
    c.setFillColorRGB(0.09, 0.11, 0.15)
    c.setStrokeColorRGB(0.20, 0.25, 0.33)
    c.setLineWidth(2)
    c.roundRect(box_x, box_y, box_w, box_h, 28, fill=1, stroke=1)

    icon_size = 125
    c.drawImage(
        ImageReader(str(ICON)),
        box_x + (box_w - icon_size) / 2,
        box_y + 24,
        width=icon_size,
        height=icon_size,
        mask="auto",
    )
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(box_x + box_w / 2, box_y + 168, "DevOps Open Agent")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 11)
    c.drawCentredString(box_x + box_w / 2, box_y + 150, "K8s · AWS · Cost · PR Review")

    center_y = box_y + box_h / 2

    c.setStrokeColorRGB(0.22, 0.74, 0.97)
    c.setLineWidth(3)
    c.line(290, center_y, 430, center_y)
    c.line(420, center_y, 430, center_y)
    c.line(420, center_y - 6, 430, center_y)
    c.line(420, center_y + 6, 430, center_y)

    llm_x, llm_y, llm_w, llm_h = 430, 200, 240, 130
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.22, 0.74, 0.97)
    c.roundRect(llm_x, llm_y, llm_w, llm_h, 20, fill=1, stroke=1)
    c.setFillColorRGB(0.22, 0.74, 0.97)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(llm_x + llm_w / 2, llm_y + 92, "SHARED AI LAYER")
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(llm_x + llm_w / 2, llm_y + 62, "LLM")
    c.setFillColorRGB(0.80, 0.84, 0.88)
    c.setFont("Helvetica", 11)
    c.drawCentredString(llm_x + llm_w / 2, llm_y + 36, "Context · Prompts · RCA")

    hub_x = 760
    branch_ys = [500, 395, 290, 185]
    card_h = 100

    c.setStrokeColorRGB(0.65, 0.55, 0.98)
    c.setLineWidth(3)
    c.line(670, center_y, hub_x, center_y)
    c.line(hub_x, branch_ys[-1], hub_x, branch_ys[0])

    for index, (name, subtitle, initial, color) in enumerate(PROVIDERS):
        y = branch_ys[index]
        c.line(hub_x, y, 860, y)
        c.line(850, y, 860, y)
        c.line(850, y - 6, 860, y)
        c.line(850, y + 6, 860, y)

        px, py, pw = 860, y - card_h / 2, 260
        c.setFillColorRGB(0.09, 0.11, 0.15)
        c.setStrokeColorRGB(0.20, 0.25, 0.33)
        c.roundRect(px, py, pw, card_h, 18, fill=1, stroke=1)

        c.setFillColorRGB(*color)
        c.circle(900, y, 22, fill=1, stroke=0)
        c.setFillColorRGB(0.04, 0.07, 0.13)
        font_size = 10 if len(initial) > 1 else 13
        c.setFont("Helvetica-Bold", font_size)
        c.drawCentredString(900, y - 4, initial)

        c.setFillColorRGB(0.97, 0.98, 0.99)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(990, y + 12, name)
        c.setFillColorRGB(0.58, 0.64, 0.72)
        c.setFont("Helvetica", 12)
        c.drawCentredString(990, y - 10, subtitle)

    c.setFillColorRGB(0.39, 0.45, 0.55)
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        W / 2,
        18,
        "Configure provider in backend/.env · All four agent modules use the same LLM layer",
    )

    c.save()


def write_svg() -> None:
    branch_ys = [500, 395, 290, 185]
    card_h = 100
    provider_blocks = []
    for index, (name, subtitle, initial, color) in enumerate(PROVIDERS):
        y = branch_ys[index]
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
        )
        font_size = 10 if len(initial) > 1 else 13
        provider_blocks.append(
            f"""  <line x1="760" y1="{y}" x2="860" y2="{y}" stroke="#A78BFA" stroke-width="3" marker-end="url(#arrowPurple)"/>
  <g filter="url(#shadow)">
    <rect x="860" y="{y - card_h / 2}" width="260" height="{card_h}" rx="18" fill="#171B26" stroke="#334155" stroke-width="2"/>
    <circle cx="900" cy="{y}" r="22" fill="{hex_color}"/>
    <text x="900" y="{y + 4}" text-anchor="middle" fill="#0B1220" font-family="system-ui,sans-serif" font-size="{font_size}" font-weight="700">{initial}</text>
    <text x="990" y="{y + 12}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="20" font-weight="700">{name}</text>
    <text x="990" y="{y - 10}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="12">{subtitle}</text>
  </g>"""
        )

    OUT_SVG.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="640" viewBox="0 0 1200 640">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0B1220"/><stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.35"/></filter>
    <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#38BDF8"/></marker>
    <marker id="arrowPurple" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#A78BFA"/></marker>
  </defs>
  <rect width="1200" height="640" rx="24" fill="url(#bg)"/>
  <text x="600" y="42" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="24" font-weight="700">DevOps Open Agent — LLM Provider Architecture</text>
  <text x="600" y="68" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="14">One platform · Shared LLM layer · Your choice of provider</text>

  <g filter="url(#shadow)">
    <rect x="70" y="155" width="220" height="250" rx="28" fill="#171B26" stroke="#334155" stroke-width="2"/>
    <image x="92" y="179" width="176" height="176" xlink:href="devops-open-agent-icon.png"/>
    <text x="180" y="348" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="17" font-weight="700">DevOps Open Agent</text>
    <text x="180" y="368" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="11">K8s · AWS · Cost · PR Review</text>
  </g>

  <line x1="290" y1="280" x2="430" y2="280" stroke="#38BDF8" stroke-width="3" marker-end="url(#arrowBlue)"/>
  <g filter="url(#shadow)">
    <rect x="430" y="200" width="240" height="130" rx="20" fill="#1E293B" stroke="#38BDF8" stroke-width="2"/>
    <text x="550" y="292" text-anchor="middle" fill="#38BDF8" font-family="system-ui,sans-serif" font-size="12" font-weight="700">SHARED AI LAYER</text>
    <text x="550" y="262" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="24" font-weight="700">LLM</text>
    <text x="550" y="236" text-anchor="middle" fill="#CBD5E1" font-family="system-ui,sans-serif" font-size="11">Context · Prompts · RCA</text>
  </g>

  <line x1="670" y1="280" x2="760" y2="280" stroke="#A78BFA" stroke-width="3"/>
  <line x1="760" y1="185" x2="760" y2="500" stroke="#A78BFA" stroke-width="3"/>
{chr(10).join(provider_blocks)}

  <text x="600" y="618" text-anchor="middle" fill="#64748B" font-family="system-ui,sans-serif" font-size="12">Configure provider in backend/.env · All four agent modules use the same LLM layer</text>
</svg>""",
        encoding="utf-8",
    )


def pdf_to_png(pdf_path: Path, png_path: Path) -> None:
    try:
        import fitz

        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        pix.save(png_path)
        return
    except Exception:
        pass
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(pdf_path), dpi=200)
        images[0].save(png_path, "PNG")
        return
    except Exception:
        pass
    raise RuntimeError("Install pymupdf or pdf2image to export PNG")


def main() -> None:
    if not ICON.exists():
        raise FileNotFoundError(f"Missing icon: {ICON}")
    draw_diagram(TMP_PDF)
    TMP_PDF.replace(OUT_PDF)
    pdf_to_png(OUT_PDF, OUT_PNG)
    write_svg()
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_PDF}")
    print(f"Wrote {OUT_SVG}")


if __name__ == "__main__":
    main()
