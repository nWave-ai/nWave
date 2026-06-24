#!/bin/sh
# nWave bootstrap installer.
#
# NOTE: Intentional exception to the nWave zero-shell-scripts policy (compare
# scripts/build_offline_bundle.py's generated install-offline.sh). This is a
# curl-able bootstrap that must run *before* any Python tooling exists on the
# target machine, so it cannot be a Python entry point.
#
# Recommended invocation (keeps the terminal on stdin so the prompt works):
#
#   sh -c "$(curl -fsSL https://raw.githubusercontent.com/nWave-ai/nWave/main/scripts/install/install.sh)"
#
# It selects a Python application installer (uv preferred, pipx supported),
# installs the `nwave-ai` CLI, then runs `nwave-ai install`.
#
# Options:
#   -t, --tool <auto|uv|pipx>   Force a tool. Default: auto  (env NWAVE_INSTALLER_TOOL)
#   -y, --yes                   Accept the pipx fallback without prompting
#                               (env NWAVE_ASSUME_YES=1)
#   -h, --help                  Show help and exit.
#
# Deliberately POSIX sh and dependency-free: the only external commands it
# invokes are the installer tools themselves (uv / pipx / nwave-ai).
set -eu

NWAVE_PKG="nwave-ai"
UV_INSTALL_CMD="curl -LsSf https://astral.sh/uv/install.sh | sh"
UV_INSTALL_BREW="brew install uv"
UV_DOCS="https://docs.astral.sh/uv/getting-started/installation/"
PIPX_INSTALL_CMD="python3 -m pip install --user pipx && python3 -m pipx ensurepath"
PIPX_INSTALL_BREW="brew install pipx"
PIPX_DOCS="https://pipx.pypa.io/stable/installation/"

# ---- output helpers -------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RED=$(printf '\033[31m'); C_YEL=$(printf '\033[33m')
    C_GRN=$(printf '\033[32m'); C_BLD=$(printf '\033[1m'); C_RST=$(printf '\033[0m')
else
    C_RED=''; C_YEL=''; C_GRN=''; C_BLD=''; C_RST=''
fi

info() { printf '%s\n' "$*"; }
warn() { printf '%s%s%s\n' "$C_YEL" "$*" "$C_RST" >&2; }
err()  { printf '%sError:%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
ok()   { printf '%s%s%s\n' "$C_GRN" "$*" "$C_RST"; }

has() { command -v "$1" >/dev/null 2>&1; }

usage() {
    info "nWave installer — bootstraps the ${NWAVE_PKG} CLI, then runs 'nwave-ai install'."
    info ""
    info "Usage:"
    info "  sh -c \"\$(curl -fsSL <raw>/scripts/install/install.sh)\" -- [OPTIONS]"
    info "  ./install.sh [OPTIONS]"
    info ""
    info "Options:"
    info "  -t, --tool <auto|uv|pipx>  Installer to use. Default: auto (uv preferred)."
    info "  -y, --yes                  Accept the pipx fallback without prompting."
    info "  -h, --help                 Show this help and exit."
    info ""
    info "Environment:"
    info "  NWAVE_INSTALLER_TOOL       Same as --tool."
    info "  NWAVE_ASSUME_YES=1         Same as --yes."
    info "  NO_COLOR                   Disable colored output."
    info ""
    info "uv is the recommended installer. Learn more: https://docs.astral.sh/uv/"
}

print_uv_instructions() {
    info ""
    info "${C_BLD}Install uv${C_RST} (recommended):"
    info "  ${UV_INSTALL_CMD}"
    info "  ${UV_INSTALL_BREW}   (Homebrew)"
    info "  Docs: ${UV_DOCS}"
}

print_pipx_instructions() {
    info ""
    info "${C_BLD}Install pipx${C_RST}:"
    info "  ${PIPX_INSTALL_CMD}"
    info "  ${PIPX_INSTALL_BREW}   (Homebrew)"
    info "  Docs: ${PIPX_DOCS}"
}

# ---- argument / environment parsing --------------------------------------
TOOL="${NWAVE_INSTALLER_TOOL:-auto}"
case "${NWAVE_ASSUME_YES:-}" in
    1 | true | TRUE | yes | YES) ASSUME_YES=1 ;;
    *) ASSUME_YES=0 ;;
esac

while [ $# -gt 0 ]; do
    case "$1" in
        -t | --tool)
            [ $# -ge 2 ] || { err "--tool requires an argument (auto|uv|pipx)."; exit 2; }
            TOOL="$2"; shift 2 ;;
        --tool=*) TOOL="${1#*=}"; shift ;;
        -y | --yes) ASSUME_YES=1; shift ;;
        -h | --help) usage; exit 0 ;;
        --) shift ;;
        *) err "Unknown option: $1"; usage >&2; exit 2 ;;
    esac
done

case "$TOOL" in
    auto | uv | pipx) ;;
    *) err "Invalid --tool '$TOOL' (expected: auto, uv, or pipx)."; exit 2 ;;
