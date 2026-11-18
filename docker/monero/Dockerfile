FROM debian:bookworm-slim

ARG MONERO_VERSION=0.11.3.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl bzip2 \
  && rm -rf /var/lib/apt/lists/*

# Each tarball's SHA-256 comes from the GPG-signed hash list in the Codeberg
# release notes (codeberg.org/wownero/wownero/releases), signed by wowario.
# Verify that signature against utils/gpg_keys/wowario.asc in wownero/wownero
# before adding a version. A version without an entry here refuses to build.
RUN set -eux; \
  tarball="wownero-x86_64-linux-gnu-v${MONERO_VERSION}.tar.bz2"; \
  case "$tarball" in \
    wownero-x86_64-linux-gnu-v0.11.3.0.tar.bz2) \
      wownero_sha256="dddb23ca97575d5538a3a3b6a23e49706db15657e124c2300ea7972cb44a0387" ;; \
    *) \
      echo "No pinned SHA-256 for $tarball; add it to docker/monero/Dockerfile from the signed release hashes" >&2; \
      exit 1 ;; \
  esac; \
  curl -fsSL -o /tmp/wownero.tar.bz2 \
    "https://codeberg.org/wownero/wownero/releases/download/v${MONERO_VERSION}/${tarball}"; \
  echo "${wownero_sha256}  /tmp/wownero.tar.bz2" | sha256sum -c -; \
  tar -xjf /tmp/wownero.tar.bz2 -C /tmp; \
  cp /tmp/wownero-*/wownerod /usr/local/bin/; \
  cp /tmp/wownero-*/wownero-wallet-rpc /usr/local/bin/; \
  rm -rf /tmp/wownero* /tmp/wownero.tar.bz2

COPY entrypoint.sh /usr/local/bin/monero-wallet-rpc-entrypoint
RUN chmod +x /usr/local/bin/monero-wallet-rpc-entrypoint

EXPOSE 34568 18083

ENTRYPOINT ["/usr/local/bin/monero-wallet-rpc-entrypoint"]
