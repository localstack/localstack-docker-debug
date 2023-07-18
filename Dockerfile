FROM golang as builder

WORKDIR /app
COPY go.sum go.mod ./
RUN go mod download
COPY main.go ./
RUN CGO_ENABLED=0 go build

FROM scratch

COPY --from=builder /app/docker-network-diagnosis /d
ENTRYPOINT ["/d"]