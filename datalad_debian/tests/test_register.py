from datalad.tests.utils import (
    assert_result_count,
    SkipTest,
)


def test_register():
    raise SkipTest("There is no command yet")
    import datalad.api as da
    assert hasattr(da, 'hello_cmd')
    assert_result_count(
        da.hello_cmd(),
        1,
        action='demo')

