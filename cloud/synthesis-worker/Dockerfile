FROM golang:1.22-bookworm AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /synthesis-worker ./cmd/worker

# Runtime image — includes Yosys, Nextpnr, ecppack, and Python (for tpt_fusion/tpt_alloy)
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    yosys \
    nextpnr-ecp5 \
    prjtrellis \
    python3 \
    python3-pip \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install TPT Python modules (available from the TPT package index or local wheel)
# Uncomment and adjust once packages are published:
# RUN pip3 install --no-cache-dir tpt-fusion tpt-alloy tpt-catalyst

COPY --from=builder /synthesis-worker /usr/local/bin/synthesis-worker

ENV PORT=9090
ENV MAX_CONCURRENT_JOBS=4
ENV WORK_DIR=/tmp/tpt-synthesis

EXPOSE 9090

ENTRYPOINT ["synthesis-worker"]
