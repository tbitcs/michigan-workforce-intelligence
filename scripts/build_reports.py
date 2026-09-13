"""Offline PDF/chart build from reviewed Markdown and public evidence snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import zipfile
from datetime import date
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
from markdown_it import MarkdownIt
from PIL import Image as PILImage
from PIL import ImageDraw
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)
from reports import ROOT, version

SOURCE = ROOT / "reports/2026-09-13-job-continuity"
WIDTH, HEIGHT = landscape(letter)
CONTENT = WIDTH - 84
MD = MarkdownIt("commonmark").enable("table")


def clean(text: str) -> str:
    return (
        text.replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", " - ")
        .replace("→", " to ")
        .replace("\u00a0", " ")
    )


def inline(token) -> str:
    result = []
    links = []
    for child in token.children or []:
        t = child.type
        if t in {"text", "code_inline"}:
            result.append(escape(clean(child.content)))
        elif t in {"softbreak", "hardbreak"}:
            result.append(" ")
        elif t in {"strong_open", "strong_close"}:
            result.append("<b>" if t.endswith("open") else "</b>")
        elif t in {"em_open", "em_close"}:
            result.append("<i>" if t.endswith("open") else "</i>")
        elif t == "link_open":
            url = child.attrGet("href") or ""
            external = url.startswith("https://")
            links.append(external)
            if external:
                result.append('<a color="#126D88" href="' + escape(url, quote=True) + '">')
        elif t == "link_close" and links.pop():
            result.append("</a>")
    return "".join(result)


def styles():
    font = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont("DejaVu", str(font / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(font / "DejaVuSans-Bold.ttf")))
    italic = font / "DejaVuSans-Oblique.ttf"
    pdfmetrics.registerFont(
        TTFont("DejaVu-Oblique", str(italic if italic.exists() else font / "DejaVuSans.ttf"))
    )
    pdfmetrics.registerFontFamily(
        "DejaVu",
        normal="DejaVu",
        bold="DejaVu-Bold",
        italic="DejaVu-Oblique",
        boldItalic="DejaVu-Bold",
    )
    s = getSampleStyleSheet()
    for name in ["BodyText", "Normal", "Heading1", "Heading2", "Heading3", "Title"]:
        s[name].fontName = "DejaVu"
        s[name].textColor = colors.HexColor("#163347")
    s["BodyText"].fontSize = 10
    s["BodyText"].leading = 14
    s["BodyText"].spaceAfter = 8
    s["Title"].fontSize = 25
    s["Title"].leading = 30
    s["Title"].alignment = TA_LEFT
    s["Heading1"].fontSize = 19
    s["Heading1"].leading = 24
    s["Heading2"].fontSize = 14
    s["Heading2"].leading = 19
    for name in ["Heading1", "Heading2", "Heading3"]:
        s[name].keepWithNext = True
    s.add(
        ParagraphStyle(
            "Cell", fontName="DejaVu", fontSize=8.5, leading=11, spaceAfter=0, wordWrap="LTR"
        )
    )
    s.add(ParagraphStyle("Small", parent=s["BodyText"], fontSize=8, leading=11))
    return s


def flow(text: str, s) -> list:
    tokens = MD.parse(text)
    story = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            level = int(token.tag[1])
            story.append(Paragraph(inline(tokens[i + 1]), s["Heading" + str(min(level, 3))]))
            i += 3
        elif token.type == "paragraph_open":
            story.append(Paragraph(inline(tokens[i + 1]), s["BodyText"]))
            i += 3
        elif token.type == "table_open":
            rows = []
            row = []
            i += 1
            while tokens[i].type != "table_close":
                if tokens[i].type == "tr_open":
                    row = []
                elif tokens[i].type == "inline":
                    row.append(Paragraph(inline(tokens[i]), s["Cell"]))
                elif tokens[i].type == "tr_close":
                    rows.append(row)
                i += 1
            table = LongTable(
                rows, colWidths=[CONTENT / len(rows[0])] * len(rows[0]), repeatRows=1, hAlign="LEFT"
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDECF1")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F3F6F8")],
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D3DB")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story += [table, Spacer(1, 12)]
            i += 1
        elif token.type in {"fence", "code_block"}:
            story.append(Paragraph(escape(clean(token.content)).replace("\n", "<br/>"), s["Small"]))
            i += 1
        else:
            i += 1
    return story


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#BDD0DA"))
    canvas.line(42, 35, WIDTH - 42, 35)
    canvas.setFont("DejaVu", 7)
    canvas.drawString(
        42,
        23,
        "Michigan Workforce Intelligence | Provider credits and source periods accompany the analysis",
    )
    canvas.drawRightString(WIDTH - 42, 23, str(doc.page))


def pdf(path: Path, title: str, texts: list[str], charts: list[Path], stamp: str):
    s = styles()
    story = [
        Paragraph(title, s["Title"]),
        Spacer(1, 10),
        Paragraph(
            "Report release " + stamp + " | Evidence review: September 13, 2026", s["BodyText"]
        ),
    ]
    story.append(
        Paragraph(
            "Independent analysis. Observations, limitations and proposals are kept separate. A new build timestamp does not refresh underlying data.",
            s["BodyText"],
        )
    )
    logo = ROOT / "docs/assets/onet-online.png"
    if logo.exists():
        story.append(Image(str(logo), width=130, height=60, hAlign="LEFT"))
    credit = 'O*NET OnLine / National Center for O*NET Development / USDOL/ETA. <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. O*NET® is a USDOL/ETA trademark. Selected wage information is adapted with project analysis; USDOL/ETA has not approved or endorsed these modifications. Original wage source: BLS. Other principal sources: BLS, Census, BEA and Michigan agencies. Full notices follow.'
    story += [Paragraph(credit, s["Small"]), PageBreak()]
    for chart in charts:
        story += [Image(str(chart), width=CONTENT, height=CONTENT * 0.55), PageBreak()]
    for idx, text in enumerate(texts):
        story.extend(flow(text, s))
        if idx < len(texts) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(
        str(path),
        pagesize=(WIDTH, HEIGHT),
        rightMargin=42,
        leftMargin=42,
        topMargin=36,
        bottomMargin=46,
        title=title,
        author="Michigan Workforce Intelligence",
        pageCompression=1,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    reader = PdfReader(path)
    if not reader.pages or any(not (p.extract_text() or "").strip() for p in reader.pages):
        raise ValueError("Empty PDF page")


def chart(
    out: Path,
    name: str,
    title: str,
    ylabel: str,
    lines: list[tuple[str, list, list]],
    source: str,
    *,
    bars: bool = False,
) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6.6))
    fig.patch.set_facecolor("#f9fbfc")
    for label, x, y in lines:
        if bars:
            ax.bar(x, y, label=label, color="#237b99")
        else:
            ax.plot(x, y, label=label, linewidth=2)
    ax.set_title(title, loc="left", fontweight="bold", pad=16)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    if not bars:
        ax.legend(loc="best", fontsize=8)
    fig.text(0.08, 0.025, source, fontsize=8, wrap=True)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    path = out / (name + ".png")
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def generate_data(out: Path, snapshot: dict) -> tuple[str, list[Path]]:
    series = snapshot["indicators"]
    charts = []
    tables = [
        "# Current jobs and price dashboard",
        "",
        f"Snapshot analyzed: {snapshot['analyzed_at']}. Ledger head: `{snapshot['ledger']['head_hash']}`.",
        "",
        "| Geography | Latest month | Unemployment rate | Year-earlier rate | Employed residents | Labor force |",
        "|---|---|---:|---:|---:|---:|",
    ]

    def find(metric, geo):
        return next(s for s in series if s["metric"] == metric and s["geography_code"] == geo)

    def valid(s):
        return [p for p in s["points"] if p["value"] is not None]

    for geo in ["26099", "26125", "26163", "26"]:
        s = find("laus.unemployment_rate", geo)
        points = valid(s)
        if not points:
            raise ValueError("Required county/state series missing")
        last = points[-1]
        prev = str(int(last["date"][:4]) - 1) + last["date"][4:]
        old = next((p["value"] for p in points if p["date"] == prev), None)
        emp = next(
            (p["value"] for p in valid(find("laus.employment", geo)) if p["date"] == last["date"]),
            None,
        )
        labor = next(
            (p["value"] for p in valid(find("laus.labor_force", geo)) if p["date"] == last["date"]),
            None,
        )
        tables.append(
            f"| {s['geography_name']} | {last['date'][:7]} | {last['value']}% | {old}% | {emp:,.0f} | {labor:,.0f} |"
        )
    tables += [
        "",
        "Source: [BLS LAUS](https://www.bls.gov/lau/), not seasonally adjusted. Same-month comparisons; employment counts people by residence, not payroll jobs. Observation/artifact IDs for every chart point are in analysis-snapshot.json.",
        "",
    ]
    for metric, name, title, ylabel in [
        (
            "laus.unemployment_rate",
            "unemployment",
            "Unemployment trends: three counties and Michigan",
            "Percent, not seasonally adjusted",
        ),
        (
            "laus.employment",
            "employment",
            "Resident employment: recovery and recent direction",
            "Index: January 2020 = 100",
        ),
    ]:
        lines = []
        for geo in ["26099", "26125", "26163", "26"]:
            s = find(metric, geo)
            pts = valid(s)
            base = pts[0]["value"]
            lines.append(
                (
                    s["geography_name"],
                    [date.fromisoformat(p["date"]) for p in pts],
                    [
                        p["value"] if metric.endswith("rate") else p["value"] / base * 100
                        for p in pts
                    ],
                )
            )
        charts.append(
            chart(
                out,
                name,
                title,
                ylabel,
                lines,
                "Source: BLS LAUS; project rebasing for employment. Historical observations, not forecasts.",
            )
        )
    for metric, name, title, ylabel in [
        (
            "ces.total_nonfarm",
            "payroll",
            "Michigan payroll jobs",
            "Thousands of jobs, seasonally adjusted",
        ),
        (
            "cpi.all_items",
            "prices",
            "Consumer-price inflation",
            "Year-over-year percent change; unadjusted indexes",
        ),
    ]:
        lines = []
        for s in [v for v in series if v["metric"] == metric]:
            pts = valid(s)
            lookup = {p["date"]: p["value"] for p in pts}
            x = []
            y = []
            for p in pts:
                old = str(int(p["date"][:4]) - 1) + p["date"][4:]
                x.append(date.fromisoformat(p["date"]))
                y.append(
                    (p["value"] / lookup[old] - 1) * 100
                    if metric.startswith("cpi") and old in lookup
                    else math.nan
                    if metric.startswith("cpi")
                    else p["value"]
                )
            lines.append((s["geography_name"], x, y))
        charts.append(
            chart(
                out,
                name,
                title,
                ylabel,
                lines,
                "Source: BLS CES/CPI. Detroit CPI is metro-wide and bimonthly; missing releases are not zero.",
            )
        )
    additional = snapshot["additional_observations"]
    q = [o for o in additional if o["metric"] == "qcew.oty_month3_emplvl_chg"]
    names = {"26": "Michigan", "26099": "Macomb", "26125": "Oakland", "26163": "Wayne"}
    if q:
        charts.append(
            chart(
                out,
                "net-jobs",
                "Payroll employment net change, March 2025 to March 2026",
                "Net jobs; not gross layoffs",
                [("Net change", [names[o["geography_code"]] for o in q], [o["value"] for o in q])],
                "Source: BLS QCEW 2026 Q1, all ownership/industries; year-over-year March employment change.",
                bars=True,
            )
        )
        tables += [
            "## Payroll jobs and wages",
            "",
            "| Geography | March 2026 payroll jobs | Year-over-year net change | Q1 weekly average wage |",
            "|---|---:|---:|---:|",
        ]
        for geo in names:
            lookup = {o["metric"]: o["value"] for o in additional if o["geography_code"] == geo}
            tables.append(
                f"| {names[geo]} | {lookup['qcew.month3_emplvl']:,.0f} | {lookup['qcew.oty_month3_emplvl_chg']:+,.0f} | ${lookup['qcew.avg_wkly_wage']:,.0f} |"
            )
        tables += [
            "",
            "Source: [BLS QCEW](https://www.bls.gov/cew/). Payroll jobs are workplace-based; net change is not a gross job-loss count.",
            "",
        ]
    prices = json.loads(SOURCE.joinpath("interstate-prices.json").read_text())
    earnings = json.loads(SOURCE.joinpath("interstate-earnings.json").read_text())
    price_by = {r["GeoName"]: r for r in prices["rows"]}
    lines = [
        (name, list(range(2008, 2025)), [float(price_by[name][str(y)]) for y in range(2008, 2025)])
        for name in ["Michigan", "Ohio", "California", "Texas"]
    ]
    charts.append(
        chart(
            out,
            "interstate-prices",
            "Relative state price levels over time",
            "BEA RPP: national price level = 100 each year",
            lines,
            "Source: BEA SARPP, all items, current 2008-2024 vintage. Relative prices, not cumulative inflation.",
        )
    )
    rows = earnings["rows"]
    adjusted = [float(r["B20002_001E"]) / (float(price_by[r["NAME"]]["2024"]) / 100) for r in rows]
    charts.append(
        chart(
            out,
            "purchasing-power",
            "Earnings and purchasing power: interstate screening",
            "2024 median earnings / (2024 RPP / 100)",
            [("Screening benchmark", [r["NAME"] for r in rows], adjusted)],
            "Sources: Census ACS 2024 1-year; BEA 2024 RPP. Not occupation-specific wages or household disposable income.",
            bars=True,
        )
    )
    tables += [
        "## Comparable-year interstate screening",
        "",
        "| State | 2024 RPP | Median earnings | Earnings MOE | Adjusted benchmark | Median monthly gross rent |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r, adjusted_value in zip(rows, adjusted, strict=True):
        tables.append(
            f"| {r['NAME']} | {float(price_by[r['NAME']]['2024']):.1f} | ${int(r['B20002_001E']):,} | +/- ${int(r['B20002_001M']):,} | ${adjusted_value:,.0f} | ${int(r['B25064_001E']):,} |"
        )
    tables += [
        "",
        "Sources: [BEA](https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area) and [Census ACS](https://api.census.gov/data/2024/acs/acs1.html). Earnings concern people age 16+ with earnings, across hours/occupations. Rent MOEs remain in the structured snapshot. Rankings are screening comparisons, not causal relocation gains or guaranteed offers.",
    ]
    return "\n".join(tables), charts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    stamp = version(args.version)
    out = ROOT / "output/pdf" / stamp
    if out.exists():
        raise SystemExit("Version directory exists; use a new timestamp rather than overwrite")
    out.mkdir(parents=True)
    snapshot = json.loads(SOURCE.joinpath("analysis-snapshot.json").read_text())
    if not snapshot["ledger"]["valid"] or not snapshot["coverage"]["valid"]:
        raise ValueError("Unverified snapshot")
    data, charts = generate_data(out, snapshot)
    credits = ROOT.joinpath("THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    def read(name):
        return SOURCE.joinpath(name + ".md").read_text(encoding="utf-8")

    primary = [data, read("jobs-context"), read("data-reanalysis"), credits]
    solution_names = [
        "executive-brief",
        "report",
        "matrices",
        "funding",
        "pilot",
        "job-corps",
        "partners-and-signals",
        "evidence",
    ]
    pdf(
        out / "jobs-economic-report.pdf",
        "Michigan jobs and economic trends",
        primary,
        charts,
        stamp,
    )
    pdf(
        out / "executive-brief.pdf",
        "Job continuity: executive companion",
        [read("executive-brief"), read("job-corps"), credits],
        [],
        stamp,
    )
    pdf(
        out / "job-continuity-solutions.pdf",
        "Keep Michigan workers while work changes",
        [read(n) for n in solution_names] + [credits],
        [],
        stamp,
    )
    out.joinpath("jobs-economic-report.md").write_text("\n\n".join(primary), encoding="utf-8")
    for name in [
        "analysis-snapshot.json",
        "interstate-prices.json",
        "interstate-earnings.json",
        "scenario-model.json",
    ]:
        out.joinpath(name).write_bytes(SOURCE.joinpath(name).read_bytes())
    qa = ROOT / "tmp/pdfs" / stamp
    qa.mkdir(parents=True)
    pages = {}
    for path in sorted(out.glob("*.pdf")):
        pages[path.name] = len(PdfReader(path).pages)
        subprocess.run(
            ["pdftoppm", "-scale-to", "1000", "-png", str(path), str(qa / path.stem)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    rendered = sorted(qa.glob("*.png"))
    for batch in range(0, len(rendered), 12):
        sheet = PILImage.new("RGB", (1200, 900), "#e3e8eb")
        draw = ImageDraw.Draw(sheet)
        for j, path in enumerate(rendered[batch : batch + 12]):
            im = PILImage.open(path).convert("RGB")
            im.thumbnail((390, 190))
            x = (j % 3) * 400
            y = (j // 3) * 225
            sheet.paste(im, (x, y + 22))
            draw.text((x + 4, y + 3), path.name[:53], fill="black")
        sheet.save(qa / f"contact-{batch // 12 + 1}.png")
    files = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()
    }
    manifest = {
        "version": stamp,
        "source_commit": os.getenv("REPORT_SOURCE_COMMIT", "working-tree-local"),
        "evidence_review_date": "2026-09-13",
        "snapshot_analyzed_at": snapshot["analyzed_at"],
        "ledger_head": snapshot["ledger"]["head_hash"],
        "pdf_pages": pages,
        "sha256": files,
        "visual_review": "Rendered every page; human/agent visual review required before release.",
    }
    out.joinpath("manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    package = out / f"reports-{stamp}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if p.name != package.name:
                z.write(p, p.name)
    out.joinpath("SHA256SUMS.txt").write_text(
        "\n".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name
            for p in sorted(out.iterdir())
            if p.is_file()
        )
        + "\n"
    )
    print(json.dumps({"version": stamp, "pdf_pages": pages, "output": str(out), "qa": str(qa)}))


if __name__ == "__main__":
    main()
