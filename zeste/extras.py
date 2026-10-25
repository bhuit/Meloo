"""Additional local tools, implemented for Windows without Apple frameworks.

Functional reference: Open Tangerine a1ff18575c5000cc50373e851e2bbe7a2b919245,
NativeApp ToolID, FrameImageToolView, MetadataOps and FileAction (GPL-3.0-only
distribution; Satsuma MIT attribution upstream). This implementation is new
Python code: no literal Swift code or proprietary Tangerine assets copied.
"""
from __future__ import annotations

import hashlib
import math
import re
import stat
import struct
from datetime import datetime
from pathlib import Path

OPERATIONS = frozenset({"frame_image", "redact_video", "visualizer", "edit_metadata", "checksum", "duplicate"})
RASTER = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".gif"}
VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".wmv"}
AUDIO = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aiff", ".aif", ".wma", ".aac"}
TAGGED_MEDIA = {".mp3", ".m4a", ".mp4", ".mov", ".mkv", ".webm", ".flac", ".ogg", ".opus", ".wav"}
EMBEDDED_METADATA = TAGGED_MEDIA | {".jpg", ".jpeg", ".tif", ".tiff", ".pdf", ".png", ".docx", ".xlsx", ".pptx"}
CHUNK = 1024 * 1024
MAX_PIXELS = 40_000_000


def _error(message):
    # Lazy import permits Engine to import this dispatcher without a cycle.
    from .engine import ConversionError
    raise ConversionError(message)


def _number(options, key, default, low, high, integer=False):
    value = options.get(key, default)
    if isinstance(value, bool):
        _error(f"Valeur invalide pour {key}.")
    try:
        parsed = float(value)
    except (ValueError, TypeError, OverflowError):
        _error(f"Valeur numérique attendue pour {key}.")
    if not math.isfinite(parsed) or not low <= parsed <= high or (integer and parsed != int(parsed)):
        _error(f"{key} doit être compris entre {low} et {high}" + (" (entier)." if integer else "."))
    return int(parsed) if integer else parsed


def _options(options, allowed):
    unknown = set(options) - set(allowed)
    if unknown:
        _error("Paramètres non pris en charge : " + ", ".join(sorted(map(str, unknown))))


def _source(path, allow_directory=False):
    path = Path(path)
    if not path.is_absolute():
        _error("Sélectionne un chemin local absolu.")
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        _error("Les liens symboliques et points de jonction ne sont pas pris en charge.")
    if not (stat.S_ISREG(info.st_mode) or (allow_directory and stat.S_ISDIR(info.st_mode))):
        _error("Cette opération exige un fichier ordinaire" + (" ou un dossier réel." if allow_directory else "."))
    return path


def _allocate(dest, name, directory=False):
    """Reserve only a fresh output; callers never truncate a pre-existing name."""
    for index in range(1, 10001):
        base = Path(name)
        candidate = dest / (name if index == 1 else f"{base.stem} ({index}){base.suffix}")
        try:
            if directory:
                candidate.mkdir()
            else:
                with candidate.open("xb"):
                    pass
            return candidate
        except FileExistsError:
            continue
    _error("Trop de noms de sortie existants.")


def _copy_bytes(engine, source, target):
    while True:
        engine.check()
        data = source.read(CHUNK)
        if not data:
            break
        target.write(data)
    engine.check()


