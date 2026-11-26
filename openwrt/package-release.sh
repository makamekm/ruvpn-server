#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    printf 'Usage: %s OUTPUT_DIRECTORY\n' "$0" >&2
    exit 2
fi

root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$1"
out=$(CDPATH='' cd -- "$1" && pwd)
stage=$(mktemp -d)
trap 'find "$stage" -type f -exec unlink {} \;; find "$stage" -depth -type d -exec rmdir {} \;' EXIT

export COPYFILE_DISABLE=1
package_client() {
    arch="$1"
    name="rupn-openwrt-$2"
    dir="$stage/$name"
    RUPN_ARCH="$arch" "$root/openwrt/build.sh" "$dir"
    cp "$root/openwrt/README.md" "$root/openwrt/install-luci.sh" "$root/openwrt/rupn.init" \
        "$root/openwrt/podkop-picker.awk" "$root/LICENSE" "$root/LICENSE.olcrtc" "$dir/"
    cp -R "$root/openwrt/luci" "$dir/"
    tar --format ustar -czf "$out/$name.tar.gz" -C "$stage" "$name"
}

package_client arm64 aarch64
package_client amd64 x86_64

server="$stage/rupn-server-docker"
mkdir "$server"
cp "$root/Dockerfile" "$root/.dockerignore" "$root/.env.example" "$root/README.md" \
    "$root/LICENSE" "$root/LICENSE.olcrtc" "$server/"
cp "$root/docker-compose.build.yml" "$server/compose.yaml"
cp "$root/openwrt/README.md" "$server/OPENWRT.md"
mkdir -p "$server/bin" "$server/src/rupn_server"
cp "$root/bin/olcrtc-linux-amd64" "$root/bin/olcrtc-linux-arm64" "$server/bin/"
cp "$root"/src/rupn_server/*.py "$server/src/rupn_server/"
tar --format ustar -czf "$out/rupn-server-docker.tar.gz" -C "$stage" rupn-server-docker

cd "$out"
set -- rupn-openwrt-aarch64.tar.gz rupn-openwrt-x86_64.tar.gz rupn-server-docker.tar.gz
if command -v sha256sum >/dev/null; then
    sha256sum "$@" >SHA256SUMS
else
    shasum -a 256 "$@" >SHA256SUMS
fi
