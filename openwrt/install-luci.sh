#!/bin/sh
set -eu

binary_dir=
if [ "${1:-}" = --binary ]; then
    [ "$#" -ge 3 ] || exit 2
    [ "$(basename -- "$2")" = rupn ] && [ -x "$2" ] || {
        printf 'Expected the executable rupn produced by build.sh\n' >&2
        exit 2
    }
    binary_dir=$(CDPATH='' cd -- "$(dirname -- "$2")" && pwd)
    shift 2
fi

if [ "$#" -lt 1 ]; then
    printf 'Usage: %s [--binary PATH_TO_RUPN] [SSH_OPTIONS] ROOT@ROUTER\n' "$0" >&2
    exit 2
fi

source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
archive() {
    set -- -C "$source_dir/luci" \
        usr/libexec/rpcd/luci.rupn \
        usr/share/luci/menu.d/luci-app-rupn.json \
        usr/share/rpcd/acl.d/luci-app-rupn.json \
        www/luci-static/resources/view/status/rupn.js \
        www/luci-static/resources/view/rupn/podkop.js \
        -C "$source_dir" rupn.init podkop-picker.awk
    if [ -n "$binary_dir" ]; then set -- "$@" -C "$binary_dir" rupn; fi
    tar --format ustar -cf - "$@"
}

