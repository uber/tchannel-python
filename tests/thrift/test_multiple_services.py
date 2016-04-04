# Copyright (c) 2015 Uber Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import (
    absolute_import, print_function, unicode_literals, division
)

import pytest

from tchannel import TChannel, thrift


@pytest.mark.gen_test
def test_inherited_method_names(tmpdir):
    thrift_file = tmpdir.join('service.thrift')
    thrift_file.write('''
        service Base { string hello() }
        service Foo extends Base {}
        service Bar extends Base {}
    ''')

    service = thrift.load(str(thrift_file), 'myservice')

    server = TChannel('server')

    @server.thrift.register(service.Foo, method='hello')
    def foo_hello(request):
        return 'foo'

    @server.thrift.register(service.Bar, method='hello')
    def bar_hello(request):
        return 'bar'

    server.listen()

    client = TChannel('client')

    res = yield client.thrift(service.Foo.hello(), hostport=server.hostport)
    assert res.body == 'foo'

    res = yield client.thrift(service.Bar.hello(), hostport=server.hostport)
    assert res.body == 'bar'