def _frame(engine, src, options, dest):
    from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter
    import pillow_heif
    pillow_heif.register_heif_opener()
    _options(options, {"padding", "radius", "background", "shadow", "shadow_blur", "shadow_opacity", "shadow_offset", "background_image", "background_blur"})
    if src.suffix.lower() not in RASTER:
        _error("Le cadre accepte uniquement les images matricielles ; SVG non pris en charge ici.")
    padding = _number(options, "padding", 48, 0, 4000, True)
    radius = _number(options, "radius", 24, 0, 4000, True)
    blur = _number(options, "shadow_blur", 16, 0, 200, True)
    opacity = _number(options, "shadow_opacity", 90, 0, 255, True)
    offset = _number(options, "shadow_offset", 8, -200, 200, True)
    shadow = options.get("shadow", True)
    if not isinstance(shadow, bool):
        _error("shadow doit être un booléen.")
    try:
        background = ImageColor.getcolor(options.get("background", "#f4ece2"), "RGBA")
    except (TypeError, ValueError, AttributeError):
        _error("Couleur de fond invalide.")
    # Check before Engine.open_image can silently select the first GIF/TIFF frame.
    with Image.open(src) as header:
        if getattr(header, "n_frames", 1) != 1:
            _error("Le cadre refuse les images animées ou multipages.")
        if header.width * header.height > MAX_PIXELS:
            _error("Image trop grande (40 millions de pixels maximum).")
    engine.check()
    im = engine.open_image(src).convert("RGBA")
    if "radius" not in options:
        radius = min(radius, min(im.size) // 2)
    if radius > min(im.size) / 2:
        _error("Le rayon dépasse la moitié du petit côté de l’image.")
    size = (im.width + padding * 2, im.height + padding * 2)
    if size[0] * size[1] > MAX_PIXELS:
        _error("Le cadre dépasserait 40 millions de pixels.")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=radius, fill=255)
    mask = ImageChops.multiply(mask, im.getchannel("A"))
    im.putalpha(mask)
    canvas = Image.new("RGBA", size, background)
    if options.get("background_image"):
        from PIL import ImageOps
        background_path = _source(Path(options['background_image']))
        backdrop = engine.open_image(background_path).convert('RGBA')
        canvas = ImageOps.fit(backdrop, size, method=Image.Resampling.LANCZOS)
    background_blur = _number(options, 'background_blur', 0, 0, 100)
    if background_blur: canvas = canvas.filter(ImageFilter.GaussianBlur(background_blur))
    if shadow:
        alpha = Image.new("L", size, 0)
        alpha.paste(mask, (padding, padding + offset))
        alpha = alpha.filter(ImageFilter.GaussianBlur(blur)).point(lambda value: value * opacity // 255)
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        layer.putalpha(alpha)
        canvas = Image.alpha_composite(canvas, layer)
    engine.check()
    canvas.alpha_composite(im, (padding, padding))
    output = _allocate(dest, f"{src.stem} — cadre.png")
    engine.save_image(canvas, output, 90)


def _video_size(engine, src):
    log = engine.ff(["-loglevel", "info", "-i", src, "-map", "0:v:0", "-frames:v", "1", "-vf", "showinfo", "-an", "-f", "null", "-"])
    match = re.search(r"\bs:(\d+)x(\d+)\b", log)
    if not match:
        _error("Impossible de lire les dimensions de la première piste vidéo.")
    return tuple(map(int, match.groups()))


def _redact_video(engine, src, options, dest):
    _options(options, {"x", "y", "width", "height", "start", "end", "blur"})
    if src.suffix.lower() not in VIDEO:
        _error("Le masquage exige un fichier vidéo pris en charge.")
    x = _number(options, "x", 0, 0, 100000, True)
    y = _number(options, "y", 0, 0, 100000, True)
    width = _number(options, "width", 100, 1, 16384, True)
    height = _number(options, "height", 100, 1, 16384, True)
    duration = engine.duration(src)
    if not math.isfinite(duration) or duration <= 0:
        _error("Durée vidéo invalide.")
    start = _number(options, "start", 0, 0, duration)
    end = _number(options, "end", duration, 0, duration)
    if end <= start:
        _error("La fin du masquage doit suivre le début.")
    actual_width, actual_height = _video_size(engine, src)
    if x + width > actual_width or y + height > actual_height:
        _error("Le rectangle dépasse les dimensions de la vidéo.")
    engine.check()
    output = _allocate(dest, f"{src.stem} — masquée.mp4")
    if options.get('blur'):
        filt=f"[0:v:0]split[base][region];[region]crop={width}:{height}:{x}:{y},gblur=sigma=12[blur];[base][blur]overlay={x}:{y}:enable='gte(t,{start})*lt(t,{end})',pad=ceil(iw/2)*2:ceil(ih/2)*2[v]"
        engine.ff(['-i',src,'-filter_complex',filt,'-map','[v]','-map','0:a:0?','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-map_metadata','-1','-map_chapters','-1','-movflags','+faststart',output])
        return
    # Re-encode the selected video pixels; do not retain a hidden original track.
    filt = f"drawbox=x={x}:y={y}:w={width}:h={height}:color=black:t=fill:enable='gte(t,{start})*lt(t,{end})',pad=ceil(iw/2)*2:ceil(ih/2)*2"
    engine.ff(["-i", src, "-map", "0:v:0", "-map", "0:a:0?", "-vf", filt,
               "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-map_metadata", "-1", "-map_chapters", "-1",
               "-movflags", "+faststart", output])


def _visualizer(engine, src, options, dest):
    _options(options, {"width", "height", "fps", "color", "background"})
    if src.suffix.lower() not in AUDIO:
        _error("Le visualiseur exige un fichier audio pris en charge.")
    width = _number(options, "width", 1280, 160, 3840, True)
    height = _number(options, "height", 720, 90, 2160, True)
    fps = _number(options, "fps", 25, 1, 60, True)
    if width % 2 or height % 2:
        _error("Les dimensions du visualiseur doivent être paires.")
    colors = []
    for key, default in (("color", "#ff5c00"), ("background", "#15151d")):
        value = options.get(key, default)
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            _error(f"{key} doit être une couleur #RRGGBB.")
        colors.append("0x" + value[1:])
    duration = engine.duration(src)
    if not math.isfinite(duration) or duration <= 0:
        _error("Durée audio invalide.")
    output = _allocate(dest, f"{src.stem} — visualiseur.mp4")
    filt = (f"[0:a:0]asplit=2[a][wave];[wave]showwaves=s={width}x{height}:mode=line:r={fps}:colors={colors[0]}:scale=sqrt:draw=full,format=rgba[w];"
            f"color=c={colors[1]}:s={width}x{height}:r={fps}[bg];[bg][w]overlay=shortest=1:format=auto,format=yuv420p[v]")
    engine.ff(["-i", src, "-filter_complex", filt, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
               "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-t", str(duration),
               "-shortest", "-map_metadata", "-1", "-movflags", "+faststart", output])


def _text_fields(options, allowed):
    _options(options, allowed)
    if not options:
        _error("Renseigne au moins un champ de métadonnées.")
    for key, value in options.items():
        if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 and c not in "\n\t" for c in value):
            _error(f"Métadonnée {key} invalide (texte, 4096 caractères maximum).")
    return options


