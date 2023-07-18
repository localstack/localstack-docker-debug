package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	upstreamURL := os.Getenv("UPSTREAM_URL")

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		res, err := http.Get(upstreamURL)
		if err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprintf(w, "error sending request: %v", err)
			return
		}
		if res.StatusCode >= 300 {
			w.WriteHeader(http.StatusBadGateway)
			fmt.Fprintf(w, "bad status from upstream")
			return
		}

		fmt.Fprintf(w, "ok")
	})
	log.Println("listening on port 5000")
	log.Fatal(http.ListenAndServe(":5000", nil))
}
