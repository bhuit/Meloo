from pathlib import Path
import pytest
import pymupdf as fitz
from zeste.engine import Engine, ConversionError


def make_pdf(path, optimized=False):
    with fitz.open() as doc:
        page=doc.new_page()
        for i in range(30): page.insert_text((30,30+i*20),f'Test line {i}: selectable text preserved')
        page.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(25,20,200,35),'uri':'https://example.com'})
        doc.set_metadata({'title':'Compression test','author':'Test'})
        kwargs=dict(garbage=4,deflate=True,deflate_images=True,deflate_fonts=True,use_objstms=1,compression_effort=100,no_new_id=True) if optimized else {}
        doc.save(path,**kwargs)
    return path


def test_lossless_compression_reduces_size_and_keeps_content(tmp_path):
    source=make_pdf(tmp_path/'source.pdf');before=source.read_bytes()
    result=Path(Engine(output_dir=tmp_path/'out').execute([source],'compress')[0])
    assert result.stat().st_size<len(before)
    with fitz.open(source) as original, fitz.open(result) as compressed:
        assert len(original)==len(compressed)
        assert original.metadata==compressed.metadata
        for a,b in zip(original,compressed):
            assert a.get_text()==b.get_text()
            assert a.get_pixmap(dpi=100).samples==b.get_pixmap(dpi=100).samples
            assert [x.get('uri') for x in a.get_links()]==[x.get('uri') for x in b.get_links()]
    assert source.read_bytes()==before


def test_already_optimized_pdf_never_publishes_a_larger_copy(tmp_path):
    source=make_pdf(tmp_path/'optimized.pdf',True);before=source.read_bytes()
    engine=Engine(output_dir=tmp_path/'out')
    outputs=engine.execute([source],'compress')
    assert outputs==[] and not list((tmp_path/'out').iterdir())
    assert 'aucun nouveau fichier' in engine.warnings[0]
    assert source.read_bytes()==before


def test_mixed_optimized_and_compressible_batch(tmp_path):
    optimized=make_pdf(tmp_path/'optimized.pdf',True)
    source=make_pdf(tmp_path/'source.pdf')
    engine=Engine(output_dir=tmp_path/'out')
    outputs=engine.execute([optimized,source],'compress')
    assert len(outputs)==1 and Path(outputs[0]).stat().st_size<source.stat().st_size
    assert any('déjà optimisé' in x for x in engine.warnings)


def test_unchanged_file_does_not_hide_a_failed_batch(tmp_path):
    optimized=make_pdf(tmp_path/'optimized.pdf',True)
    with pytest.raises(ConversionError,match='Aucun fichier'):
        Engine(output_dir=tmp_path/'out').execute([optimized,tmp_path/'missing.pdf'],'compress')
