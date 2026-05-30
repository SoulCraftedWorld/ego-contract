#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/generated/cpp"
mkdir -p "$OUT_DIR"

protoc \
  -I "$ROOT_DIR/proto" \
  --cpp_out="$OUT_DIR" \
  "$ROOT_DIR/proto/ego/v1/ego_common.proto" \
  "$ROOT_DIR/proto/ego/v1/ego_config.proto" \
  "$ROOT_DIR/proto/ego/v1/ego_control.proto" \
  "$ROOT_DIR/proto/ego/v1/ego_data.proto"

echo "Generated C++ files into $OUT_DIR"
