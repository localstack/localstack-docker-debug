import dns.resolver
import dns.rdatatype
import dns.rrset


TEST_DNS_NAMES = [
    "host.localstack.cloud",
    "host.docker.internal",
    "localhost.localstack.cloud",
    "example.com",
    "s3.amazonaws.com",
]


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
    for name in TEST_DNS_NAMES:
        print(resolve_name(name))
