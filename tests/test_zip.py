from pathlib import Path
import zipfile
import pytest
from zeste.catalog import operations, feature_groups
from zeste.engine import Engine


@pytest.mark.parametrize('ext', ['jpg','mp4','mp3','pdf','docx','xlsx','pptx','srt','bin','zip'])
def test_create_zip_accepts_any_file_verbatim(tmp_path,ext):
    source=tmp_path/('original.'+ext);contents=b'original data\x00\xff';source.write_bytes(contents)
    # Even a ZIP input is stored intact, never extracted or converted implicitly.
    assert 'create_zip' in {op.id for op in operations([source],'quick')}
    assert 'create_zip' in {op.id for op in operations([source],'convert')}
    result=Path(Engine(output_dir=tmp_path/'out').execute([source],'create_zip')[0])
    with zipfile.ZipFile(result) as archive:
        assert archive.namelist()==[source.name]
        assert archive.read(source.name)==contents
    assert source.read_bytes()==contents


def test_create_zip_groups_mixed_selection_and_keeps_empty_directories(tmp_path):
    folder=tmp_path/'folder';folder.mkdir();(folder/'empty').mkdir();(folder/'file.txt').write_bytes(b'one')
    source=tmp_path/'photo.jpg';source.write_bytes(b'two')
    result=Engine(output_dir=tmp_path/'out').execute([folder,source],'create_zip')
    assert len(result)==1
    with zipfile.ZipFile(result[0]) as archive:
        assert archive.read('folder/file.txt')==b'one' and archive.read('photo.jpg')==b'two'
        assert 'folder/empty/' in archive.namelist()


def test_zip_output_inside_selected_folder_excludes_own_staging(tmp_path):
    folder=tmp_path/'input';folder.mkdir();(folder/'source.txt').write_bytes(b'original')
    result=Engine(output_dir=folder/'out').execute([folder],'create_zip')
    with zipfile.ZipFile(result[0]) as archive:
        assert archive.read('input/source.txt')==b'original'
        assert not any('.zeste-' in name or name.endswith('.zip') for name in archive.namelist())


def test_zip_switch_is_universal_and_independent_of_compression():
    groups=dict(feature_groups())
    assert any(key=='common/create_zip' for key,_,_ in groups['Tous les fichiers'])
    enabled=lambda key:key!='common/create_zip'
    ops={op.id for op in operations(['image.png'],'quick',enabled=enabled)}
    assert 'create_zip' not in ops and 'compress' in ops
    assert 'create_zip' in {op.id for op in operations(['slides.pptx'],'quick',office=False)}
