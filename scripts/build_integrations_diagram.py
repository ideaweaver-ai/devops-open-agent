#!/usr/bin/env python3
"""Render DevOps Open Agent → Integrations → PagerDuty, Teams & Slack diagram."""

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

W, H = 1200, 620
CENTER_Y = 310
CARD_W, CARD_H = 180, 125
CARD_X = 860
CARD_GAP = 22


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
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, mid_y - 38, "PagerDuty · Teams · Slack")


def draw_pagerduty_card(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.02, 0.67, 0.22)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    c.setFillColorRGB(0.02, 0.67, 0.22)
    c.circle(mid_x, y + h / 2 + 14, 24, fill=1, stroke=0)
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(mid_x, y + h / 2 + 10, "PD")

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(mid_x, y + 38, "PagerDuty")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, y + 22, "Incidents · On-call")


def draw_teams_card(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.31, 0.39, 0.79)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    c.setFillColorRGB(0.31, 0.39, 0.79)
    c.roundRect(mid_x - 24, y + h / 2 - 18, 48, 48, 12, fill=1, stroke=0)
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(mid_x, y + h / 2 + 2, "T")

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(mid_x, y + 38, "Microsoft Teams")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, y + 22, "Team alerts · Webhooks")


def draw_slack_card(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColorRGB(0.12, 0.16, 0.23)
    c.setStrokeColorRGB(0.29, 0.08, 0.29)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 22, fill=1, stroke=1)

    mid_x = x + w / 2
    c.setFillColorRGB(0.29, 0.08, 0.29)
    c.roundRect(mid_x - 24, y + h / 2 - 18, 48, 48, 12, fill=1, stroke=0)
    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(mid_x, y + h / 2 + 2, "#")

    c.setFillColorRGB(0.97, 0.98, 0.99)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(mid_x, y + 38, "Slack")
    c.setFillColorRGB(0.58, 0.64, 0.72)
    c.setFont("Helvetica", 10)
    c.drawCentredString(mid_x, y + 22, "Team alerts · Webhooks")


def card_positions() -> tuple[float, float, float]:
    total = CARD_H * 3 + CARD_GAP * 2
    top_y = CENTER_Y + total / 2 - CARD_H
    middle_y = top_y - CARD_H - CARD_GAP
    bottom_y = middle_y - CARD_H - CARD_GAP
    return top_y, middle_y, bottom_y


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
        "AI recommendations delivered to PagerDuty, Microsoft Teams, and Slack",
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

    pd_y, teams_y, slack_y = card_positions()
    hub_right = hub_x + hub_w
    hub_mid_y = hub_y + hub_h / 2

    draw_arrow(c, platform_x + platform_w, CENTER_Y, hub_x - 8, hub_mid_y, (0.22, 0.74, 0.97))
    draw_arrow(
        c,
        hub_right + 5,
        hub_mid_y + 58,
        CARD_X - 8,
        pd_y + CARD_H / 2,
        (0.02, 0.67, 0.22),
    )
    draw_arrow(
        c,
        hub_right + 5,
        hub_mid_y,
        CARD_X - 8,
        teams_y + CARD_H / 2,
        (0.31, 0.39, 0.79),
    )
    draw_arrow(
        c,
        hub_right + 5,
        hub_mid_y - 58,
        CARD_X - 8,
        slack_y + CARD_H / 2,
        (0.29, 0.08, 0.29),
    )

    draw_pagerduty_card(c, CARD_X, pd_y, CARD_W, CARD_H)
    draw_teams_card(c, CARD_X, teams_y, CARD_W, CARD_H)
    draw_slack_card(c, CARD_X, slack_y, CARD_W, CARD_H)

    c.setFillColorRGB(0.39, 0.45, 0.55)
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        W / 2,
        18,
        "Per-user webhooks · Configurable cooldown · Agent-level toggles · Integrations tab in UI",
    )

    c.save()


