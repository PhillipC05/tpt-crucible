FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o observer ./cmd/observer

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/observer .
EXPOSE 8080
CMD ["./observer"]
