from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from tchannel import TChannel

@pytest.mark.gen_test
@pytest.mark.call
def test_call_should_get_response():

    import ipdb
    ipdb.set_trace()

    tchannel = TChannel()

    assert tchannel
