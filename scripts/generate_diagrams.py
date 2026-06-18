from __future__ import annotations

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "diagrams"
WIDTH = 1920
HEIGHT = 1080


COLORS = {
    "bg": (248, 250, 252),
    "paper": (255, 255, 255),
    "panel": (241, 245, 249),
    "line": (203, 213, 225),
    "line_strong": (148, 163, 184),
    "text": (15, 23, 42),
    "muted": (71, 85, 105),
    "soft_text": (100, 116, 139),
    "blue": (37, 99, 235),
    "green": (22, 163, 74),
    "amber": (217, 119, 6),
    "violet": (124, 58, 237),
    "rose": (219, 39, 119),
    "cyan": (8, 145, 178),
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
    "eyebrow": font("segoeuib.ttf", 18),
    "title": font("segoeuib.ttf", 52),
    "subtitle": font("segoeui.ttf", 25),
    "section": font("segoeuib.ttf", 24),
    "node": font("segoeuib.ttf", 25),
    "body": font("segoeui.ttf", 19),
    "small": font("segoeui.ttf", 16),
    "mono": font("consola.ttf", 17),
}

BODY_LINE_HEIGHT = 24
TITLE_LINE_HEIGHT = 30


def canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (WIDTH, HEIGHT), COLORS["bg"] + (255,))
    draw = ImageDraw.Draw(image)
    draw_background(draw)
    draw_header(draw, title, subtitle)
    draw_footer(draw)
    return image, draw


def draw_background(draw: ImageDraw.ImageDraw) -> None:
    for y in range(0, HEIGHT, 40):
        color = (236, 241, 247) if y % 160 == 0 else (243, 246, 250)
        draw.line((0, y, WIDTH, y), fill=color, width=1)
    for x in range(0, WIDTH, 40):
        color = (236, 241, 247) if x % 160 == 0 else (243, 246, 250)
        draw.line((x, 0, x, HEIGHT), fill=color, width=1)


def draw_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((90, 58), "INTERVIEWER AGENT", font=FONTS["eyebrow"], fill=COLORS["blue"])
    draw.text((90, 88), title, font=FONTS["title"], fill=COLORS["text"])
    draw.text((92, 156), subtitle, font=FONTS["subtitle"], fill=COLORS["muted"])
    draw.line((90, 205, WIDTH - 90, 205), fill=COLORS["line"], width=2)
    draw.line((90, 205, 600, 205), fill=COLORS["blue"], width=4)


def draw_footer(draw: ImageDraw.ImageDraw) -> None:
    draw.line((90, HEIGHT - 74, WIDTH - 90, HEIGHT - 74), fill=COLORS["line"], width=2)
    draw.text(
        (90, HEIGHT - 48),
        "Architecture source: cli.py -> controller.py -> engine.py -> workflow.py",
        font=FONTS["mono"],
        fill=COLORS["soft_text"],
    )
    draw.text(
        (WIDTH - 420, HEIGHT - 48),
        "Generated from scripts/generate_diagrams.py",
        font=FONTS["mono"],
        fill=COLORS["soft_text"],
    )


def draw_shadowed_round_rect(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    width: int = 2,
) -> None:
    x1, y1, x2, y2 = box
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (x1 + 4, y1 + 8, x2 + 4, y2 + 8),
        radius=radius,
        fill=(15, 23, 42, 36),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    image.alpha_composite(shadow)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def section(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    color: tuple[int, int, int],
) -> None:
    draw_shadowed_round_rect(
        image,
        box,
        radius=18,
        fill=(255, 255, 255),
        outline=COLORS["line"],
        width=2,
    )
    x1, y1, x2, _ = box
    draw.rounded_rectangle((x1, y1, x2, y1 + 58), radius=18, fill=COLORS["panel"])
    draw.rectangle((x1, y1 + 40, x2, y1 + 58), fill=COLORS["panel"])
    draw.rounded_rectangle((x1 + 22, y1 + 20, x1 + 34, y1 + 38), radius=4, fill=color)
    draw.text((x1 + 46, y1 + 16), title, font=FONTS["section"], fill=COLORS["text"])


