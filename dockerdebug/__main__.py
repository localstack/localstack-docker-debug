import socket
import ssl

import dns.resolver
import dns.rdatatype
import dns.rrset
from dnslib.dns import QTYPE, DNSQuestion, DNSRecord


TEST_DNS_NAMES = [
    "host.localstack.cloud",
    "host.docker.internal",
    "localhost.localstack.cloud",
    "example.com",
    "s3.amazonaws.com",
]


# https://www.askpython.com/python/python-program-to-verify-ssl-certificates
def verify_ssl_certificate(hostname: str, port: int = 443) -> bool:
    context = ssl.create_default_context()

    try:
        with socket.create_connection((hostname, port)) as sock:
            try:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    ssock.do_handshake()
                    ssock.getpeercert()
                    return True
            except ssl.SSLCertVerificationError:
                return False
    except ConnectionRefusedError:
        return False


class NoDomain:
    def __init__(self, question: str):
        self.question = question

    def __repr__(self) -> str:
        return f"{self.question}: NO_DOMAIN"


def resolve_name(name: str) -> dns.rrset.RRset | NoDomain:
    try:
        answer = dns.resolver.resolve(name, rdtype=dns.rdatatype.A)
        return answer.rrset or NoDomain(name)
    except dns.resolver.NXDOMAIN:
        return NoDomain(name)


if __name__ == "__main__":

    q = DNSRecord(q=DNSQuestion("amazonaws.com", QTYPE.A))
    a = DNSRecord.parse(q.send("8.8.8.8", 53, tcp=False))
    for rr in a.rr:
        print(rr.rdata)

    print(socket.gethostbyname_ex("amazonaws.com"))

    raise SystemExit(0)


    verify_ssl_certificate("localhost", 9000)
    # for name in TEST_DNS_NAMES:
    #     print(resolve_name(name))