def write_svg() -> None:
    platform_x, platform_w, platform_h = 60, 210, 250
    platform_y = CENTER_Y - platform_h / 2
    hub_x, hub_w, hub_h = 430, 220, 180
    hub_y = CENTER_Y - hub_h / 2
    pd_y, teams_y, slack_y = card_positions()
    hub_right = hub_x + hub_w
    hub_mid_x = hub_x + hub_w / 2
    hub_mid_y = hub_y + hub_h / 2

    OUT_SVG.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="620" viewBox="0 0 1200 620">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0B1220"/><stop offset="100%" stop-color="#111827"/>
    </linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="4" stdDeviation="8" flood-opacity="0.35"/></filter>
    <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#38BDF8"/></marker>
    <marker id="arrowGreen" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#06AC38"/></marker>
    <marker id="arrowTeams" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#5059C9"/></marker>
    <marker id="arrowSlack" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#4A154B"/></marker>
  </defs>
  <rect width="1200" height="620" rx="24" fill="url(#bg)"/>
  <text x="600" y="42" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="24" font-weight="700">DevOps Open Agent — Enterprise Integrations</text>
  <text x="600" y="68" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="14">AI recommendations delivered to PagerDuty, Microsoft Teams, and Slack</text>

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
    <text x="{hub_mid_x}" y="{hub_mid_y - 38}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">PagerDuty · Teams · Slack</text>
  </g>

  <line x1="{hub_right + 5}" y1="{hub_mid_y + 58}" x2="{CARD_X - 8}" y2="{pd_y + CARD_H / 2}" stroke="#06AC38" stroke-width="3" marker-end="url(#arrowGreen)"/>
  <line x1="{hub_right + 5}" y1="{hub_mid_y}" x2="{CARD_X - 8}" y2="{teams_y + CARD_H / 2}" stroke="#5059C9" stroke-width="3" marker-end="url(#arrowTeams)"/>
  <line x1="{hub_right + 5}" y1="{hub_mid_y - 58}" x2="{CARD_X - 8}" y2="{slack_y + CARD_H / 2}" stroke="#4A154B" stroke-width="3" marker-end="url(#arrowSlack)"/>

  <g filter="url(#shadow)">
    <rect x="{CARD_X}" y="{pd_y}" width="{CARD_W}" height="{CARD_H}" rx="22" fill="#1E293B" stroke="#06AC38" stroke-width="2"/>
    <circle cx="{CARD_X + CARD_W / 2}" cy="{pd_y + CARD_H / 2 + 14}" r="24" fill="#06AC38"/>
    <text x="{CARD_X + CARD_W / 2}" y="{pd_y + CARD_H / 2 + 20}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="16" font-weight="700">PD</text>
    <text x="{CARD_X + CARD_W / 2}" y="{pd_y + 38}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="20" font-weight="700">PagerDuty</text>
    <text x="{CARD_X + CARD_W / 2}" y="{pd_y + 22}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">Incidents · On-call</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="{CARD_X}" y="{teams_y}" width="{CARD_W}" height="{CARD_H}" rx="22" fill="#1E293B" stroke="#5059C9" stroke-width="2"/>
    <rect x="{CARD_X + CARD_W / 2 - 24}" y="{teams_y + CARD_H / 2 - 18}" width="48" height="48" rx="12" fill="#5059C9"/>
    <text x="{CARD_X + CARD_W / 2}" y="{teams_y + CARD_H / 2 + 8}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="18" font-weight="700">T</text>
    <text x="{CARD_X + CARD_W / 2}" y="{teams_y + 38}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="18" font-weight="700">Microsoft Teams</text>
    <text x="{CARD_X + CARD_W / 2}" y="{teams_y + 22}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">Team alerts · Webhooks</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="{CARD_X}" y="{slack_y}" width="{CARD_W}" height="{CARD_H}" rx="22" fill="#1E293B" stroke="#4A154B" stroke-width="2"/>
    <rect x="{CARD_X + CARD_W / 2 - 24}" y="{slack_y + CARD_H / 2 - 18}" width="48" height="48" rx="12" fill="#4A154B"/>
    <text x="{CARD_X + CARD_W / 2}" y="{slack_y + CARD_H / 2 + 8}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="24" font-weight="700">#</text>
    <text x="{CARD_X + CARD_W / 2}" y="{slack_y + 38}" text-anchor="middle" fill="#F8FAFC" font-family="system-ui,sans-serif" font-size="20" font-weight="700">Slack</text>
    <text x="{CARD_X + CARD_W / 2}" y="{slack_y + 22}" text-anchor="middle" fill="#94A3B8" font-family="system-ui,sans-serif" font-size="10">Team alerts · Webhooks</text>
  </g>

  <text x="600" y="602" text-anchor="middle" fill="#64748B" font-family="system-ui,sans-serif" font-size="12">Per-user webhooks · Configurable cooldown · Agent-level toggles · Integrations tab in UI</text>
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