archive | ssh "$@" 'set -eu
    umask 077
    test "$(id -u)" -eq 0
    for tool in jq curl flock uci ubus; do
        command -v "$tool" >/dev/null || { printf "Required router command missing: %s\n" "$tool" >&2; exit 1; }
    done
    test -x /etc/init.d/rpcd
    stage=$(mktemp -d /tmp/rupn-luci-install.XXXXXX)
    trap "find \"$stage\" -type f -exec unlink {} \;; find \"$stage\" -depth -type d -exec rmdir {} \;" EXIT
    tar -xof - -C "$stage"
    sh -n "$stage/rupn.init"
    sh -n "$stage/usr/libexec/rpcd/luci.rupn"

    binary=/usr/bin/rupn
    if [ -f "$stage/rupn" ]; then binary="$stage/rupn"; fi
    test -x "$binary"
    "$binary" -h 2>&1 | grep -q -- "-profile" || {
        printf "Install the updated RUPN binary with --binary first.\n" >&2
        exit 1
    }

    podkop_dir=/www/luci-static/resources/view/podkop
    podkop_menu=/usr/share/luci/menu.d/luci-app-podkop.json
    podkop_ready=0
    if [ -f "$podkop_dir/section.js" ] && [ -f "$podkop_menu" ]; then
        upstream_section="$podkop_dir/section.js"
        if grep -Fq "rupn.addConnectionPicker(section);" "$upstream_section"; then
            upstream_section=/etc/rupn/podkop-section.js.original
        fi
        if [ -f "$upstream_section" ] &&
            awk -f "$stage/podkop-picker.awk" "$upstream_section" >"$stage/rupnsection.js" &&
            grep -Fq "require view.podkop.section as section" "$podkop_dir/podkop.js" &&
            sed "s/view\.podkop\.section as section/view.podkop.rupnsection as section/" \
                "$podkop_dir/podkop.js" >"$stage/rupn-view.js" &&
            jq -e "select(.[\"admin/services/podkop\"].action.path | type == \"string\") |
                .[\"admin/services/podkop\"].action.path = \"podkop/rupn-view\"" \
                "$podkop_menu" >"$stage/podkop-menu.json"; then
            podkop_ready=1
        else
            printf "This Podkop version needs the manual SOCKS5 URL shown in Status > RUPN.\n" >&2
        fi
    fi

    put_file() {
        local src="$1" dst="$2" mode="$3" temp
        temp=$(mktemp "${dst}.XXXXXX")
        cp "$src" "$temp"
        chown 0:0 "$temp"
        chmod "$mode" "$temp"
        mv "$temp" "$dst"
    }

    mkdir -p /etc/rupn/tokens
    chmod 700 /etc/rupn /etc/rupn/tokens
    migrated=0
    created_config=0
    if [ ! -e /etc/config/rupn ]; then
        if [ -s /etc/rupn/token ]; then
            "$binary" -check -token-file /etc/rupn/token
            put_file /etc/rupn/token /etc/rupn/tokens/conn_17808 600
            printf "config connection conn_17808\n\toption name \"Основное подключение\"\n\toption enabled 1\n" >"$stage/rupn.config"
            migrated=1
        else
            : >"$stage/rupn.config"
        fi
        put_file "$stage/rupn.config" /etc/config/rupn 600
        created_config=1
    fi

    was_running=0
    pidof rupn >/dev/null && was_running=1
    if [ -f /etc/init.d/rupn ]; then cp /etc/init.d/rupn "$stage/previous.init"; fi
    if [ -f "$stage/rupn" ]; then
        if [ -f /usr/bin/rupn ]; then cp /usr/bin/rupn "$stage/previous.rupn"; fi
        put_file "$stage/rupn" /usr/bin/rupn 755
    fi
    put_file "$stage/rupn.init" /etc/init.d/rupn 755
    if [ "$was_running" -eq 1 ] && ! /etc/init.d/rupn reload; then
        if [ -f "$stage/previous.init" ]; then
            put_file "$stage/previous.init" /etc/init.d/rupn 755
        else
            unlink /etc/init.d/rupn
        fi
        if [ -f "$stage/rupn" ]; then
            if [ -f "$stage/previous.rupn" ]; then
                put_file "$stage/previous.rupn" /usr/bin/rupn 755
            else
                unlink /usr/bin/rupn
            fi
        fi
        if [ "$created_config" -eq 1 ]; then unlink /etc/config/rupn; fi
        if [ "$migrated" -eq 1 ]; then unlink /etc/rupn/tokens/conn_17808; fi
        if [ -f /etc/init.d/rupn ]; then /etc/init.d/rupn restart; fi
        exit 1
    fi
    if [ ! -f "$stage/previous.init" ]; then /etc/init.d/rupn enable; fi
    if [ "$migrated" -eq 1 ] && cmp -s /etc/rupn/token /etc/rupn/tokens/conn_17808; then
        unlink /etc/rupn/token
    fi

    mkdir -p /www/luci-static/resources/view/rupn
    chmod 755 /www/luci-static/resources/view/rupn
    put_file "$stage/usr/libexec/rpcd/luci.rupn" /usr/libexec/rpcd/luci.rupn 755
    for file in usr/share/luci/menu.d/luci-app-rupn.json usr/share/rpcd/acl.d/luci-app-rupn.json \
        www/luci-static/resources/view/status/rupn.js www/luci-static/resources/view/rupn/podkop.js; do
        put_file "$stage/$file" "/$file" 644
    done
    if [ "$podkop_ready" -eq 1 ]; then
        put_file "$stage/rupnsection.js" "$podkop_dir/rupnsection.js" 644
        put_file "$stage/rupn-view.js" "$podkop_dir/rupn-view.js" 644
        if [ "$upstream_section" != "$podkop_dir/section.js" ]; then
            put_file "$upstream_section" "$podkop_dir/section.js" 644
        fi
        put_file "$stage/podkop-menu.json" "$podkop_menu" 644
    fi

    stop_rpcd_processes() {
        local entry pid
        for entry in /proc/[0-9]*/exe; do
            if [ "$(readlink "$entry" 2>/dev/null)" = /sbin/rpcd ]; then
                pid=${entry#/proc/}
                kill "-$1" "${pid%/exe}" 2>/dev/null || true
            fi
        done
    }
    /etc/init.d/rpcd stop
    stop_rpcd_processes TERM
    for attempt in 1 2 3 4 5 6 7 8; do
        if ! ubus list luci.rupn 2>/dev/null | grep -qx luci.rupn; then break; fi
        sleep 1
    done
    if ubus list luci.rupn 2>/dev/null | grep -qx luci.rupn; then
        stop_rpcd_processes KILL
        sleep 1
    fi
    /etc/init.d/rpcd start
    for cache in /tmp/luci-indexcache*.json; do
        if [ -f "$cache" ]; then unlink "$cache"; fi
    done
    ubus -t 8 wait_for luci.rupn
    ubus -v list luci.rupn | grep -q save_profile
'
