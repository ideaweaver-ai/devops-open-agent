#!/usr/bin/env python3
"""Build DevOps Open Agent product tour PDF.

Page 1  : Cover with logo and platform overview
Pages 2-15 : Screenshots 1-14 in numeric filename order (no blank pages)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ASSETS = Path("/Users/plakhera/.cursor/projects/Users-plakhera-open-devops-agent/assets")
LOGO = Path("/Users/plakhera/open-devops-agent/img/devops-open-agent-icon.png")
OUTPUTS = [
    Path("/Users/plakhera/open-devops-agent/docs/devops-open-agent-product-tour.pdf"),
    Path("/Users/plakhera/Desktop/devops-open-agent-product-tour.pdf"),
]

PAGE_W, PAGE_H = landscape(letter)
MARGIN = 36
HEADER_H = 72
FOOTER_H = 24

SCREENSHOTS = [
    {
        "num": 1,
        "file": "1-DevOps-Open-Agent-5a66d2a6-c6d9-4c6b-82ab-326422dfa15f.png",
        "title": "DevOps Open Agent",
        "description": (
            "Platform home for the Kubernetes Debugging Agent. Select a cluster, "
            "check system readiness, and start an investigation."
        ),
    },
    {
        "num": 2,
        "file": "2-Kubernetes-Investigation-85aedeec-8cac-4d6c-b168-aecfd2ead9ee.png",
        "title": "Kubernetes Investigation",
        "description": (
            "Live investigation progress across discovery, pods, logs, events, "
            "deployments, networking, topology, and AI diagnosis."
        ),
    },
    {
        "num": 3,
        "file": "3-Kubernetes-AI-Diagnosis-d0f04322-2eec-4005-bfaf-0cd099dd3a51.png",
        "title": "Kubernetes AI Diagnosis",
        "description": (
            "AI root cause analysis with confidence score, evidence, and a clear "
            "summary of the ImagePullBackOff issue."
        ),
    },
    {
        "num": 4,
        "file": "4-Recent-investigation-history-446d7fa4-f733-45ca-9dce-21f7483b1408.png",
        "title": "Recent Investigation History",
        "description": (
            "Unified history showing root cause, agent, cluster, status, confidence, "
            "and timestamps for past runs."
        ),
    },
    {
        "num": 5,
        "file": "5-kubernetes-cluster-topology-6ea30126-3457-4689-9818-a2e55c7a0a8a.png",
        "title": "Kubernetes Cluster Topology",
        "description": (
            "Namespace-grouped resource map of services, deployments, replica sets, "
            "and pods with relationship edges."
        ),
    },
    {
        "num": 6,
        "file": "6-AWS-DevOps-Agent-a1c515ce-9c41-467d-b55b-d3641f9e3f7f.png",
        "title": "AWS DevOps Agent",
        "description": (
            "Choose AWS account, region, and troubleshooting category such as full scan, "
            "security, EC2, network, or change audit."
        ),
    },
    {
        "num": 7,
        "file": "7-AWS-Investigation-cd1808d1-5279-4977-957b-e3275c082f32.png",
        "title": "AWS Investigation",
        "description": (
            "AWS investigation pipeline covering EC2, network, security groups, load "
            "balancers, CloudWatch, CloudTrail, Config, topology, and AI diagnosis."
        ),
    },
    {
        "num": 8,
        "file": "8-AWS-Investigation-history-0565c043-41c0-4820-a14d-bd43ac2e2090.png",
        "title": "AWS Investigation History",
        "description": (
            "AWS investigation history with account/region, status, confidence, and "
            "root cause summaries."
        ),
    },
    {
        "num": 9,
        "file": "9-AWS-AI-Analysis-25239a38-b6c7-46a1-bd80-17b47e185a32.png",
        "title": "AWS AI Analysis",
        "description": (
            "AI diagnosis for exposed security groups, stopped EC2 instances, and "
            "actionable suggested fixes with CLI examples."
        ),
    },
    {
        "num": 10,
        "file": "10-AWS-Topology-efc788b6-56cd-4ac4-bdb9-2bb5af88c454.png",
        "title": "AWS Topology",
        "description": (
            "Interactive AWS topology map for VPCs, subnets, EC2, EBS, security groups, "
            "gateways, and IAM relationships."
        ),
    },
    {
        "num": 11,
        "file": "11-Cloud-cost-detector-6478a266-dbfd-4f4a-8086-e10f65c87b2e.png",
        "title": "Cloud Cost Detector",
        "description": (
            "Multi-step AWS cost optimization workflow from discovery through unused "
            "resource analysis to AI cost analysis."
        ),
    },
    {
        "num": 12,
        "file": "12-Cloud-investigation-details-eb9682ae-6deb-4f2c-9c23-02effe3afa94.png",
        "title": "Cloud Investigation Details",
        "description": (
            "Detailed savings estimate, Cost Explorer context, AI optimization report, "
            "and prioritized findings for wasteful resources."
        ),
    },
    {
        "num": 13,
        "file": "13-GitHub-PR-Reviewer-52b9911f-0541-4f59-80f4-a5524221c6ed.png",
        "title": "GitHub PR Reviewer",
        "description": (
            "Configure GitHub webhooks and tokens, or trigger a manual DevOps PR review "
            "for any repository."
        ),
    },
    {
        "num": 14,
        "file": "14-PR-Review-AI-Analysis-55848ffe-8adc-4f29-88b4-67d1728077d8.png",
        "title": "PR Review AI Analysis",
        "description": (
            "Completed AI DevOps PR review with risk rating and structured security "
            "and reliability findings."
        ),
    },
]


def fit_box(src_w: int, src_h: int, max_w: float, max_h: float) -> tuple[float, float]:
    scale = min(max_w / src_w, max_h / src_h)
    return src_w * scale, src_h * scale


def wrap_text(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, line_height: float) -> float:
    words = text.split()
    line: list[str] = []
    current_y = y
    for word in words:
        trial = " ".join(line + [word])
        if c.stringWidth(trial, "Helvetica", 11) <= max_width:
            line.append(word)
        else:
            if line:
                c.drawString(x, current_y, " ".join(line))
                current_y -= line_height
            line = [word]
    if line:
        c.drawString(x, current_y, " ".join(line))
        current_y -= line_height
    return current_y


def draw_cover(c: canvas.Canvas) -> None:
    c.setFillColor(colors.HexColor("#0B1220"))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    content_w = PAGE_W - 2 * MARGIN
    center_x = PAGE_W / 2

    if LOGO.exists():
        with PILImage.open(LOGO) as logo:
            lw, lh = logo.size
        logo_size = 140
        lw, lh = fit_box(lw, lh, logo_size, logo_size)
        c.drawImage(
            ImageReader(str(LOGO)),
            center_x - lw / 2,
            PAGE_H - MARGIN - lh - 10,
            width=lw,
            height=lh,
            mask="auto",
        )
        text_top = PAGE_H - MARGIN - lh - 36
    else:
        text_top = PAGE_H - MARGIN - 40

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(center_x, text_top, "DevOps Open Agent")

    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(
        center_x,
        text_top - 28,
        "Open Source AI-Powered DevOps Troubleshooting Platform",
    )

    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.setFont("Helvetica", 11)
    intro = (
        "Self-hostable platform for Kubernetes debugging, AWS troubleshooting, "
        "cloud cost optimization, and AI-powered GitHub PR review. "
        "Run locally or on your own infrastructure with Docker Compose."
    )
    y = wrap_text(c, intro, MARGIN + 40, text_top - 70, content_w - 80, 16)

    c.setFillColor(colors.HexColor("#38BDF8"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 40, y - 10, "Modules")

    modules = [
        "1. Kubernetes Debugging Agent — clusters, workloads, networking, topology",
        "2. AWS DevOps Agent — EC2, VPC, security, load balancers, CloudTrail",
        "3. Cloud Cost Detector — unused resources and savings estimates",
        "4. PR Reviewer — DevOps-focused GitHub pull request reviews",
    ]
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.setFont("Helvetica", 11)
    module_y = y - 30
    for item in modules:
        c.drawString(MARGIN + 52, module_y, item)
        module_y -= 18

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(center_x, MARGIN, "Page 1 · Cover · DevOps Open Agent Product Tour")


def draw_screenshot_page(c: canvas.Canvas, page: dict) -> None:
    c.setFillColor(colors.white)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    content_w = PAGE_W - 2 * MARGIN
    y = PAGE_H - MARGIN

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(MARGIN, y, f"{page['num']}. {page['title']}")
    y -= 26

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 10)
    y = wrap_text(c, page["description"], MARGIN, y, content_w, 14)
    y -= 8

    image_path = ASSETS / page["file"]
    if not image_path.exists():
        raise FileNotFoundError(f"Missing screenshot: {image_path}")

    with PILImage.open(image_path) as img:
        iw, ih = img.size

    max_w = content_w
    max_h = y - MARGIN - FOOTER_H
    draw_w, draw_h = fit_box(iw, ih, max_w, max_h)
    x = MARGIN + (content_w - draw_w) / 2
    img_y = MARGIN + FOOTER_H + (max_h - draw_h) / 2

    c.drawImage(ImageReader(str(image_path)), x, img_y, width=draw_w, height=draw_h, mask="auto")

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(
        PAGE_W / 2,
        MARGIN - 4,
        f"Page {page['num'] + 1} · {page['title']} · DevOps Open Agent",
    )


def build_pdf(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=landscape(letter))
    c.setTitle("DevOps Open Agent Product Tour")
    c.setAuthor("DevOps Open Agent")

    draw_cover(c)
    for page in SCREENSHOTS:
        c.showPage()
        draw_screenshot_page(c, page)

    c.save()
    total_pages = 1 + len(SCREENSHOTS)
    print(f"Wrote {output} ({total_pages} pages)")


def main() -> None:
    if not LOGO.exists():
        raise FileNotFoundError(f"Missing logo: {LOGO}")
    for path in OUTPUTS:
        build_pdf(path)


if __name__ == "__main__":
    main()
