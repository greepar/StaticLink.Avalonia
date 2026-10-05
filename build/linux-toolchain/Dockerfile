# Multi-architecture index; deliberately update together with the snapshot/cache key.
FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

ARG DEBIAN_SNAPSHOT=20260901T000000Z
ARG DEPOT_TOOLS_REVISION=8a5434051036b32412a2ecb10c213a72e3f3ccb9
ENV DEBIAN_FRONTEND=noninteractive \
    DEPOT_TOOLS_UPDATE=0 \
    DEPOT_TOOLS_REVISION=${DEPOT_TOOLS_REVISION} \
    LLVM_AR=llvm-ar-16 \
    BUILD_JOBS=4

# HTTP bootstrap uses Debian's signed Release metadata. Do not disable signature checks.
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\ndeb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && apt-get update \
    && printf 'Package: *\nPin: origin "snapshot.debian.org"\nPin-Priority: 1001\n' > /etc/apt/preferences.d/staticlink-snapshot \
    && apt-get dist-upgrade -y --allow-downgrades \
    && apt-get install -y --no-install-recommends \
       ca-certificates git curl python3 python3-six python3-requests python3-httplib2 \
       build-essential ccache clang-16 lld-16 llvm-16 libclang-rt-16-dev ninja-build \
       pkg-config cmake binutils file unzip xz-utils bzip2 patch \
       libfontconfig1-dev libglib2.0-dev libgl1-mesa-dev libpci-dev \
       libx11-dev libxcb1-dev libxext-dev libwayland-dev libexpat1-dev libicu72 libssl3 \
    && for tool in clang clang++ llvm-ar llvm-ranlib llvm-nm; do \
         ln -s "/usr/bin/$tool-16" "/usr/local/bin/$tool"; \
       done \
    && mkdir -p /opt/staticlink \
    && dpkg-query -W > /opt/staticlink/packages.lock \
    && rm -rf /var/lib/apt/lists/*

# Store the pinned checkout inside the image so the runner never selects depot_tools HEAD.
RUN git init /opt/depot_tools \
    && git -C /opt/depot_tools remote add origin https://chromium.googlesource.com/chromium/tools/depot_tools.git \
    && git -C /opt/depot_tools fetch --depth 1 origin "$DEPOT_TOOLS_REVISION" \
    && git -C /opt/depot_tools checkout --detach FETCH_HEAD
ENV DEPOT_TOOLS_DIR=/opt/depot_tools
WORKDIR /src
CMD ["bash"]
