from dataclasses import dataclass
from pathlib import Path

IMAGES = {"jpg", "jpeg", "png", "webp", "heic", "heif", "tif", "tiff", "avif", "bmp", "gif", "svg"}
VIDEOS = {"mp4", "mov", "mkv", "webm", "avi", "wmv", "m4v"}
AUDIO = {"mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "aif", "wma", "aac"}
DOCS = {"docx", "doc", "odt", "rtf", "txt", "md", "html", "htm", "epub", "pages"}
SHEETS = {"xlsx", "xls", "ods", "csv", "tsv"}
SLIDES = {"pptx", "ppt", "odp"}
ARCHIVES = {"zip", "tar", "gz", "tgz", "rar", "7z", "bz2", "xz"}


def family(path):
    p = Path(path)
    if p.is_dir(): return "folder"
    ext = p.suffix.lower().lstrip(".")
    for name, extensions in [("image", IMAGES), ("video", VIDEOS), ("audio", AUDIO), ("document", DOCS), ("sheet", SHEETS), ("slides", SLIDES), ("archive", ARCHIVES)]:
        if ext in extensions: return name
    return {"pdf": "pdf", "srt": "subtitle", "vtt": "subtitle"}.get(ext, "file")


@dataclass(frozen=True)
class Operation:
    id: str
    label: str
    icon: str = "↗"
    detail: str = ""


CREATE_ZIP = Operation("create_zip", "Créer ZIP", "▣", "Placer les fichiers ou dossiers sélectionnés dans un ZIP, en conservant les originaux.")
# Stable positions within each file family; the wheel keeps unavailable slots.
DESTINATIONS = {
    "image": ["jpg", "png", "webp", "pdf", "heic", "avif", "tiff", "bmp", "gif"],
    "video": ["mp4", "mov", "mkv", "webm", "gif", "avi", "wmv", "mp3", "wav"],
    "audio": ["mp3", "wav", "m4a", "flac", "ogg", "opus", "aiff", "wma"],
    "pdf": ["docx", "png", "jpg", "pptx", "xlsx", "txt", "md", "html", "epub"],
    "document": ["pdf", "docx", "txt", "epub", "md", "html", "odt", "rtf"],
    "sheet": ["xlsx", "pdf", "csv", "ods", "tsv"],
    "slides": ["pdf", "pptx", "png", "jpg"],
    "subtitle": ["srt", "vtt", "txt"],
    "archive": ["zip", "tar", "7z", "gz"],
    "folder": ["tar", "7z", "gz"], "file": ["tar", "7z"],
}


def destination_order(paths):
    kinds = {family(p) for p in paths}
    return DESTINATIONS.get(next(iter(kinds)), []) if len(kinds) == 1 else []


def format_label(ext):
    return {"docx":"Word (DOCX)", "xlsx":"Excel (XLSX)", "pptx":"PowerPoint (PPTX)", "gz":"GZIP", "md":"Markdown", "txt":"Texte (TXT)"}.get(ext, ext.upper())


TOOLS = {
    "image": [Operation("compress", "Compresser", "↓", "Qualité ou poids cible"), Operation("edit_image", "Retoucher", "✎", "Recadrer, annoter, masquer, régler"), Operation("resize", "Redimensionner", "↔"), Operation("rotate", "Pivoter", "↻"), Operation("collage", "Collage", "▦"), Operation("images_pdf", "Créer un PDF", "▤"), Operation("metadata", "Métadonnées", "ⓘ"), Operation("strip_metadata", "Nettoyer les infos", "◇"), Operation("qr", "Lire un QR code", "▣")],
    "video": [Operation("compress", "Compresser", "↓"), Operation("trim", "Découper", "✂"), Operation("crop_video", "Recadrer", "⊡"), Operation("speed", "Vitesse", "»"), Operation("split_media", "Séparer", "⫶"), Operation("join_media", "Assembler", "+"), Operation("snapshot", "Extraire une image", "▧"), Operation("mute", "Retirer le son", "♪"), Operation("metadata", "Informations", "ⓘ"), Operation("strip_metadata", "Nettoyer les infos", "◇")],
    "audio": [Operation("compress", "Compresser", "↓"), Operation("trim", "Découper", "✂"), Operation("normalize", "Normaliser", "≋"), Operation("bleep", "Masquer par un bip", "♪"), Operation("channels", "Mono / stéréo", "◉"), Operation("speed", "Vitesse", "»"), Operation("split_media", "Séparer", "⫶"), Operation("join_media", "Assembler", "+"), Operation("metadata", "Informations", "ⓘ"), Operation("strip_metadata", "Nettoyer les infos", "◇")],
    "pdf": [Operation("compress", "Compresser", "↓"), Operation("merge_pdf", "Fusionner", "+"), Operation("split_pdf", "Séparer les pages", "⫶"), Operation("reorder_pdf", "Choisir les pages", "▤", "Extraire et réordonner : 3,1,2-4"), Operation("rotate_pdf", "Pivoter les pages", "↻"), Operation("redact_pdf", "Masquer du texte", "▬", "Suppression du texte sélectionné dans une copie"), Operation("metadata", "Métadonnées", "ⓘ"), Operation("strip_metadata", "Nettoyer les infos", "◇")],
    "archive": [Operation("extract", "Extraire", "↗", "Dans un nouveau dossier"), Operation("metadata", "Contenu de l’archive", "ⓘ")],
}
ACTIONS = [Operation("copy", "Copier vers…", "⧉"), Operation("move", "Déplacer vers…", "↗"), Operation("float", "Garder à portée", "◈"), Operation("copy_path", "Copier le chemin", "⌁"), Operation("terminal", "Ouvrir un terminal", ">_"), Operation("share", "Partager sous Windows", "↥")]
ACTIONS = [Operation("reveal", "Afficher le fichier", "↗"), Operation("copy_files", "Copier les fichiers", "⧉"), Operation("copy_path", "Copier le chemin", "⌁"), Operation("duplicate", "Dupliquer", "⧉"), Operation("checksum", "Empreinte SHA-256", "#"), *[x for x in ACTIONS if x.id != "copy_path"]]
TOOLS["image"].insert(2, Operation("frame_image", "Ajouter un fond", "▧", "Marge, arrondis et ombre autour de l’image"))
TOOLS["image"].append(Operation("edit_metadata", "Modifier les infos", "ⓘ", "JPEG et TIFF : auteur et commentaire"))
TOOLS["video"].insert(3, Operation("redact_video", "Masquer une zone", "▬", "Rectangle noir encodé dans une nouvelle vidéo"))
TOOLS["audio"].insert(3, Operation("visualizer", "Onde en vidéo", "≋", "Créer une vidéo MP4 depuis le son"))
for kind in ["audio", "video", "pdf"]:
    TOOLS[kind].append(Operation("edit_metadata", "Modifier les infos", "ⓘ"))


IMAGE_EDITORS = {"edit_image", "annotate_image", "crop_image", "redact_image"}
TOOLS["image"][1:2] = [
    Operation("edit_image", "Retoucher la photo", "✎", "Lumière, couleurs, détail et aperçu"),
    Operation("annotate_image", "Annoter la photo", "✎", "Texte, flèches, formes et dessin"),
    Operation("crop_image", "Recadrer l’image", "⊡", "Zone, dimensions exactes et proportions"),
    Operation("redact_image", "Masquer une zone", "▬", "Aplat ou flou dans une nouvelle copie"),
]
TOOLS["pdf"] = [Operation(x.id, "Organiser les pages" if x.id == "reorder_pdf" else x.label, x.icon, x.detail) for x in TOOLS["pdf"]]


def feature_key(paths, operation):
    if operation in {"compress", "edit_metadata", "create_zip"}: return "common/" + operation
    if operation.startswith("to:"): return "convert/" + operation[3:]
    if operation in {x.id for x in ACTIONS}: return "actions/" + operation
    kinds = {family(p) for p in paths}
    return (next(iter(kinds)) if len(kinds) == 1 else "file") + "/" + operation


def feature_groups():
    groups = [("Tous les fichiers", [("common/create_zip", "Créer un ZIP", CREATE_ZIP.detail), ("common/compress", "Compresser", "Images, médias et PDF optimisés ; autres fichiers dans un ZIP."), ("common/edit_metadata", "Modifier les métadonnées", "Champs intégrés si le format le permet ; fiche JSON séparée sinon.")])]
    for kind, title in [("image", "Images"), ("video", "Vidéo"), ("audio", "Audio"), ("pdf", "PDF"), ("archive", "Archives")]:
        groups.append((title, [(kind+"/"+op.id, op.label, op.detail) for op in TOOLS[kind] if op.id not in {"compress", "edit_metadata"}]))
    formats = sorted({op.id[3:] for ext in ["png", "mp4", "mp3", "pdf", "docx", "xlsx", "pptx", "srt", "zip", "bin"] for op in _available(["sample."+ext], "convert", True)})
    groups.append(("Conversions", [("convert/"+ext, ext.upper(), "Afficher ce format de sortie") for ext in formats]))
    groups.append(("Actions", [("actions/"+op.id, op.label, op.detail) for op in ACTIONS]))
    return groups


def operations(paths, mode="convert", office=False, enabled=None):
    result = _available(paths, mode, office)
    if paths and mode in {"quick", "convert"}: result = [CREATE_ZIP, *[op for op in result if op.id != "create_zip"]]
    return result if enabled is None else [op for op in result if enabled(feature_key(paths, op.id))]


def _available(paths, mode="convert", office=False):
    if not paths: return []
    if mode == "quick":
        tools = operations(paths, "tools", office)
        convert = operations(paths, "convert", office)
        return [op for op in tools if op.id == "compress"] + convert
    if mode == "actions": return [x for x in ACTIONS if x.id != "checksum" or all(Path(p).is_file() for p in paths)]
    families = {family(p) for p in paths}
    if len(families) != 1:
        return [] if mode == "convert" else [Operation("compress", "Compresser", "↓")]
    kind = next(iter(families))
    if mode == "tools":
        result = list(TOOLS.get(kind, []))
        if not any(x.id == "compress" for x in result): result.insert(0, Operation("compress", "Compresser en ZIP", "↓"))
        if kind != "folder" and not any(x.id == "edit_metadata" for x in result): result.append(Operation("edit_metadata", "Modifier les infos", "ⓘ"))
        if len(paths) < 2: result = [x for x in result if x.id not in {"collage", "join_media", "merge_pdf"}]
        if len(paths) > 1: result = [x for x in result if x.id not in IMAGE_EDITORS | {"reorder_pdf", "edit_metadata"}]
        if kind == "image" and any(Path(p).suffix.lower() == ".svg" for p in paths): result = [x for x in result if x.id != "frame_image"]
        return result
    outputs = list(DESTINATIONS.get(kind, []))
    if not office:
        if kind == "slides": outputs = []
        if kind == "sheet": outputs = ["xlsx", "csv", "tsv"]
        if kind == "document" and any(Path(p).suffix.lower() in {".doc", ".pages"} for p in paths): outputs = []
    ext = {Path(p).suffix.lower().lstrip(".") for p in paths}
    return [Operation("to:" + x, format_label(x), "↗", "Première image" if kind == "image" and ".gif" in {Path(p).suffix.lower() for p in paths} else "") for x in outputs if ext != {x}]