def _jpeg_exif(engine, src, output, payload):
    """Replace APP1 EXIF while copying the compressed scan bytes unchanged."""
    if len(payload) > 65533:
        _error("Les métadonnées EXIF dépassent la limite JPEG.")
    with src.open("rb") as source, output.open("wb") as target:
        if source.read(2) != b"\xff\xd8":
            _error("En-tête JPEG invalide.")
        target.write(b"\xff\xd8\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload)
        while True:
            engine.check()
            marker = source.read(2)
            if len(marker) != 2 or marker[0] != 255:
                _error("Structure JPEG non prise en charge.")
            while marker[1] == 255:
                following = source.read(1)
                if not following:
                    _error("JPEG tronqué.")
                marker = b"\xff" + following
            if marker[1] in {0, 0xD8, 0xD9, 0x01, *range(0xD0, 0xD8)}:
                _error("Structure JPEG non prise en charge.")
            raw_length = source.read(2)
            if len(raw_length) != 2:
                _error("JPEG tronqué.")
            length = struct.unpack(">H", raw_length)[0]
            if length < 2:
                _error("Segment JPEG invalide.")
            segment = source.read(length - 2)
            if len(segment) != length - 2:
                _error("JPEG tronqué.")
            if marker != b"\xff\xe1" or not segment.startswith(b"Exif\x00\x00"):
                target.write(marker + raw_length + segment)
            if marker == b"\xff\xda":
                _copy_bytes(engine, source, target)
                return


def _image_metadata(engine, src, options, dest):
    from PIL import Image
    values = _text_fields(options, {"author", "comment", "datetime"})
    if "datetime" in values and values["datetime"]:
        try:
            datetime.strptime(values["datetime"], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            _error("Date EXIF attendue : AAAA:MM:JJ HH:MM:SS.")
    with Image.open(src) as im:
        if im.format not in {"JPEG", "TIFF"} or getattr(im, "n_frames", 1) != 1:
            _error("Métadonnées image : JPEG ou TIFF à une seule page uniquement.")
        if im.width * im.height > MAX_PIXELS:
            _error("Image trop grande (40 millions de pixels maximum).")
        im.load()
        exif = im.getexif()
        for key, tag, xp in (("author", 315, 40093), ("comment", 270, 40092)):
            if key in values:
                value = values[key]
                for old in (tag, xp):
                    if old in exif:
                        del exif[old]
                if value:
                    exif[xp] = value.encode("utf-16-le") + b"\0\0"
                    if value.isascii():
                        exif[tag] = value
        if "comment" in values:
            nested = exif.get_ifd(34665)
            nested.pop(37510, None)
            if values["comment"]:
                value = values["comment"]
                nested[37510] = (b"ASCII\0\0\0" + value.encode("ascii") if value.isascii()
                                 else b"UNICODE\0\xfe\xff" + value.encode("utf-16-be"))
            if nested:
                exif[34665] = nested
        if "datetime" in values:
            if values["datetime"]:
                exif[306] = values["datetime"]
            elif 306 in exif:
                del exif[306]
        engine.check()
        if im.format == "JPEG":
            payload = exif.tobytes()
            if len(payload) > 65533:
                _error("Les métadonnées EXIF dépassent la limite JPEG.")
            output = _allocate(dest, f"{src.stem} — métadonnées{src.suffix.lower()}")
            _jpeg_exif(engine, src, output, payload)
        else:
            output = _allocate(dest, f"{src.stem} — métadonnées{src.suffix.lower()}")
            # Pillow's native TIFF writer supports nested EXIF dictionaries;
            # the libtiff compressed path cannot serialize EXIFIFDOffset here.
            im.save(output, format="TIFF", tiffinfo=exif, compression="raw")
            engine.warnings.append(f"{src.name} : copie TIFF non compressée, pixels conservés.")


def _edit_metadata(engine, src, options, dest):
    ext = src.suffix.lower()
    if ext == '.png':
        from PIL import Image, PngImagePlugin
        values = _text_fields(options, {'author','title','comment'})
        with Image.open(src) as im:
            if getattr(im,'n_frames',1) != 1: _error('Métadonnées PNG : les images animées ne sont pas prises en charge.')
            info = PngImagePlugin.PngInfo()
            tags = dict(im.text)
            tags.update({{'author':'Author','title':'Title','comment':'Description'}[key]: value for key,value in values.items()})
            for key,value in tags.items(): info.add_itxt(key,str(value))
            extra = {key:im.info[key] for key in ['icc_profile','dpi','exif','transparency'] if key in im.info}
            im.save(_allocate(dest,f'{src.stem} — métadonnées.png'),pnginfo=info,**extra)
        return
    if ext in {'.docx','.xlsx','.pptx'}:
        import zipfile
        from lxml import etree as ET
        values = _text_fields(options, {'author','title','comment'})
        ns = 'http://purl.org/dc/elements/1.1/'
        with zipfile.ZipFile(src) as original:
            if original.getinfo('docProps/core.xml').file_size > 2_000_000: _error('Métadonnées Office trop volumineuses.')
            tree = ET.fromstring(original.read('docProps/core.xml'),ET.XMLParser(resolve_entities=False,no_network=True))
            for key,value in values.items():
                name = '{'+ns+'}'+{'author':'creator','title':'title','comment':'description'}[key]
                node = tree.find(name)
                if node is None: node = ET.SubElement(tree,name)
                node.text = value
            with zipfile.ZipFile(_allocate(dest,f'{src.stem} — métadonnées{ext}'),'w') as output:
                for entry in original.infolist():
                    engine.check()
                    if entry.filename == 'docProps/core.xml': output.writestr(entry,ET.tostring(tree,encoding='utf-8',xml_declaration=True))
                    else:
                        with original.open(entry) as source,output.open(entry,'w') as target: _copy_bytes(engine,source,target)
        return
    if ext in {".jpg", ".jpeg", ".tif", ".tiff"}:
        return _image_metadata(engine, src, options, dest)
    if ext == ".pdf":
        import pymupdf as fitz
        values = _text_fields(options, {"author", "title", "subject"})
        with fitz.open(src) as doc:
            if doc.needs_pass:
                _error("Déverrouille une copie du PDF avant de modifier ses métadonnées.")
            from .pdf_metadata import rights_only_xmp
            retained_xmp = rights_only_xmp(doc.get_xml_metadata())
            metadata = dict(doc.metadata)
            metadata.update(values)
            doc.set_metadata(metadata)
            if doc.get_xml_metadata():
                if retained_xmp:
                    doc.set_xml_metadata(retained_xmp)
                else:
                    doc.del_xml_metadata()
                engine.warnings.append(f"{src.name} : ancien descriptif XMP retiré ; les mentions de droits sont conservées.")
            engine.check()
            output = _allocate(dest, f"{src.stem} — métadonnées.pdf")
            doc.save(output, garbage=4, deflate=True)
        return
    if ext in TAGGED_MEDIA:
        values = _text_fields(options, {"author", "title", "comment"})
        output = _allocate(dest, f"{src.stem} — métadonnées{ext}")
        args = ["-i", src, "-map", "0", "-c", "copy", "-map_metadata", "0"]
        for key, value in values.items():
            args += ["-metadata", f"{'artist' if key == 'author' else key}={value}"]
        if ext in {".mp4", ".mov", ".m4a"}:
            args += ["-movflags", "+faststart"]
        engine.ff([*args, output])
        return
    import json
    values = _text_fields(options, {'author','title','comment'})
    output = _allocate(dest,src.name+'.metadata.json')
    output.write_text(json.dumps({'source':src.name,'storage':'sidecar','fields':values},ensure_ascii=False,indent=2),encoding='utf8')
    engine.warnings.append(f'{src.name} : informations enregistrées dans une fiche JSON séparée ; le fichier original est inchangé.')


def _checksum(engine, paths, options, dest):
    _options(options, set())
    for src in paths:
        if any(c in src.name for c in "\r\n"):
            _error("Nom de fichier incompatible avec le format SHA-256.")
        digest = hashlib.sha256()
        with src.open("rb") as stream:
            while True:
                engine.check()
                block = stream.read(CHUNK)
                if not block:
                    break
                digest.update(block)
        engine.check()
        output = _allocate(dest, src.name + ".sha256.txt")
        output.write_text(f"{digest.hexdigest()}  {src.name}\n", encoding="utf-8")


def _duplicate(engine, paths, options, dest):
    _options(options, set())
    count = 0

    def copy(source, target, depth=0):
        nonlocal count
        engine.check()
        count += 1
        if count > 100000 or depth > 64:
            _error("Dossier trop volumineux : 100 000 éléments ou 64 niveaux maximum.")
        _source(source, True)
        if source.is_dir():
            for entry in source.iterdir():
                engine.check()
                _source(entry, True)
                child = target / entry.name
                if entry.is_dir():
                    child.mkdir()
                else:
                    with child.open("xb"):
                        pass
                copy(entry, child, depth + 1)
        else:
            with source.open("rb") as incoming, target.open("wb") as outgoing:
                _copy_bytes(engine, incoming, outgoing)

    for src in paths:
        if src.is_dir():
            if dest.resolve().is_relative_to(src.resolve()):
                _error("Le dossier de sortie doit être situé hors du dossier à dupliquer.")
            target = _allocate(dest, src.name + " — copie", True)
        else:
            target = _allocate(dest, f"{src.stem} — copie{src.suffix}")
        copy(src, target)


def dispatch_extra(engine, paths: list[Path], operation: str, options: dict, dest: Path) -> bool:
    """Return False only for an unknown operation; invalid requests raise."""
    if operation not in OPERATIONS:
        return False
    if not isinstance(options, dict) or not paths:
        _error("Fichiers ou options manquants.")
    if operation not in {"checksum", "duplicate"} and len(paths) != 1:
        _error("Cet outil traite un fichier à la fois.")
    dest = Path(dest)
    if not dest.is_dir() or dest.is_symlink():
        _error("Dossier temporaire de sortie invalide.")
    engine.check()
    paths = [_source(path, operation == "duplicate") for path in paths]
    if operation == "checksum":
        _checksum(engine, paths, options, dest)
    elif operation == "duplicate":
        _duplicate(engine, paths, options, dest)
    else:
        {"frame_image": _frame, "redact_video": _redact_video, "visualizer": _visualizer,
         "edit_metadata": _edit_metadata}[operation](engine, paths[0], options, dest)
    engine.check()
    return True
