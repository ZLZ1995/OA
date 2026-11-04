import io
import zipfile
import pytest
from app.services.workpaper_archives import supported, valid_upload
from app.api.v1.operation_workpapers import Submit
from app.services.workpaper_archives import validate_volumes

def test_volume_sequence():
    validate_volumes(['report.7z.001', 'report.7z.002'])
    validate_volumes(['report.r00', 'report.r01', 'report.rar'])
    for names in [['a.7z.002'], ['a.part1.rar', 'a.part3.rar'], ['a.zip', 'A.ZIP']]:
        with pytest.raises(ValueError):
            validate_volumes(names)

@pytest.mark.parametrize('name', ['a.rar', 'a.7z', 'a.tar.gz', 'a.tar.bz2', 'a.tar.xz', 'a.part1.rar', 'a.7z.001', 'a.7z.012', 'a.zip.002', 'a.z01', 'a.r00', 'A.ZIP'])
def test_names(name):
    assert supported(name)

def test_zip_and_invalid_content():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('report.txt', 'report')
    assert valid_upload('report.zip', stream)
    assert not valid_upload('report.zip', io.BytesIO(b'not zip'))
    assert not valid_upload('report.exe', stream)

def test_split_continuation_does_not_require_archive_header():
    assert valid_upload('report.7z.002', io.BytesIO(b'continuation'))
    assert not valid_upload('report.7z.002', io.BytesIO())

def test_optional_password_preserves_whitespace_and_rejects_other_files():
    args = dict(reviewer_id=1, request_id='request-test', revision=0, material_type='ZIP', file_ids=[12])
    assert Submit(**args).archive_passwords == {}
    assert Submit(**args, archive_passwords={'12': ' secret '}).archive_passwords == {'12': ' secret '}
    with pytest.raises(ValueError):
        Submit(**args, archive_passwords={'13': 'secret'})
