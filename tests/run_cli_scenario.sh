#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <binary> <input-file> [expected-fragment...]" >&2
  exit 2
fi

binary="$1"
input_file="$2"
shift 2

output="$("$binary" < "$input_file")"

for expected in "$@"; do
  if [[ "$output" != *"$expected"* ]]; then
    echo "missing expected output fragment: $expected" >&2
    echo "--- output ---" >&2
    echo "$output" >&2
    exit 1
  fi
done
