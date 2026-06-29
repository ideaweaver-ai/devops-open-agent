#!/usr/bin/env python3
"""Render DevOps Open Agent → Integrations → PagerDuty & Slack diagram."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "img" / "devops-open-agent-icon.png"
OUT_PNG = ROOT / "img" / "integrations-diagram.png"
OUT_PDF = ROOT / "img" / "integrations-diagram.pdf"
OUT_SVG = ROOT / "img" / "integrations-diagram.svg"
TMP_PDF = ROOT / "img" / ".integrations-diagram-tmp.pdf"

W, H = 1200, 560
CENTER_Y = 280


def draw_arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, color: tuple[float, float, float]) -> None:
    c.setStrokeColorRGB(*color)
    c.setLineWidth(3)
    c.line(x1, y1, x2, y2)
    angle_x = x2 - x1
    angle_y = y2 - y1
    if abs(angle_x) >= abs(angle_y):
        if angle_x > 0:
            c.line(x2 - 10, y2 - 6, x2, y2)
            c.line(x2 - 10, y2 + 6, x2, y2)
        else:
            c.line(x2 + 10, y2 - 6, x2, y2)
            c.line(x2 + 10, y2 + 6, x2, y2)
    elif angle_y > 0:
        c.line(x2 - 6, y2 - 10, x2, y2)
        c.line(x2 + 6, y2 - 10, x2, y2)
    else:
        c.line(x2 - 6, y2 + 10, x2, y2)
        c.line(x2 + 6, y2 + 10, x2, y2)


def draw_integration_hub(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.22, 0.74, 0.97)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    mid_y = y + h / 2

    c.setFillColorRGB(0.22, 0.74, 0.97)
    c.circle(mid_x, mid_y + 28, 26, fill=1, stroke=0)
    c.setStrokeColorRGB(0.04, 0.07, 0.13)
    c.setLineWidth(3)
    c.line(mid_x - 12, mid_y + 28, mid_x + 12, mid_y + 28)
    c.line(mid_x, mid_y + 16, mid_x, mid_y + 40)

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(mid_x, mid_y - 18, "Integrations")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 11)
    c.drawCentredString(mid_x, mid_y - 38, "PagerDuty · Slack")


def draw_pagerduty_card(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.02, 0.67, 0.22)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    c.setFillColorRGB(0.02, 0.67, 0.22)
    c.circle(mid_x, y + h / 2 + 18, 28, fill=1, stroke=0)
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(mid_x, y + h / 2 + 12, "PD")

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(mid_x, y + 42, "PagerDuty")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, y + 24, "Incidents · On-call")


def draw_slack_card(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.29, 0.08, 0.29)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    c.setFillColorRGB(0.29, 0.08, 0.29)
    c.roundRect(mid_x - 28, y + h / 2 - 10, 56, 56, 14, fill=1, stroke=0)
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(mid_x, y + h / 2 + 8, "#")

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(mid_x, y + 42, "Slack")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, y + 24, "Team alerts · Webhooks")


def draw_diagram(pdf_path: Path) -> None:
    c = canvas.Canvas(str(pdf_path), pagesize=(W, H))
    c.setTitle("DevOps Open Agent — Integrations")

    c.setFillColorRGB(0.04, 0.07, 0.13)
    c.roundRect(0, 0, W, H, 24, fill=1, stroke=0)

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, H - 42, "DevOps Open Agent — Enterprise Integrations")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        W / 2,
        H - 68,
        "AI recommendations delivered to PagerDuty incidents and Slack channels",
    )

    platform_x, platform_w, platform_h = 60, 210, 250
    platform_y = CENTER_Y - platform_h / 2
    c.setFillColorRGB(0.09, 0.11, 0.15)
    c.setStrokeColorRGB(0.20, 0.25, 0.33)
    c.setLineWidth(2)
    c.roundRect(platform_x, platform_y, platform_w, platform_h, 28, fill=1, stroke=1)

    icon_size = 110
    c.drawImage(
        ImageReader(str(ICON)),
        platform_x + (platform_w - icon_size) / 2,
        platform_y + 30,
        width=icon_size,
        height=icon_size,
        mask="auto",
    )
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(platform_x + platform_w / 2, platform_y + 168, "DevOps Open Agent")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 11)
    c.drawCentredString(platform_x + platform_w / 2, platform_y + 150, "Open Source Platform")

    hub_x, hub_w, hub_h = 430, 220, 180
    hub_y = CENTER_Y - hub_h / 2
    draw_integration_hub(c, hub_x, hub_y, hub_w, hub_h)

    pd_x, pd_w, pd_h = 860, 180, 150
    pd_y = CENTER_Y + 35
    slack_y = CENTER_Y - pd_h - 35

    hub_right = hub_x + hub_w
    hub_mid_x = hub_x + hub_w / 2
    hub_mid_y = hub_y + hub_h / 2

    draw_arrow(c, platform_x + platform_w, CENTER_Y, hub_x - 8, hub_mid_y, (0.22, 0.74, 0.97))
    draw_arrow(c, hub_right + 5, hub_mid_y + 42, pd_x - 8, pd_y + pd_h / 2, (0.02, 0.67, 0.22))
    draw_arrow(c, hub_right + 5, hub_mid_y - 42, pd_x - 8, slack_y + pd_h / 2, (0.29, 0.08, 0.29))

    draw_pagerduty_card(c, pd_x, pd_y, pd_w, pd_h)
    draw_slack_card(c, pd_x, slack_y, pd_w, pd_h)

    c.setFillColorRGB(0.39, 0.45, 0.55)
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        W / 2,
        18,
        "Per-user routing keys · Configurable cooldown · Agent-level toggles · Integrations tab in UI",
    )

    c.save()


def write_svg() -> None:
    platform_x, platform_w, platform_h = 60, 210, 250
    platform_y = CENTER_Y - platform_h / 2
    hub_x, hub_w, hub_h = 430, 220, 180
    hub_y = CENTER_Y - hub_h / 2
    pd_x, pd_w, pd_h = 860, 180, 150
    pd_y = CENTER_Y + 35
    slack_y = CENTER_Y - pd_h - 35
    hub_right = hub_x + hub_w
    hub_mid_x = hub_x + hub_w / 2
    hub_mid_y = hub_y + hub_h / 2

    OUT_SVG.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="560" viewBox="0 0 1200 560">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0B1220"/><stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.35"/></filter>
    <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#38BDF8"/></marker>
    <marker id="arrowGreen" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#06AC38"/></marker>
    <marker id="arrowSlack" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#4A154B"/></marker>
  </defs>
  <rect width="1200" height="560" rx="24" fill="url(#bg)"/>
  <text x="600" y="42" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="24" font-weight="700">DevOps Open Agent — Enterprise Integrations</text>
  <text x="600" y="68" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="14">AI recommendations delivered to PagerDuty incidents and Slack channels</text>

  <g filter="url(#shadow)">
    <rect x="{platform_x}" y="{platform_y}" width="{platform_w}" height="{platform_h}" rx="28" fill="#171B26" stroke="#334155" stroke-width="2"/>
    <image x="{platform_x + 55}" y="{platform_y + 30}" width="110" height="110" xlink:href="devops-open-agent-icon.png"/>
    <text x="{platform_x + platform_w / 2}" y="{platform_y + 168}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="16" font-weight="700">DevOps Open Agent</text>
    <text x="{platform_x + platform_w / 2}" y="{platform_y + 150}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="11">Open Source Platform</text>
  </g>

  <line x1="{platform_x + platform_w}" y1="{CENTER_Y}" x2="{hub_x - 8}" y2="{hub_mid_y}" stroke="#38BDF8" stroke-width="3" marker-end="url(#arrowBlue)"/>

  <g filter="url(#shadow)">
    <rect x="{hub_x}" y="{hub_y}" width="{hub_w}" height="{hub_h}" rx="22" fill="#1E293B" stroke="#38BDF8" stroke-width="2"/>
    <circle cx="{hub_mid_x}" cy="{hub_mid_y + 28}" r="26" fill="#38BDF8"/>
    <line x1="{hub_mid_x - 12}" y1="{hub_mid_y + 28}" x2="{hub_mid_x + 12}" y2="{hub_mid_y + 28}" stroke="#0B1220" stroke-width="3"/>
    <line x1="{hub_mid_x}" y1="{hub_mid_y + 16}" x2="{hub_mid_x}" y2="{hub_mid_y + 40}" stroke="#0B1220" stroke-width="3"/>
    <text x="{hub_mid_x}" y="{hub_mid_y - 18}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="22" font-weight="700">Integrations</text>
    <text x="{hub_mid_x}" y="{hub_mid_y - 38}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="11">PagerDuty · Slack</text>
  </g>

  <line x1="{hub_right + 5}" y1="{hub_mid_y + 42}" x2="{pd_x - 8}" y2="{pd_y + pd_h / 2}" stroke="#06AC38" stroke-width="3" marker-end="url(#arrowGreen)"/>
  <line x1="{hub_right + 5}" y1="{hub_mid_y - 42}" x2="{pd_x - 8}" y2="{slack_y + pd_h / 2}" stroke="#4A154B" stroke-width="3" marker-end="url(#arrowSlack)"/>

  <g filter="url(#shadow)">
    <rect x="{pd_x}" y="{pd_y}" width="{pd_w}" height="{pd_h}" rx="22" fill="#1E293B" stroke="#06AC38" stroke-width="2"/>
    <circle cx="{pd_x + pd_w / 2}" cy="{pd_y + pd_h / 2 + 18}" r="28" fill="#06AC38"/>
    <text x="{pd_x + pd_w / 2}" y="{pd_y + pd_h / 2 + 24}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="18" font-weight="700">PD</text>
    <text x="{pd_x + pd_w / 2}" y="{pd_y + 42}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="22" font-weight="700">PagerDuty</text>
    <text x="{pd_x + pd_w / 2}" y="{pd_y + 24}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">Incidents · On-call</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="{pd_x}" y="{slack_y}" width="{pd_w}" height="{pd_h}" rx="22" fill="#1E293B" stroke="#4A154B" stroke-width="2"/>
    <rect x="{pd_x + pd_w / 2 - 28}" y="{slack_y + pd_h / 2 - 10}" width="56" height="56" rx="14" fill="#4A154B"/>
    <text x="{pd_x + pd_w / 2}" y="{slack_y + pd_h / 2 + 14}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="26" font-weight="700">#</text>
    <text x="{pd_x + pd_w / 2}" y="{slack_y + 42}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="22" font-weight="700">Slack</text>
    <text x="{pd_x + pd_w / 2}" y="{slack_y + 24}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">Team alerts · Webhooks</text>
  </g>

  <text x="600" y="542" text-anchor="middle" fill="#64748B" font-family="system-ui,sans-serif" font-size="12">Per-user routing keys · Configurable cooldown · Agent-level toggles · Integrations tab in UI</text>
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
