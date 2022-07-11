from datalad.tests.utils_pytest import assert_raises

from ..utils import result_matches


def test_result_matches():
    assert_raises(TypeError, result_matches)
    assert_raises(ValueError, result_matches, 5)
    assert result_matches({})
    assert result_matches(dict(random='something'))
    assert result_matches(dict(random='something'), random='something')
    assert result_matches(dict(random='something'),
                          random=('else', 'something'))
    assert not result_matches(dict(random='something'), random=5)
    assert not result_matches(dict(random='something'), somekey='something')
    assert not result_matches(dict(random='something'),
                              random=('v1', 'v2'))
    assert result_matches(
        dict(msg=('text %s', 'value')),
        msg=(('text %s', 'value'),)
    )
    assert result_matches(
        dict(msg=('text %s', 'value')),
        msg=[('text %s', 'value'),]
    )
