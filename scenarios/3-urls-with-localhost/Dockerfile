FROM golang as builder

WORKDIR /app
COPY go.sum go.mod ./
RUN go mod download
COPY main.go ./
RUN CGO_ENABLED=0 go build -o app

FROM alpine

RUN apk --no-cache add bind-tools curl
COPY --from=builder /app/app /app
ENTRYPOINT ["/app"]
