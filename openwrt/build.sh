#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    printf 'Usage: %s OUTPUT_DIRECTORY\n' "$0" >&2
    exit 2
fi

source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
olcrtc_root=$(CDPATH='' cd -- "${OLCRTC_ROOT:-$source_dir/../../olcrtc}" && pwd)
mkdir -p "$1"
output_dir=$(CDPATH='' cd -- "$1" && pwd)

arch=${RUPN_ARCH:-arm64}
case "$arch" in
    arm64) export GOARM64=v8.0 ;;
    amd64) export GOAMD64=v1 ;;
    *) printf 'Unsupported RUPN_ARCH: %s\n' "$arch" >&2; exit 2 ;;
esac

cd "$olcrtc_root"
env GOOS=linux GOARCH="$arch" CGO_ENABLED=0 \
    go build -mod=readonly -buildvcs=false -trimpath \
    -ldflags='-s -w -checklinkname=0' -o "$output_dir/rupn" "$source_dir/main.go"