def node(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    lines: list[str],
    color: tuple[int, int, int],
    tag: str | None = None,
) -> None:
    x1, y1, x2, y2 = box
    draw_shadowed_round_rect(
        image,
        box,
        radius=16,
        fill=COLORS["paper"],
        outline=(226, 232, 240),
        width=2,
    )
    draw.rounded_rectangle((x1, y1, x1 + 8, y2), radius=4, fill=color)
    title_max_width = x2 - x1 - (150 if tag else 56)
    title_lines = wrap_pixels(draw, title, FONTS["node"], title_max_width)
    title_y = y1 + 22
    for title_line in title_lines[:2]:
        draw.text((x1 + 28, title_y), title_line, font=FONTS["node"], fill=COLORS["text"])
        title_y += TITLE_LINE_HEIGHT
    if tag:
        chip(draw, (x2 - 74, y1 + 34), tag, color)

    draw_wrapped_lines(
        draw,
        x=x1 + 28,
        y=max(y1 + 64, title_y + 4),
        lines=lines,
        selected_font=FONTS["body"],
        fill=COLORS["muted"],
        max_width=x2 - x1 - 60,
        max_y=y2 - 24,
        line_height=BODY_LINE_HEIGHT,
    )


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
        if text_width(draw, trial, selected_font) <= max_width:
            current = trial
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def draw_wrapped_lines(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    lines: list[str],
    selected_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
    max_y: int,
    line_height: int,
) -> None:
    current_y = y
    for line in lines:
        for part in wrap_pixels(draw, line, selected_font, max_width):
            if current_y + line_height > max_y:
                draw.text((x, max_y - line_height + 4), "...", font=selected_font, fill=fill)
                return
            draw.text((x, current_y), part, font=selected_font, fill=fill)
            current_y += line_height


def text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    selected_font: ImageFont.FreeTypeFont,
) -> int:
    box = draw.textbbox((0, 0), text, font=selected_font)
    return box[2] - box[0]


