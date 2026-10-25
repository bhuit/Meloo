"""Local photo adjustments and flattened annotations, shared by preview/export."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ADJUSTMENTS = [
    ("exposure", "Exposition", 0., -3., 3., .1),
    ("brightness", "Luminosité", 1., 0., 3., .1),
    ("contrast", "Contraste", 1., 0., 3., .1),
    ("highlights", "Hautes lumières", 0., -100., 100., 5.),
    ("shadows", "Ombres", 0., -100., 100., 5.),
    ("color", "Saturation", 1., 0., 3., .1),
    ("temperature", "Température", 0., -100., 100., 5.),
    ("tint", "Teinte", 0., -100., 100., 5.),
    ("sharpness", "Netteté", 1., 0., 3., .1),
    ("clarity", "Clarté", 0., 0., 100., 5.),
    ("dehaze", "Correction du voile", 0., 0., 100., 5.),
    ("denoise", "Réduction du bruit", 0., 0., 100., 5.),
    ("grain", "Grain", 0., 0., 100., 5.),
]


def adjust_photo(image, options):
    values = {}
    for key, title, default, low, high, step in ADJUSTMENTS:
        value = float(options.get(key, default))
        if not math.isfinite(value) or not low <= value <= high: raise ValueError(f"Réglage invalide : {title}")
        values[key] = value
    rgba = image.convert("RGBA"); alpha = rgba.getchannel("A"); im = rgba.convert("RGB")
    if any(values[key] for key in ["exposure", "highlights", "shadows", "temperature", "tint", "dehaze"]):
        a = np.asarray(im, dtype=np.float32) / 255
        a *= 2 ** values["exposure"]
        luminance = a.mean(axis=2, keepdims=True).clip(0, 1)
        a += values["shadows"] / 300 * (1-luminance)**2
        a += values["highlights"] / 300 * luminance**2
        a += np.array([values["temperature"] / 600, values["tint"] / 900, -values["temperature"] / 600], dtype=np.float32)
        if values["dehaze"]:
            low, high = np.percentile(a, [2, 98])
            if high-low > .02:
                corrected = ((a-low)/(high-low)).clip(0, 1)
                strength = values["dehaze"] / 100
                a = a*(1-strength)+corrected*strength
        im = Image.fromarray((a.clip(0, 1)*255).round().astype("uint8"))
    for key, cls in [("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast), ("color", ImageEnhance.Color)]:
        if values[key] != 1: im = cls(im).enhance(values[key])
    if values["denoise"]:
        im = Image.blend(im, im.filter(ImageFilter.MedianFilter(3)), values["denoise"]/100)
    if values["clarity"]:
        im = im.filter(ImageFilter.UnsharpMask(radius=max(2, im.width/160), percent=round(values["clarity"]), threshold=2))
    if values["sharpness"] != 1: im = ImageEnhance.Sharpness(im).enhance(values["sharpness"])
    if values["grain"]:
        noise = np.random.default_rng(42).normal(0, values["grain"]*.12, (im.height, im.width, 1))
        im = Image.fromarray(np.clip(np.asarray(im, dtype=np.float32)+noise, 0, 255).astype("uint8"))
    im.putalpha(alpha)
    return im


def annotate(image, annotations, scale=1.):
    im = image.convert("RGBA").copy()
    for item in annotations:
        kind = item["type"]
        box = [round(x*scale) for x in item["box"]]
        x1,y1,x2,y2 = box
        color = item.get("color", "#ff7845")
        width = max(1, round(item.get("width", max(2, image.width/250))*scale))
        draw = ImageDraw.Draw(im)
        if kind == "redact": draw.rectangle(box, fill=item.get("fill", "black"))
        elif kind == "blur":
            box = (max(0,x1), max(0,y1), min(im.width,x2), min(im.height,y2))
            if box[2] > box[0] and box[3] > box[1]:
                region = im.crop(box).filter(ImageFilter.GaussianBlur(max(4, 18*scale)))
                im.paste(region, box[:2])
        elif kind == "rectangle": draw.rectangle(box, outline=color, width=width)
        elif kind == "ellipse": draw.ellipse(box, outline=color, width=width)
        elif kind in {"arrow", "line", "pen", "highlight"}:
            points = [tuple(round(v*scale) for v in p) for p in item.get("points", [(item["box"][0],item["box"][1]), (item["box"][2],item["box"][3])])]
            if kind == "highlight":
                layer = Image.new("RGBA", im.size); painter = ImageDraw.Draw(layer)
                from PIL import ImageColor
                painter.line(points, fill=ImageColor.getrgb(color)+(90,), width=max(8, width*4), joint="curve")
                im = Image.alpha_composite(im, layer)
            else: draw.line(points, fill=color, width=width, joint="curve")
            if kind == "arrow" and len(points) >= 2:
                a,b = points[0],points[-1]; angle = math.atan2(b[1]-a[1],b[0]-a[0]); length = max(10*scale,width*4)
                draw.polygon([b,(b[0]-length*math.cos(angle-.45),b[1]-length*math.sin(angle-.45)),(b[0]-length*math.cos(angle+.45),b[1]-length*math.sin(angle+.45))],fill=color)
        elif kind in {"text", "number"}:
            size = max(6, round(item.get("font_size", max(16,image.width/28))*scale))
            try: font = ImageFont.truetype("segoeui.ttf", size)
            except OSError: font = ImageFont.load_default(size=size)
            if kind == "number":
                draw.ellipse((x1,y1,x1+size*1.6,y1+size*1.6),fill=color)
                draw.text((x1+size*.8,y1+size*.8), item.get("text","1"), font=font,fill="white",anchor="mm")
            else: draw.text((x1,y1), item.get("text",""), font=font,fill=color)
    return im


def render_photo(image, options):
    im = adjust_photo(image, options)
    crop = options.get("crop")
    if crop:
        x1,y1,x2,y2 = map(int,crop)
        if not 0 <= x1 < x2 <= im.width or not 0 <= y1 < y2 <= im.height: raise ValueError("Zone de recadrage hors image.")
        im = im.crop((x1,y1,x2,y2))
    im = annotate(im, options.get("annotations", []))
    # Do not carry a source EXIF thumbnail or hidden XMP through a redaction.
    im.info.pop('exif', None); im.info.pop('xmp', None)
    return im
