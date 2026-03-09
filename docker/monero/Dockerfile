FROM debian:bookworm-slim

ARG MONERO_VERSION=0.11.3.0

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl bzip2 \
  && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
  curl -fsSL -o /tmp/wownero.tar.bz2 \
    "https://codeberg.org/wownero/wownero/releases/download/v${MONERO_VERSION}/wownero-x86_64-linux-gnu-v${MONERO_VERSION}.tar.bz2"; \
  tar -xjf /tmp/wownero.tar.bz2 -C /tmp; \
  cp /tmp/wownero-*/wownerod /usr/local/bin/; \
  cp /tmp/wownero-*/wownero-wallet-rpc /usr/local/bin/; \
  rm -rf /tmp/wownero* /tmp/wownero.tar.bz2

COPY entrypoint.sh /usr/local/bin/monero-wallet-rpc-entrypoint
RUN chmod +x /usr/local/bin/monero-wallet-rpc-entrypoint

EXPOSE 34568 18083

ENTRYPOINT ["/usr/local/bin/monero-wallet-rpc-entrypoint"]
