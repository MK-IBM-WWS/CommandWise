#!/usr/bin/env bash

valid_domain() {
    local LC_ALL=C
    local domain="$1" suffix="${1##*.}" label='[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?'
    local pattern="^($label\\.)+$label$"
    [[ ${#domain} -le 253 && "$domain" =~ $pattern && "$suffix" =~ [a-z] &&
        ! "$suffix" =~ ^0x[[:xdigit:]]*$ ]]
}

configured_domain() {
    sed -n 's/^CW_DOMAIN=//p' "$1"
}

valid_tls_certificate() {
    local domain="$1" directory="$2" certificate_key private_key
    local cert="$directory/server.crt" key="$directory/server.key"
    [[ -s "$cert" && -s "$key" ]] &&
        openssl verify -CAfile "$cert" -purpose sslserver -verify_hostname "$domain" "$cert" >/dev/null 2>&1 &&
        certificate_key="$(openssl x509 -in "$cert" -noout -pubkey 2>/dev/null)" &&
        private_key="$(openssl pkey -in "$key" -passin pass: -pubout 2>/dev/null)" &&
        [[ -n "$certificate_key" && "$certificate_key" == "$private_key" ]]
}

ensure_tls_certificate() (
    local domain="$1" directory="$2" stage
    umask 077
    mkdir -p "$directory"
    if valid_tls_certificate "$domain" "$directory"; then
        return 0
    fi

    stage="$(mktemp -d "$directory/.new-XXXXXX")"
    trap 'rm -rf -- "$stage"' EXIT
    if ! openssl req -x509 -newkey rsa:3072 -noenc -sha256 -days 365 \
        -config /dev/null -subj '/CN=CommandWise' \
        -addext "subjectAltName=DNS:$domain" \
        -addext 'basicConstraints=critical,CA:FALSE' \
        -addext 'keyUsage=critical,digitalSignature,keyEncipherment' \
        -addext 'extendedKeyUsage=serverAuth' \
        -keyout "$stage/server.key" -out "$stage/server.crt" 2>"$stage/openssl.log"; then
        cat "$stage/openssl.log" >&2
        return 1
    fi
    valid_tls_certificate "$domain" "$stage"
    chmod 0600 "$stage/server.key"
    chmod 0644 "$stage/server.crt"
    mv -f -- "$stage/server.key" "$stage/server.crt" "$directory/"
    printf 'Самоподписанный сертификат выпущен для %s.\n' "$domain"
)
