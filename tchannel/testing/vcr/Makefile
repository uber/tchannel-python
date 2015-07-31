IMPORTS=from tchannel.testing.vcr.thrift import *
DYNAMIC=dynexc=VCRThriftError,dynbase=VCRThriftBase,dynimport="$(IMPORTS)"
PY_OPTIONS=tornado,dynamic,slots,$(DYNAMIC)

# NOTE: Not using utf8strings because dynamic and fastbinary do not quite work
# correctly with it yet. We'll have to manually encode and decode UTF8 before
# calling Thrift.

.PHONY: all proxy

all: proxy

proxy: proxy.thrift
	thrift --gen py:$(PY_OPTIONS) -out . proxy.thrift
	rm proxy/VCRProxy-remote
