#!/usr/bin/env bash
LIB_V=${LIB_VERSION:-v0}
charmcraft publish-lib "charms.holism.$LIB_V.holism"  # $ TEMPLATE: Filled in by ./scripts/init.sh
