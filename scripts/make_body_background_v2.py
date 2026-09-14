from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1018
BG = (250, 249, 246)
NAVY = (24, 36, 63)
RED = (194, 18, 48)
GOLD = (177, 133, 59)
GRAY = (100, 105, 112)


def font(size):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size)


def dossier():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 16, H), fill=NAVY + (235,))
    d.rectangle((16, 0, 21, H), fill=RED + (220,))
    d.line((70, 82, 650, 82), fill=GOLD + (160,), width=2)
    d.line((70, 920, 650, 920), fill=GOLD + (160,), width=2)
    d.text((70, 45), "RESEARCH DOSSIER / 01", font=font(16), fill=RED + (220,))
    d.text((545, 45), "YIJIN", font=font(16), fill=NAVY + (155,))
    # 右侧资料卡片堆叠
    for y, w, color in ((170, 150, NAVY), (390, 190, GOLD), (610, 125, RED)):
        d.rounded_rectangle((485, y, 485+w, y+110), radius=8, outline=color+(45,), width=2)
        d.line((505, y+28, 485+w-20, y+28), fill=color+(45,), width=2)
        d.line((505, y+52, 485+w-44, y+52), fill=color+(28,), width=2)
        d.line((505, y+76, 485+w-65, y+76), fill=color+(28,), width=2)
    d.text((492, 300), "EVIDENCE", font=font(13), fill=GRAY+(125,))
    d.text((492, 520), "MODEL", font=font(13), fill=GRAY+(125,))
    d.text((492, 740), "REVIEW", font=font(13), fill=GRAY+(125,))
    # 证据链：有方向的线，而不是随机装饰
    points = [(420, 220), (450, 445), (410, 665), (470, 820)]
    d.line(points, fill=RED+(100,), width=3, joint="curve")
    for i, (x, y) in enumerate(points, 1):
        d.ellipse((x-8, y-8, x+8, y+8), fill=BG+(255,), outline=RED+(150,), width=2)
        d.text((x-5, y-7), str(i), font=font(11), fill=RED+(190,))
    d.text((70, 850), "SOURCE  →  ANALYSIS  →  REVIEW", font=font(14), fill=NAVY+(100,))
    return im


def index():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 42, H), fill=RED+(220,))
    d.rectangle((42, 0, 47, H), fill=GOLD+(210,))
    d.text((85, 55), "01", font=font(54), fill=NAVY+(28,))
    d.text((85, 120), "INDUSTRY / EVIDENCE / DECISION", font=font(15), fill=RED+(190,))
    # 右侧索引刻度和证据定位符
    d.line((590, 150, 590, 850), fill=NAVY+(35,), width=2)
    for y in range(180, 851, 70):
        d.line((578, y, 604, y), fill=NAVY+(55,), width=2)
        d.ellipse((584, y-4, 596, y+4), fill=GOLD+(130,))
    d.arc((360, 260, 700, 600), 200, 330, fill=RED+(80,), width=4)
    d.arc((410, 310, 750, 650), 200, 330, fill=GOLD+(75,), width=3)
    d.line((410, 530, 585, 430), fill=RED+(100,), width=3)
    d.ellipse((578, 426, 592, 440), fill=RED+(150,))
    return im


def conclusion():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((70, 55), "EVIDENCE FIRST", font=font(16), fill=RED+(210,))
    d.line((70, 86, 650, 86), fill=GOLD+(170,), width=2)
    # 结论页的大面积“校验印记”
    d.ellipse((330, 480, 650, 800), outline=NAVY+(20,), width=2)
    d.ellipse((365, 515, 615, 765), outline=GOLD+(40,), width=2)
    d.arc((300, 450, 680, 830), 230, 320, fill=RED+(110,), width=4)
    d.line((475, 640, 570, 575), fill=RED+(110,), width=4)
    d.ellipse((562, 567, 578, 583), fill=GOLD+(140,))
    d.text((70, 870), "TRACEABLE / REVIEWABLE / REUSABLE", font=font(14), fill=NAVY+(100,))
    return im


board = Image.new("RGB", (W*3+80, H+80), (232, 231, 227))
for i, (label, maker) in enumerate((("A  RESEARCH DOSSIER", dossier), ("B  INDEX SYSTEM", index), ("C  EVIDENCE STAMP", conclusion))):
    board.paste(maker(), (20+i*(W+20), 40))
    ImageDraw.Draw(board).text((35+i*(W+20), 12), label, font=font(14), fill=NAVY)
board.save("docs/competition/assets/body-background-options-v2.png")
