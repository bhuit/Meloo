from pathlib import Path

import pymupdf
import pytest

from zeste.engine import Engine
from zeste.pdf_metadata import rights_only_xmp

XMP = '''<x:xmpmeta xmlns:x="adobe:ns:meta/"
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:r="http://ns.adobe.com/xap/1.0/rights/">
 <rdf:RDF><rdf:Description rdf:about="" r:WebStatement="https://example.org/license">
 <dc:title>Private title</dc:title><dc:creator>Private author</dc:creator>
 <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">Copyright Example</rdf:li></rdf:Alt></dc:rights>
 </rdf:Description></rdf:RDF></x:xmpmeta>'''


@pytest.mark.parametrize("operation", ["strip_metadata", "edit_metadata"])
def test_pdf_notices_survive_metadata_edits(tmp_path, operation):
    source = tmp_path / "input.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((20, 40), "Unchanged content")
        document.set_metadata({"author": "Private author", "title": "Private title", "producer": "MuPDF notice", "creator": "Source software"})
        document.set_xml_metadata(XMP)
        document.save(source)
    original = source.read_bytes()
    result = Path(Engine(output_dir=tmp_path / "out").execute([source], operation, {"title": "New title"})[0])
    with pymupdf.open(result) as document:
        assert document.metadata["producer"] == "MuPDF notice"
        assert document.metadata["creator"] == "Source software"
        assert "Copyright Example" in document.get_xml_metadata()
        assert "https://example.org/license" in document.get_xml_metadata()
        assert "Private title" not in document.get_xml_metadata()
        assert "Private author" not in document.get_xml_metadata()
        assert "Unchanged content" in document[0].get_text()
        if operation == "strip_metadata":
            assert not document.metadata["author"] and not document.metadata["title"]
    assert source.read_bytes() == original


def test_xmp_entities_are_rejected():
    with pytest.raises(Exception):
        rights_only_xmp('<!DOCTYPE x [<!ENTITY e SYSTEM "file:///private">]><x>&e;</x>')