def chip(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    color: tuple[int, int, int],
) -> None:
    x, y = center
    padding = 14
    text_box = draw.textbbox((0, 0), text, font=FONTS["mono"])
    w = text_box[2] - text_box[0] + padding * 2
    h = 30
    draw.rounded_rectangle(
        (x - w // 2, y - h // 2, x + w // 2, y + h // 2),
        radius=10,
        fill=tint(color, 0.08),
        outline=tint(color, 0.5),
        width=1,
    )
    draw.text((x - w // 2 + padding, y - 11), text, font=FONTS["mono"], fill=color)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int] = COLORS["line_strong"],
    *,
    width: int = 4,
    label: str | None = None,
    label_offset: tuple[int, int] = (0, -28),
) -> None:
    draw.line((start, end), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 16
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
        mid = (
            (start[0] + end[0]) // 2 + label_offset[0],
            (start[1] + end[1]) // 2 + label_offset[1],
        )
        chip(draw, mid, label, color)


def polyline_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    color: tuple[int, int, int] = COLORS["line_strong"],
    *,
    width: int = 4,
    label: str | None = None,
    label_at: tuple[int, int] | None = None,
) -> None:
    for a, b in zip(points, points[1:]):
        draw.line((a, b), fill=color, width=width)
    arrow(draw, points[-2], points[-1], color, width=width)
    if label and label_at:
        chip(draw, label_at, label, color)


def tint(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(channel + (255 - channel) * (1 - amount)) for channel in color)


def architecture_diagram() -> None:
    image, draw = canvas(
        "Architecture actuelle",
        "Le flow produit est déterministe; CrewAI est un moteur interchangeable.",
    )

    section(image, draw, (80, 250, 520, 870), "Interface CLI", COLORS["blue"])
    section(image, draw, (590, 250, 1130, 870), "Application core", COLORS["green"])
    section(image, draw, (1200, 250, 1840, 870), "Moteur IA et données", COLORS["violet"])

    nodes = {
        "entry": (120, 330, 480, 500),
        "ui": (120, 560, 480, 735),
        "controller": (630, 330, 1090, 535),
        "engine": (630, 605, 1090, 825),
        "crew": (1240, 330, 1535, 505),
        "apis": (1580, 330, 1800, 505),
        "models": (1240, 585, 1535, 760),
        "storage": (1580, 585, 1800, 760),
    }

    node(
        image,
        draw,
        nodes["entry"],
        "Entrée Typer",
        ["cli.py", "Options, version, KeyboardInterrupt", "Délègue à run_session()"],
        COLORS["blue"],
        "CLI",
    )
    node(
        image,
        draw,
        nodes["ui"],
        "Rendu Rich",
        ["ui.py ne fait que rendre", "Prévol, revue, pratique", "Feedback et résumé"],
        COLORS["cyan"],
        "UX",
    )
    node(
        image,
        draw,
        nodes["controller"],
        "Contrôleur session",
        [
            "controller.py possède le flow",
            "Prévol, recherche, revue questions",
            "Commandes pratique, résumé, save",
        ],
        COLORS["green"],
        "FLOW",
    )
    node(
        image,
        draw,
        nodes["engine"],
        "Protocole InterviewEngine",
        [
            "ResearchBrief et QuestionDeck",
            "FeedbackReport et SessionSummary",
            "Fake engines pour tests rapides",
        ],
        COLORS["amber"],
        "API",
    )
    node(
        image,
        draw,
        (1240, 330, 1800, 525),
        "Adaptateur CrewAI",
        [
            "workflow.py est le moteur par défaut",
            "Imports CrewAI paresseux",
            "Crews séparés: recherche, coaching, résumé",
        ],
        COLORS["violet"],
        "ADAPTER",
    )
    node(
        image,
        draw,
        (1240, 605, 1518, 785),
        "APIs externes",
        ["Claude via CrewAI LLM", "Serper search", "Website scraping"],
        COLORS["rose"],
    )
    node(
        image,
        draw,
        (1548, 605, 1800, 825),
        "Modèles + JSON",
        ["models.py + parsing.py", "SessionEvent log", "runs/*.json"],
        COLORS["blue"],
    )

    arrow(draw, (480, 415), (630, 415), COLORS["blue"], label="run")
    arrow(draw, (630, 470), (480, 650), COLORS["cyan"], label="render")
    arrow(draw, (860, 535), (860, 605), COLORS["amber"], label="engine calls")
    arrow(draw, (1090, 710), (1240, 430), COLORS["violet"], label="default")
    arrow(draw, (1515, 525), (1380, 605), COLORS["rose"], label="tools")
    polyline_arrow(
        draw,
        [(1090, 455), (1160, 455), (1160, 840), (1674, 840), (1674, 825)],
        COLORS["green"],
        label="records",
        label_at=(1415, 820),
    )

    chip(draw, (1518, 862), "CrewAI peut être remplacé sans réécrire le flow CLI", COLORS["muted"])

    image.convert("RGB").save(OUT_DIR / "interviewer-agent-architecture.png", quality=95)


def step_card(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    number: str,
    title: str,
    lines: list[str],
    color: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = box
    draw_shadowed_round_rect(
        image,
        box,
        radius=18,
        fill=COLORS["paper"],
        outline=(226, 232, 240),
        width=2,
    )
    draw.ellipse((x1 + 24, y1 + 22, x1 + 70, y1 + 68), fill=tint(color, 0.12), outline=color, width=2)
    draw.text((x1 + 39, y1 + 32), number, font=FONTS["mono"], fill=color)
    title_y = y1 + 24
    for title_line in wrap_pixels(draw, title, FONTS["node"], x2 - x1 - 120)[:2]:
        draw.text((x1 + 88, title_y), title_line, font=FONTS["node"], fill=COLORS["text"])
        title_y += TITLE_LINE_HEIGHT
    draw_wrapped_lines(
        draw,
        x=x1 + 30,
        y=max(y1 + 78, title_y + 6),
        lines=lines,
        selected_font=FONTS["body"],
        fill=COLORS["muted"],
        max_width=x2 - x1 - 60,
        max_y=y2 - 24,
        line_height=BODY_LINE_HEIGHT,
    )


def agentic_flow_diagram() -> None:
    image, draw = canvas(
        "Flow d'entretien actuel",
        "Une boucle CLI guidée: revue, génération, pratique, feedback structuré, résumé.",
    )

    steps = [
        ((95, 290, 425, 500), "1", "Boot", ["Load .env", "Validate API keys", "Collect missing inputs"], COLORS["blue"]),
        ((505, 290, 835, 500), "2", "Revue contexte", ["Afficher le contexte", "Éditer un champ", "Restart ou exit"], COLORS["cyan"]),
        ((915, 290, 1245, 500), "3", "Recherche + questions", ["Live dashboard", "ResearchBrief", "QuestionDeck"], COLORS["violet"]),
        ((1325, 290, 1655, 500), "4", "Revue questions", ["Accepter", "Éditer ou retirer", "Régénérer le deck"], COLORS["amber"]),
        ((300, 620, 630, 820), "5", "Pratique", ["help, repeat, hint, example", "next ou exit", "Capture multi-ligne"], COLORS["green"]),
        ((710, 620, 1040, 820), "6", "Feedback structuré", ["Score 1-5", "Ce qui marche", "Signal manquant + révision"], COLORS["rose"]),
        ((1120, 620, 1450, 820), "7", "Résumé session", ["Gaps récurrents", "Réponse forte / faible", "Plan de pratique"], COLORS["violet"]),
        ((1530, 620, 1770, 820), "8", "Sauvegarde", ["SessionRecord", "Events log", "runs/*.json"], COLORS["blue"]),
    ]

    for box, number, title, lines, color in steps:
        step_card(image, draw, box, number, title, lines, color)

    arrow(draw, (425, 395), (505, 395), COLORS["blue"], label="confirm")
    arrow(draw, (835, 395), (915, 395), COLORS["cyan"], label="research")
    arrow(draw, (1245, 395), (1325, 395), COLORS["violet"], label="questions")
    polyline_arrow(
        draw,
        [(1490, 500), (1490, 555), (465, 555), (465, 620)],
        COLORS["amber"],
        label="start practice",
        label_at=(975, 555),
    )
    arrow(draw, (630, 720), (710, 720), COLORS["green"], label="answer")
    arrow(draw, (1040, 720), (1120, 720), COLORS["rose"], label="attempts")
    arrow(draw, (1450, 720), (1530, 720), COLORS["blue"], label="write")
    polyline_arrow(
        draw,
        [(875, 620), (875, 575), (465, 575), (465, 620)],
        COLORS["green"],
        width=3,
        label="revise",
        label_at=(670, 575),
    )
    polyline_arrow(
        draw,
        [(1490, 290), (1490, 240), (1080, 240), (1080, 290)],
        COLORS["amber"],
        width=3,
        label="regenerate",
        label_at=(1285, 240),
    )

    draw.rounded_rectangle((95, 845, 1770, 915), radius=18, fill=COLORS["panel"], outline=COLORS["line"], width=2)
    draw.text((125, 864), "Session events", font=FONTS["section"], fill=COLORS["text"])
    draw.text(
        (330, 868),
        "research_complete -> question_deck_accepted/edited/removed -> attempt_scored -> session_summarized",
        font=FONTS["mono"],
        fill=COLORS["muted"],
    )

    image.convert("RGB").save(OUT_DIR / "interviewer-agent-agentic-flow.png", quality=95)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    architecture_diagram()
    agentic_flow_diagram()
    print(f"Wrote diagrams to {OUT_DIR}")


if __name__ == "__main__":
    main()
