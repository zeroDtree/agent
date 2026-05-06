#!/usr/bin/env bash
# Configure uv's default PyPI index to the Tsinghua mirror (or a custom mirror).
# Writes ~/.config/uv/uv.toml. Intended for Linux/macOS; Docker runs this as the app user.

set -euo pipefail

MIRROR_HOST="${UV_MIRROR_HOST:-mirrors.tuna.tsinghua.edu.cn}"
USE_HTTPS="${UV_USE_HTTPS:-1}"

if [[ -n "${UV_INDEX_URL:-}" ]]; then
	MIRROR_URL="${UV_INDEX_URL}"
else
	if [[ "$USE_HTTPS" == "1" ]]; then
		SCHEME="https"
	else
		SCHEME="http"
	fi
	MIRROR_URL="${SCHEME}://${MIRROR_HOST}/pypi/web/simple/"
fi

echo "==> alt_uv_source.sh: uv default index -> ${MIRROR_URL}"

if [[ "${OSTYPE:-}" == linux-gnu* || "${OSTYPE:-}" == darwin* ]]; then
	CONF_DIR="${HOME}/.config/uv"
	CONF_PATH="${CONF_DIR}/uv.toml"
else
	echo "alt_uv_source.sh: only Linux and macOS are supported (OSTYPE=${OSTYPE:-unknown})" >&2
	echo "On Windows, edit: %AppData%\\uv\\uv.toml" >&2
	exit 1
fi

mkdir -p "${CONF_DIR}"

# Overwrite uv.toml with a single default index (typical for CI/images).
if ! cat <<EOF >"${CONF_PATH}"
[[index]]
url = "${MIRROR_URL}"
default = true
EOF
then
	echo "alt_uv_source.sh: failed to write ${CONF_PATH}" >&2
	exit 1
fi

echo "==> Wrote ${CONF_PATH}"
