#!/usr/bin/env python3
"""
MedMind AI - Investor One-Pager PDF Generator
Output: /opt/medmind/frontend/public/medmind-pitch-deck.pdf
"""
from fpdf import FPDF
from pathlib import Path

OUT = Path("/opt/medmind/frontend/public/medmind-pitch-deck.pdf")

FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

RED        = (220, 38, 38)
DARK       = (15, 23, 42)
GREY       = (80, 95, 115)
LIGHT_GREY = (148, 163, 184)
BG_GREY    = (248, 250, 252)
WHITE      = (255, 255, 255)
GREEN      = (22, 163, 74)
BLUE       = (37, 99, 235)
BORDER     = (220, 228, 238)
PANEL_BG   = (18, 28, 50)


class PitchDeck(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_margins(0, 0, 0)
        self.set_auto_page_break(False)
        self.add_font("dv",  "",  FONT_REG)
        self.add_font("dv",  "B", FONT_BOLD)

    # ------------------------------------------------------------------ helpers
    def fill(self, x, y, w, h, color):
        self.set_fill_color(*color)
        self.rect(x, y, w, h, style="F")

    def txt(self, x, y, w, lh, text, size=8, bold=False, color=DARK, align="L"):
        self.set_xy(x, y)
        self.set_font("dv", "B" if bold else "", size)
        self.set_text_color(*color)
        self.multi_cell(w, lh, text, align=align, new_x="LEFT", new_y="NEXT")

    def badge(self, x, y, text, bg=RED, fg=WHITE, size=6):
        self.set_font("dv", "B", size)
        tw = self.get_string_width(text) + 5
        self.fill(x, y, tw, 5, bg)
        self.set_text_color(*fg)
        self.set_xy(x + 2.5, y + 0.8)
        self.cell(tw - 5, 3.5, text, align="C")

    def hline(self, x, y, w, color=BORDER):
        self.set_draw_color(*color)
        self.set_line_width(0.25)
        self.line(x, y, x + w, y)

    def sec(self, x, y, label, color=DARK, size=7):
        self.set_xy(x, y)
        self.set_font("dv", "B", size)
        self.set_text_color(*color)
        self.cell(80, 4, label.upper())

    def bullet(self, x, y, text, w=58, size=7, color=GREY, dot_color=RED):
        self.set_xy(x, y)
        self.set_font("dv", "B", 8)
        self.set_text_color(*dot_color)
        self.cell(4, 4, ">")
        self.set_xy(x + 4, y)
        self.set_font("dv", "", size)
        self.set_text_color(*color)
        self.multi_cell(w - 4, 3.6, text, new_x="LEFT", new_y="NEXT")

    def check(self, x, y, text, done=True, w=60):
        mark = "+" if done else "o"
        mc   = GREEN if done else LIGHT_GREY
        tc   = DARK  if done else LIGHT_GREY
        self.set_xy(x, y)
        self.set_font("dv", "B", 7)
        self.set_text_color(*mc)
        self.cell(5, 3.6, mark)
        self.set_xy(x + 5, y)
        self.set_font("dv", "", 7)
        self.set_text_color(*tc)
        self.multi_cell(w - 5, 3.6, text, new_x="LEFT", new_y="NEXT")

    def stat_row(self, x, y, val, label, vc=RED, w=55):
        self.set_xy(x, y)
        self.set_font("dv", "B", 10)
        self.set_text_color(*vc)
        self.cell(22, 4.5, val)
        self.set_xy(x + 22, y + 0.5)
        self.set_font("dv", "", 6.5)
        self.set_text_color(*LIGHT_GREY)
        self.multi_cell(w - 22, 3.3, label, new_x="LEFT", new_y="NEXT")


# ================================================================== Build page

def build():
    pdf = PitchDeck()
    pdf.add_page()
    W, H = 297, 210

    # ---- Left dark panel ---------------------------------------------------- #
    pdf.fill(0, 0, 70, H, PANEL_BG)

    # Logo
    pdf.set_xy(7, 8)
    pdf.set_font("dv", "B", 21)
    pdf.set_text_color(*WHITE)
    pdf.cell(24, 10, "Med")
    pdf.set_text_color(*RED)
    pdf.cell(20, 10, "Mind")

    pdf.txt(7, 20, 56, 4, "AI Medical Education Platform", size=7, color=LIGHT_GREY)
    pdf.badge(7, 26, "INVESTOR ONE-PAGER  |  Q2 2026", bg=(30, 42, 68), fg=LIGHT_GREY, size=6)

    # Divider
    pdf.set_draw_color(45, 58, 80)
    pdf.set_line_width(0.2)
    pdf.line(7, 35, 63, 35)

    # Key Metrics
    pdf.txt(7, 37, 56, 3.5, "KEY METRICS", size=6, bold=True, color=LIGHT_GREY)
    metrics = [
        ("8,000+",  "Medical articles (7 languages)"),
        ("82+",     "Clinical modules"),
        ("16",      "Clinical calculators"),
        ("3",       "YouTube channels (EN/ES/AR)"),
        ("200+",    "Videos + Shorts uploaded"),
        ("7",       "Languages supported"),
        ("5",       "User roles (B2C + B2B)"),
        ("~85%",    "Gross margin target"),
    ]
    y = 42
    for val, lbl in metrics:
        pdf.stat_row(7, y, val, lbl)
        y += 7

    # Divider
    pdf.set_draw_color(45, 58, 80)
    pdf.line(7, H - 33, 63, H - 33)

    # Contact
    pdf.txt(7, H - 30, 56, 3.5, "CONTACT", size=6, bold=True, color=LIGHT_GREY)
    pdf.txt(7, H - 25, 56, 4,   "invest@medmind.pro", size=8, bold=True, color=WHITE)
    pdf.txt(7, H - 19, 56, 4,   "medmind.pro/investors", size=7.5, color=RED)
    pdf.txt(7, H - 14, 56, 3.5, "medmind.pro", size=7, color=LIGHT_GREY)

    # ---- Right content area ------------------------------------------------- #
    RX = 74    # right panel start X
    RW = W - RX - 4

    # ---- Hero headline ------------------------------------------------------- #
    pdf.txt(RX, 7, RW, 7, "The AI platform medical education needs",
            size=16, bold=True, color=DARK)
    pdf.txt(RX, 17, RW * 0.88, 3.8,
            "MedMind is a production-ready, multilingual AI medical education platform - "
            "combining adaptive curriculum, AI tutoring, spaced-repetition, clinical calculators, "
            "and automated video content for 12M+ clinicians and students worldwide.",
            size=7.5, color=GREY)

    # ---- ROW 1: Problem | Solution | Market ---------------------------------- #
    COL = (RW - 6) / 3
    cx = [RX, RX + COL + 3, RX + (COL + 3) * 2]
    Y1 = 31

    # -- Problem
    pdf.sec(cx[0], Y1, "The Problem")
    pdf.hline(cx[0], Y1 + 5, COL)
    probs = [
        "Medical tools are fragmented - no single platform covers curriculum, AI tutoring, and clinical decision support",
        "Best tools are English-only, excluding 80%+ of global medical students",
        "Quality prep costs $1,000-5,000/yr - inaccessible for emerging markets",
        "Generic AI (ChatGPT) lacks clinical structure and cites nothing",
    ]
    yp = Y1 + 7
    for p in probs:
        pdf.bullet(cx[0], yp, p, w=COL)
        yp += 8

    # -- Solution
    pdf.sec(cx[1], Y1, "Our Solution", color=RED)
    pdf.hline(cx[1], Y1 + 5, COL)
    sols = [
        "Complete platform: AI tutor + curriculum + flashcards + calculators + video - one product",
        "7 languages at launch - only multilingual medical AI platform in the world",
        "Real-time PubMed integration - answers grounded in current evidence, not static data",
        "Free tier + depth-based premium = organic acquisition with high LTV conversion",
    ]
    ys = Y1 + 7
    for s in sols:
        pdf.bullet(cx[1], ys, s, w=COL, dot_color=RED)
        ys += 8

    # -- Market
    pdf.sec(cx[2], Y1, "Market Size", color=BLUE)
    pdf.hline(cx[2], Y1 + 5, COL)
    mkt = [
        ("$6.4B",    "Global medical e-learning (2024)"),
        ("18% CAGR", "Annual market growth"),
        ("~2M",      "Medical students worldwide"),
        ("~10M",     "Practicing physicians globally"),
        ("$299-699", "Annual spend per student on tools"),
    ]
    ym = Y1 + 7
    for val, lbl in mkt:
        pdf.set_xy(cx[2], ym)
        pdf.set_font("dv", "B", 8.5)
        pdf.set_text_color(*BLUE)
        pdf.cell(22, 3.8, val)
        pdf.set_xy(cx[2] + 22, ym + 0.3)
        pdf.set_font("dv", "", 6.8)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(COL - 23, 3.4, lbl, new_x="LEFT", new_y="NEXT")
        ym += 6

    # ---- ROW 2: Revenue | Traction | Why We Win ----------------------------- #
    Y2 = 90
    pdf.hline(RX, Y2 - 2, RW, color=(200, 210, 222))

    # -- Revenue Model
    pdf.sec(cx[0], Y2, "Revenue Model + Unit Economics")
    pdf.hline(cx[0], Y2 + 5, COL)
    revs = [
        ("B2C Subscriptions", "$15/mo Student  |  $40/mo Pro  |  $299 Lifetime", GREEN),
        ("B2B Institutional",  "$199/mo Clinic  |  Enterprise custom pricing",    BLUE),
        ("Content + API",      "YouTube monetisation  |  SEO affiliate  |  API",  GREY),
    ]
    yr = Y2 + 7
    for name, desc, c in revs:
        pdf.set_xy(cx[0], yr)
        pdf.set_font("dv", "B", 7.5)
        pdf.set_text_color(*c)
        pdf.cell(COL, 3.8, name)
        pdf.set_xy(cx[0], yr + 4)
        pdf.set_font("dv", "", 6.5)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(COL, 3.4, desc, new_x="LEFT", new_y="NEXT")
        yr += 10

    econ = [
        ("Student LTV 24mo", "$360",   GREEN),
        ("Pro LTV 18mo",     "$720",   GREEN),
        ("Clinic LTV 12mo",  "$2,400", GREEN),
        ("Target CAC (SEO)", "< $10",  BLUE),
        ("Gross Margin",     "~85%",   RED),
    ]
    ye = yr + 2
    for lbl, val, c in econ:
        pdf.set_xy(cx[0], ye)
        pdf.set_font("dv", "", 6.5)
        pdf.set_text_color(*GREY)
        pdf.cell(30, 3.6, lbl)
        pdf.set_font("dv", "B", 7)
        pdf.set_text_color(*c)
        pdf.cell(15, 3.6, val)
        ye += 4

    # -- Traction
    pdf.sec(cx[1], Y2, "Traction & Milestones")
    pdf.hline(cx[1], Y2 + 5, COL)
    traction = [
        (True,  "Platform live at medmind.pro (production server)"),
        (True,  "8,000+ multilingual medical articles, Google-indexed"),
        (True,  "82+ clinical modules across 7 specialties"),
        (True,  "16 clinical calculators - multilingual, SEO-optimised"),
        (True,  "3 YouTube channels - EN/ES/AR - 200+ videos uploaded"),
        (True,  "Daily automated Shorts pipeline across all 3 channels"),
        (True,  "7-language localisation complete (incl. Arabic, Turkish)"),
        (True,  "Admin + B2B Clinic tier fully implemented"),
        (False, "First 100 paying users"),
        (False, "University partnership pilot"),
    ]
    yt = Y2 + 7
    for done, text in traction:
        pdf.check(cx[1], yt, text, done=done, w=COL)
        yt += 5

    # -- Competitive Moat
    pdf.sec(cx[2], Y2, "Why MedMind Wins", color=RED)
    pdf.hline(cx[2], Y2 + 5, COL)
    moat = [
        ("Multilingual by design",
         "7 languages at launch. Competitors are English-only. We own the emerging market."),
        ("Complete product, not a feature",
         "Curriculum + AI + flashcards + calculators + video content. All in one platform."),
        ("SEO content flywheel",
         "8,000+ indexed articles compound organic discovery. Near-zero paid CAC."),
        ("Evidence-based AI",
         "PubMed-grounded answers. Clinical accuracy that generic AI tools can't match."),
        ("Automated video pipeline",
         "3 YouTube channels updated daily. Scalable content engine with zero marginal cost."),
        ("Multi-role = institutional sales",
         "Student > Resident > Doctor > Professor > Admin. One platform, institution-wide."),
    ]
    ym2 = Y2 + 7
    for title, desc in moat:
        pdf.set_xy(cx[2], ym2)
        pdf.set_font("dv", "B", 7.5)
        pdf.set_text_color(*RED)
        pdf.cell(COL, 3.5, title)
        pdf.set_xy(cx[2], ym2 + 3.8)
        pdf.set_font("dv", "", 6.5)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(COL, 3.3, desc, new_x="LEFT", new_y="NEXT")
        ym2 += 10

    # ---- ROW 3: Roadmap ----------------------------------------------------- #
    Y3 = H - 47
    pdf.hline(RX, Y3 - 2, RW, color=(200, 210, 222))

    phases = [
        ("Phase 1  |  Q2-Q3 2026", "Launch & Revenue",
         ["Marketing launch + SEO content campaign", "First 100 paying subscribers",
          "App Store / Google Play listing"], RED),
        ("Phase 2  |  Q4 2026-Q1 2027", "B2B & Institutional",
         ["First university pilot (100-300 seats)", "SCORM/LTI integration for LMS",
          "1,000+ monthly active users"], BLUE),
        ("Phase 3  |  2027+", "Scale & API",
         ["Medical AI API for EHR / health-tech", "15+ languages + Series A",
          "10,000+ paying users across B2C + B2B"], GREEN),
    ]

    for i, (phase, title, items, c) in enumerate(phases):
        px = cx[i]
        pdf.badge(px, Y3, phase, bg=c, fg=WHITE, size=6)
        pdf.txt(px, Y3 + 7, COL - 2, 4, title, size=8, bold=True, color=DARK)
        yi = Y3 + 13
        for item in items:
            pdf.bullet(px, yi, item, w=COL - 2, size=6.5, color=GREY, dot_color=c)
            yi += 6

    # ---- Bottom band: The Ask ----------------------------------------------- #
    pdf.fill(RX - 2, H - 13, RW + 6, 13, BG_GREY)
    pdf.hline(RX - 2, H - 13, RW + 6, color=BORDER)

    pdf.txt(RX, H - 10, 115, 3.8,
            "Pre-Seed Round  |  Raising to fund marketing launch, infrastructure scaling & first institutional partnerships.",
            size=7, color=DARK, bold=False)
    pdf.txt(RX + 118, H - 10, 75, 3.8,
            "invest@medmind.pro  |  medmind.pro/investors",
            size=7, bold=True, color=RED)

    # Save
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    sz = OUT.stat().st_size
    print(f"Saved: {OUT}  ({sz // 1024} KB)")


if __name__ == "__main__":
    build()
