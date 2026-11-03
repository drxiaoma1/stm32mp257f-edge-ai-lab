#!/usr/bin/env bash
# Sourced by setup.sh and build.sh. Never fetches from the network.
lab_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
host_tools="$HOME/.local/share/hello-lab-host-tools"
if [[ $(uname -s) != Linux ]]; then
    echo 'Run this command inside Ubuntu, not macOS or PowerShell.' >&2
    return 1
fi
if [[ -d "$host_tools/bin" ]]; then export PATH="$host_tools/bin:$PATH"; fi
load_lab_sdk() {
    local env_file="${SDK_ENV:-$HOME/hello-lab-sdk/environment-setup-cortexa35-ostl-linux}"
    if [[ ! -f "$env_file" ]]; then
        echo 'SDK not installed. Run bash setup.sh first.' >&2
        return 1
    fi
    # SDK environment scripts are not compatible with nounset.
    set +u
    source "$env_file"
    set -u
    [[ ${CROSS_COMPILE:-} == aarch64-ostl-linux- ]] || { echo 'Wrong SDK target.' >&2; return 1; }
    [[ ${OECORE_SDK_VERSION:-} == *v25.06.11* ]] || { echo 'SDK version must match v25.06.11.' >&2; return 1; }
    "${CROSS_COMPILE}gcc" --version | sed -n '1p'
}
