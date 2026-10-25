"""Remove descriptive PDF metadata while retaining software and rights notices."""
from copy import deepcopy
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import fromstring

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP = "adobe:ns:meta/"
RIGHTS = "http://ns.adobe.com/xap/1.0/rights/"
DC_RIGHTS = "{http://purl.org/dc/elements/1.1/}rights"
CC = "http://creativecommons.org/ns#"


def rights_only_xmp(xml):
    """Keep standard XMP copyright/license fields, including RDF attribute form.

    Parsing failures intentionally abort the operation before metadata is edited.
    This tool does not promise to anonymize document contents or rights holders.
    """
    if not xml:
        return ""
    if len(xml) > 8_000_000:
        raise ValueError("Bloc XMP trop volumineux pour un nettoyage sûr.")
    root = fromstring(xml)
    output = ET.Element(f"{{{XMP}}}xmpmeta")
    rdf = ET.SubElement(output, f"{{{RDF}}}RDF")
    def is_notice(tag):
        return tag == DC_RIGHTS or tag.startswith(f"{{{RIGHTS}}}") or tag.startswith(f"{{{CC}}}")
    for original in root.iter(f"{{{RDF}}}Description"):
        description = ET.Element(f"{{{RDF}}}Description", {f"{{{RDF}}}about": ""})
        for key, value in original.attrib.items():
            if is_notice(key):
                description.set(key, value)
        for child in original:
            if is_notice(child.tag):
                description.append(deepcopy(child))
        if len(description) or len(description.attrib) > 1:
            rdf.append(description)
    return ET.tostring(output, encoding="unicode") if len(rdf) else ""


def clear_pdf_metadata(document):
    notices = rights_only_xmp(document.get_xml_metadata())
    producer = document.metadata.get("producer", "")
    creator = document.metadata.get("creator", "")
    cleared = {key: "" for key in ("title", "author", "subject", "keywords", "creationDate", "modDate", "trapped")}
    cleared.update(producer=producer, creator=creator)
    document.set_metadata(cleared)
    if notices:
        document.set_xml_metadata(notices)
    else:
        document.del_xml_metadata()
