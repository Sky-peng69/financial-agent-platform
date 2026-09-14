from PIL import Image, ImageDraw

W, H = 720, 1018
BG = (251, 250, 247)
NAVY = (26, 39, 68)
RED = (200, 16, 46)
GOLD = (181, 138, 69)


def base():
    return Image.new("RGB", (W, H), BG)


def grid_option():
    im = base()
    d = ImageDraw.Draw(im, "RGBA")
    for x in (535, 580, 625, 670):
        d.line((x, 0, x, H), fill=NAVY + (16,), width=1)
    for y in range(110, 880, 64):
        d.line((500, y, 700, y), fill=NAVY + (13,), width=1)
    d.line((540, 180, 665, 90), fill=RED + (70,), width=3)
    d.line((580, 180, 665, 90), fill=GOLD + (85,), width=2)
    for x, y, r, c in ((665, 90, 8, RED), (580, 180, 6, GOLD), (630, 500, 5, NAVY)):
        d.ellipse((x-r, y-r, x+r, y+r), fill=c + (110,))
    return im


def card_option():
    im = base()
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle((0, 0, 34, H), fill=RED + (220,))
    d.rectangle((34, 0, 42, H), fill=GOLD + (190,))
    d.rounded_rectangle((475, 105, 675, 330), radius=18, outline=NAVY + (22,), width=2)
    d.rounded_rectangle((505, 380, 690, 570), radius=18, outline=GOLD + (30,), width=2)
    d.line((500, 215, 620, 160, 665, 245), fill=RED + (90,), width=3, joint="curve")
    d.line((520, 475, 585, 425, 650, 500), fill=NAVY + (50,), width=2, joint="curve")
    for x, y in ((620, 160), (665, 245), (585, 425), (650, 500)):
        d.ellipse((x-6, y-6, x+6, y+6), fill=GOLD + (125,))
    return im


def wave_option():
    im = base()
    d = ImageDraw.Draw(im, "RGBA")
    for i in range(9):
        box = (355-i*12, 650-i*15, 880+i*18, 1140+i*25)
        d.arc(box, 195, 340, fill=NAVY + (13,), width=2)
    for i in range(5):
        d.arc((480-i*18, 540-i*12, 780+i*20, 850+i*14), 195, 340, fill=GOLD + (28,), width=2)
    d.line((510, 675, 675, 565), fill=RED + (70,), width=3)
    d.ellipse((665, 565, 679, 579), fill=RED + (100,))
    return im


canvas = Image.new("RGB", (W * 3 + 80, H + 80), (238, 237, 233))
for idx, (name, fn) in enumerate((("A", grid_option), ("B", card_option), ("C", wave_option))):
    im = fn()
    canvas.paste(im, (20 + idx * (W + 20), 40))
    d = ImageDraw.Draw(canvas)
    d.text((35 + idx * (W + 20), 12), name, fill=NAVY)

canvas.save("docs/competition/assets/body-background-options.png")