esac

# ---- pipx-fallback confirmation ------------------------------------------
# 0 = accept pipx, 1 = decline, 2 = cannot ask (non-interactive, no --yes).
confirm_pipx() {
    if [ "$ASSUME_YES" = 1 ]; then
        return 0
    fi
    if [ -t 0 ]; then
        printf '%suv is recommended but only pipx was found.%s Continue with pipx? [y/N] ' \
            "$C_YEL" "$C_RST"
        IFS= read -r reply || reply=''
        case "$reply" in
            y | Y | yes | YES | Yes) return 0 ;;
            *) return 1 ;;
        esac
    fi
    return 2
}

# ---- tool selection ------------------------------------------------------
SELECTED=''
case "$TOOL" in
    uv)
        if has uv; then
            SELECTED=uv
        else
            err "--tool uv was requested but 'uv' is not installed."
            print_uv_instructions
            exit 1
        fi
        ;;
    pipx)
        # Explicit --tool pipx is explicit consent: no uv-recommendation prompt.
        if has pipx; then
            SELECTED=pipx
        else
            err "--tool pipx was requested but 'pipx' is not installed."
            print_pipx_instructions
            exit 1
        fi
        ;;
    auto)
        if has uv; then
            SELECTED=uv
        elif has pipx; then
            rc=0
            confirm_pipx || rc=$?
            if [ "$rc" = 0 ]; then
                warn "Proceeding with pipx (uv is recommended)."
                SELECTED=pipx
            elif [ "$rc" = 1 ]; then
                info "Aborted — install uv, then re-run this installer."
                print_uv_instructions
                exit 1
            else
                err "pipx is available but uv is not, and this is a non-interactive shell."
                info "uv is the ${C_BLD}recommended${C_RST} installer. Choose one of:"
                info "  - Install uv (recommended), then re-run:  ${UV_INSTALL_CMD}"
                info "  - Re-run forcing pipx explicitly:         --tool pipx"
                info "  - Re-run accepting the pipx fallback:     --yes  (or NWAVE_ASSUME_YES=1)"
                exit 1
            fi
        else
            err "Neither 'uv' nor 'pipx' is installed — one is required."
            info "uv is the ${C_BLD}preferred${C_RST} installer."
            print_uv_instructions
            print_pipx_instructions
            exit 1
        fi
        ;;
esac

# ---- install -------------------------------------------------------------
case "$SELECTED" in
    uv)
        info "Installing ${NWAVE_PKG} with uv..."
        # --reinstall forces the latest published version even when an older
        # nwave-ai is already installed. A bare `uv tool install` no-ops on an
        # existing install, which silently stranded users on stale builds whose
        # CLI lacked newer subcommands like `doctor` (#74).
        uv tool install --reinstall "$NWAVE_PKG"
        ;;
    pipx)
        info "Installing ${NWAVE_PKG} with pipx..."
        # --force reinstalls to the latest version even when nwave-ai is already
        # present; a plain `pipx install` skips an existing install (#74).
        pipx install --force "$NWAVE_PKG"
        ;;
esac

if has nwave-ai; then
    info "Running 'nwave-ai install'..."
    nwave-ai install
    # Capability probe: the `doctor` subcommand was added after some early
    # nwave-ai builds. The force-latest install above should guarantee it
    # exists, but if a pinned or stale CLI still slips through we must not fail
    # an otherwise healthy install with "Unknown command: doctor" (#74).
    # `doctor --help` exits 0 on any CLI that supports the subcommand and
    # non-zero on one that does not.
    if nwave-ai doctor --help >/dev/null 2>&1; then
        info "Running 'nwave-ai doctor'..."
        # Propagate doctor's exit code: it is the authority on whether the
        # installation is healthy (0) or has a real problem (non-zero). A
        # non-blocking warning is reported by doctor as a passing check (0).
        doctor_rc=0
        nwave-ai doctor || doctor_rc=$?
        if [ "$doctor_rc" -eq 0 ]; then
            ok "nWave installation complete."
        else
            warn "'nwave-ai doctor' reported problems (exit ${doctor_rc}) — review the output above."
        fi
        exit "$doctor_rc"
    else
        warn "Installed nwave-ai predates the 'doctor' health check — skipping it."
        case "$SELECTED" in
            uv)   warn "Upgrade to the latest with: uv tool install --reinstall ${NWAVE_PKG}" ;;
            pipx) warn "Upgrade to the latest with: pipx install --force ${NWAVE_PKG}" ;;
        esac
        ok "nWave installation complete."
    fi
else
    warn "${NWAVE_PKG} was installed but 'nwave-ai' is not on your PATH yet."
    case "$SELECTED" in
        uv)   info "Run: uv tool update-shell   (or add ~/.local/bin to PATH)" ;;
        pipx) info "Run: pipx ensurepath   then open a new shell" ;;
    esac
    info "Then finish with: nwave-ai install"
fi
