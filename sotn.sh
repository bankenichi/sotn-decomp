#!/usr/bin/env sh
# Prefer the standard Linux Go install when PATH is a non-login MCP job env
# (streamable-http often inherits a PATH without /usr/local/go/bin).
if [ -x /usr/local/go/bin/go ]; then
  GO_BIN=/usr/local/go/bin/go
else
  GO_BIN=go
fi
exec "$GO_BIN" run ./tools/sotn-assets "$@"
