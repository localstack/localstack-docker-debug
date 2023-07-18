package main

import (
	"log"
	"net"

	"github.com/miekg/dns"
)

func handleStaticValue(w dns.ResponseWriter, r *dns.Msg) {
	qname := r.Question[0].Name
	log.Printf("got request for %s", qname)

	m := new(dns.Msg)
	m.SetReply(r)

	if qname == "example.com." {
		log.Printf("Emulating server failure")
		m.Rcode = dns.RcodeServerFailure
		w.WriteMsg(m)
		return
	}

	rr := dns.A{
		Hdr: dns.RR_Header{Name: qname, Rrtype: dns.TypeA, Class: dns.ClassINET, Ttl: 0},
		A:   net.IPv4(10, 10, 10, 10),
	}
	m.Answer = append(m.Answer, &rr)
	log.Printf("%+#v", m)
	// indicate failure
	w.WriteMsg(m)
}

func main() {
	dns.HandleFunc(".", handleStaticValue)
	server := &dns.Server{
		Addr:      ":53",
		Net:       "udp",
		ReusePort: true,
	}
	log.Printf("listening for DNS requests")
	log.Fatal(server.ListenAndServe())
}
