from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "diagrams"
WIDTH = 1920
HEIGHT = 1080


COLORS = {
    "bg": (5, 10, 20),
    "grid": (16, 36, 58),
    "grid_dim": (9, 23, 39),
    "panel": (10, 20, 35),
    "panel_2": (13, 27, 46),
    "cyan": (44, 232, 255),
    "green": (63, 255, 154),
    "magenta": (255, 74, 221),
    "violet": (147, 112, 255),
    "yellow": (255, 211, 90),
    "orange": (255, 138, 76),
    "white": (232, 246, 255),
    "muted": (133, 159, 184),
    "dark_line": (24, 54, 82),
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts") / name,
        Path("C:/Windows/Fonts") / "segoeui.ttf",
        Path("C:/Windows/Fonts") / "arial.ttf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


FONTS = {
    "title": font("segoeuib.ttf", 56),
    "subtitle": font("segoeui.ttf", 26),
    "section": font("segoeuib.ttf", 24),
    "node": font("segoeuib.ttf", 26),
    "body": font("segoeui.ttf", 19),
    "small": font("segoeui.ttf", 17),
    "mono": font("consola.ttf", 22),
    "mono_small": font("consola.ttf", 18),
}


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(image)
    draw_grid(draw)
    draw_header(draw, title, subtitle)
    draw_footer(draw)
    return image, draw


def draw_grid(draw: ImageDraw.ImageDraw) -> None:
    for x in range(0, WIDTH, 48):
        color = COLORS["grid"] if x % 192 == 0 else COLORS["grid_dim"]
        draw.line((x, 0, x, HEIGHT), fill=color, width=1)
    for y in range(0, HEIGHT, 48):
        color = COLORS["grid"] if y % 192 == 0 else COLORS["grid_dim"]
        draw.line((0, y, WIDTH, y), fill=color, width=1)

    for i in range(8):
        radius = 260 + i * 46
        alpha_color = tuple(max(0, c - i * 16) for c in COLORS["cyan"])
        draw.ellipse(
            (WIDTH - 430 - radius, -170 - radius, WIDTH - 430 + radius, -170 + radius),
            outline=alpha_color,
            width=1,
        )


def draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((90, 58), "INTERVIEWER AGENT", font=FONTS["mono_small"], fill=COLORS["cyan"])
    draw.text((90, 88), title, font=FONTS["title"], fill=COLORS["white"])
    draw.text((92, 158), subtitle, font=FONTS["subtitle"], fill=COLORS["muted"])
    draw.line((90, 205, WIDTH - 90, 205), fill=COLORS["dark_line"], width=2)
    draw.line((90, 205, 600, 205), fill=COLORS["cyan"], width=4)


def draw_footer(draw: ImageDraw.ImageDraw) -> None:
    draw.line((90, HEIGHT - 74, WIDTH - 90, HEIGHT - 74), fill=COLORS["dark_line"], width=2)
    draw.text(
        (90, HEIGHT - 50),
        "CrewAI + Claude Sonnet 4.6 + Serper + Rich CLI",
        font=FONTS["mono_small"],
        fill=COLORS["muted"],
    )
    draw.text(
        (WIDTH - 360, HEIGHT - 50),
        "Generated from repo architecture",
        font=FONTS["mono_small"],
        fill=COLORS["muted"],
    )


def rounded_node(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: list[str],
    accent: tuple[int, int, int],
    tag: str | None = None,
) -> None:
    x1, y1, x2, y2 = box
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((x1 + 6, y1 + 8, x2 + 6, y2 + 8), radius=22, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    image.alpha_composite(shadow)

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle((x1, y1, x2, y2), radius=24, outline=accent + (170,), width=3)
    glow = glow.filter(ImageFilter.GaussianBlur(7))
    image.alpha_composite(glow)

    draw.rounded_rectangle((x1, y1, x2, y2), radius=24, fill=COLORS["panel"], outline=accent, width=2)
    draw.rounded_rectangle((x1 + 10, y1 + 10, x1 + 20, y2 - 10), radius=5, fill=accent)

    if tag:
        tag_w = text_size(draw, tag, FONTS["mono_small"])[0] + 24
        title_w = text_size(draw, title, FONTS["node"])[0]
        if x1 + 42 + title_w < x2 - tag_w - 30:
            draw.rounded_rectangle((x2 - tag_w - 18, y1 + 18, x2 - 18, y1 + 50), radius=12, fill=COLORS["panel_2"], outline=accent, width=1)
            draw.text((x2 - tag_w - 6, y1 + 23), tag, font=FONTS["mono_small"], fill=accent)

    draw.text((x1 + 42, y1 + 26), title, font=FONTS["node"], fill=COLORS["white"])
    body_y = y1 + 70
    max_y = y2 - 24
    for line in lines:
        for part in wrap_pixels(draw, line, FONTS["body"], x2 - x1 - 78):
            if body_y + 23 > max_y:
                draw.text((x1 + 42, body_y), "...", font=FONTS["body"], fill=COLORS["muted"])
                return
            draw.text((x1 + 42, body_y), part, font=FONTS["body"], fill=COLORS["muted"])
            body_y += 25


def wrap_pixels(
    draw: ImageDraw.ImageDraw,
    text: str,
    selected_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if text_size(draw, trial, selected_font)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def label_chip(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    color: tuple[int, int, int],
) -> None:
    x, y = center
    w = text_size(draw, text, FONTS["mono_small"])[0] + 34
    h = 34
    draw.rounded_rectangle((x - w // 2, y - h // 2, x + w // 2, y + h // 2), radius=12, fill=COLORS["panel_2"], outline=color, width=1)
    draw.text((x - w // 2 + 17, y - 12), text, font=FONTS["mono_small"], fill=color)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    width: int = 5,
    label: str | None = None,
    label_offset: tuple[int, int] = (0, -24),
) -> None:
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 18
    spread = 0.48
    p1 = (
        end[0] - length * math.cos(angle - spread),
        end[1] - length * math.sin(angle - spread),
    )
    p2 = (
        end[0] - length * math.cos(angle + spread),
        end[1] - length * math.sin(angle + spread),
    )
    draw.polygon([end, p1, p2], fill=color)
    if label:
        mid = ((start[0] + end[0]) // 2 + label_offset[0], (start[1] + end[1]) // 2 + label_offset[1])
        label_chip(draw, mid, label, color)


def poly_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    color: tuple[int, int, int],
    width: int = 5,
    label: str | None = None,
    label_at: tuple[int, int] | None = None,
) -> None:
    for a, b in zip(points, points[1:]):
        draw.line((a, b), fill=color, width=width)
    arrow(draw, points[-2], points[-1], color, width=width)
    if label and label_at:
        label_chip(draw, label_at, label, color)


def text_size(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[2] - box[0], box[3] - box[1]


def architecture_diagram() -> None:
    image, draw = canvas(
        "CLI Architecture",
        "A notebook workflow repackaged as a polished, testable terminal application.",
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)

    nodes = {
        "terminal": (90, 285, 405, 485),
        "cli": (500, 285, 830, 485),
        "ui": (500, 565, 830, 785),
        "workflow": (915, 350, 1275, 650),
        "crew": (1370, 265, 1775, 510),
        "services": (1370, 575, 1775, 825),
        "storage": (915, 720, 1275, 930),
    }

    rounded_node(
        image,
        draw,
        nodes["terminal"],
        "PowerShell Entry",
        ["Run .\\interview", "Pass company, role, interviewer, attempts", "Local .env stays on machine"],
        COLORS["cyan"],
        "CMD",
    )
    rounded_node(
        image,
        draw,
        nodes["cli"],
        "Typer CLI",
        ["interviewer_agent.cli", "Options, version, validation", "Async run loop"],
        COLORS["green"],
        "CLI",
    )
    rounded_node(
        image,
        draw,
        nodes["ui"],
        "Rich UI Layer",
        ["Operator-console panels", "Spinners for long CrewAI work", "Markdown feedback rendering"],
        COLORS["magenta"],
        "UX",
    )
    rounded_node(
        image,
        draw,
        nodes["workflow"],
        "Workflow Core",
        ["CrewInterviewWorkflow", "Build agents and tasks lazily", "Parse questions into a clean list"],
        COLORS["yellow"],
        "PY",
    )
    rounded_node(
        image,
        draw,
        nodes["crew"],
        "CrewAI Agent Layer",
        ["Research Agent: company + interviewer", "Coach Agent: questions + feedback", "Sequential task process"],
        COLORS["violet"],
        "AGENTS",
    )
    rounded_node(
        image,
        draw,
        nodes["services"],
        "External Intelligence",
        ["Claude Sonnet 4.6 via Anthropic", "SerperDevTool: 3 searches, 5 results", "ScrapeWebsiteTool: 4 pages"],
        COLORS["orange"],
        "APIS",
    )
    rounded_node(
        image,
        draw,
        nodes["storage"],
        "Session Record",
        ["Inputs, questions, attempts, feedback", "Early-exit state", "JSON saved under runs/"],
        COLORS["green"],
        "JSON",
    )

    arrow(draw, (405, 385), (500, 385), COLORS["cyan"], label="launch")
    arrow(draw, (665, 485), (665, 565), COLORS["magenta"], label="render")
    arrow(draw, (830, 385), (915, 470), COLORS["green"], label="inputs")
    arrow(draw, (830, 665), (915, 535), COLORS["magenta"], label="status")
    arrow(draw, (1275, 490), (1370, 395), COLORS["yellow"], label="tasks")
    arrow(draw, (1572, 515), (1572, 585), COLORS["orange"], label="tools")
    arrow(draw, (1275, 560), (1370, 690), COLORS["violet"], label="LLM + web")
    arrow(draw, (1095, 650), (1095, 720), COLORS["green"], label="history")

    label_chip(draw, (1088, 315), "ENV: ANTHROPIC_API_KEY + SERPER_API_KEY", COLORS["cyan"])
    arrow(draw, (1088, 337), (1088, 360), COLORS["cyan"], width=3)

    image.convert("RGB").save(OUT_DIR / "interviewer-agent-architecture.png", quality=95)


def agentic_flow_diagram() -> None:
    image, draw = canvas(
        "Agentic Flow",
        "From interview target inputs to iterative coaching feedback and saved practice history.",
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)

    steps = [
        ((110, 290, 420, 485), "BOOT", ["Load .env", "Validate API keys", "Collect target inputs"], COLORS["cyan"]),
        ((500, 290, 810, 485), "RESEARCH", ["Research Agent", "Company task", "Interviewer task"], COLORS["violet"]),
        ((890, 290, 1200, 485), "QUESTION GEN", ["Coach Agent", "10 role-specific questions", "Research context included"], COLORS["green"]),
        ((1280, 290, 1590, 485), "PARSE", ["Markdown output", "Regex + fallback parser", "Clean question list"], COLORS["yellow"]),
        ((500, 600, 810, 810), "PRACTICE LOOP", ["Show one question", "Capture answer attempt", "next / retry / exit"], COLORS["magenta"]),
        ((890, 600, 1200, 810), "FEEDBACK CREW", ["Coach Agent scores answer", "Strengths + gaps", "Stronger answer outline"], COLORS["orange"]),
        ((1280, 600, 1590, 810), "SESSION SAVED", ["SessionRecord", "Attempts + feedback", "runs/*.json"], COLORS["cyan"]),
    ]

    for box, title, lines, color in steps:
        rounded_node(image, draw, box, title, lines, color)

    arrow(draw, (420, 388), (500, 388), COLORS["cyan"], label="target")
    arrow(draw, (810, 388), (890, 388), COLORS["violet"], label="research")
    arrow(draw, (1200, 388), (1280, 388), COLORS["green"], label="markdown")
    poly_arrow(
        draw,
        [(1435, 485), (1435, 540), (655, 540), (655, 600)],
        COLORS["yellow"],
        label="questions",
        label_at=(1040, 540),
    )
    arrow(draw, (810, 705), (890, 705), COLORS["magenta"], label="answer")
    arrow(draw, (1200, 705), (1280, 705), COLORS["orange"], label="record")

    poly_arrow(
        draw,
        [(1045, 600), (1045, 555), (655, 555), (655, 600)],
        COLORS["magenta"],
        width=4,
        label="retry",
        label_at=(850, 555),
    )
    poly_arrow(
        draw,
        [(655, 810), (655, 865), (1435, 865), (1435, 810)],
        COLORS["cyan"],
        width=4,
        label="next or exit",
        label_at=(1040, 865),
    )

    draw.rounded_rectangle((112, 835, 428, 906), radius=20, fill=COLORS["panel_2"], outline=COLORS["dark_line"], width=2)
    draw.text((142, 855), "Control commands:", font=FONTS["section"], fill=COLORS["white"])
    draw.text((142, 884), "retry = Enter | next/skip | exit/quit/stop", font=FONTS["small"], fill=COLORS["muted"])

    image.convert("RGB").save(OUT_DIR / "interviewer-agent-agentic-flow.png", quality=95)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    architecture_diagram()
    agentic_flow_diagram()
    print(f"Wrote diagrams to {OUT_DIR}")


if __name__ == "__main__":
    main()
