"""Render the existing Meloo icon and a simple orange/mint wizard sidebar."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
icon = Image.open(ROOT.parent / "assets/zeste.png").convert("RGBA")
image = Image.new("RGB", (328, 628))
pixels = image.load()
for y in range(image.height):
    for x in range(image.width):
        t = (x / image.width + y / image.height) / 2
        pixels[x, y] = tuple(round(a * (1-t) + b*t) for a, b in zip((32, 37, 41), (18, 61, 54)))
draw = ImageDraw.Draw(image)
draw.ellipse((34, 70, 294, 330), outline=(86, 113, 98), width=2)
icon.thumbnail((188, 188), Image.Resampling.LANCZOS)
image.paste(icon, ((328-icon.width)//2, 105), icon)
fonts = Path("C:/Windows/Fonts")
title = ImageFont.truetype(str(fonts / "segoeuib.ttf"), 44)
small = ImageFont.truetype(str(fonts / "segoeui.ttf"), 21)
draw.text((164, 370), "Meloo", font=title, fill="white", anchor="mm")
draw.text((164, 423), "Vos fichiers, simplement.", font=small, fill=(196, 217, 204), anchor="mm")
draw.rounded_rectangle((88, 487, 154, 495), radius=4, fill=(255, 149, 78))
draw.rounded_rectangle((174, 487, 240, 495), radius=4, fill=(137, 210, 172))
image.save(ROOT / "wizard-large.bmp")
small_image = Image.new("RGB", (110, 110), "white")
icon.thumbnail((90, 90), Image.Resampling.LANCZOS)
small_image.paste(icon, ((110-icon.width)//2, (110-icon.height)//2), icon)
small_image.save(ROOT / "wizard-small.bmp")
