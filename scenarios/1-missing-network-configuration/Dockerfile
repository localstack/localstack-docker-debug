FROM golang as builder

WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY main.go ./
RUN CGO_ENABLED=0 go build -o app

FROM scratch

COPY --from=builder /app/app /app
ENTRYPOINT ["/app"]