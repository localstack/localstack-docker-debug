# Scenario 2

I am running LS from within a docker compose stack. My LS container and application container are implicitly within a user defined docker network, created by docker compose. I wish to access an API Gateway subdomain from my application container but I can’t. I am using `<container_name>:4566` to connect to from my application container, but I cannot access `<api id>.execute-api.us-east-1.<container_name>:4566`.

1. Solution: [configure the DNS server of the application container to point to LocalStack](https://docs.localstack.cloud/references/network-troubleshooting/endpoint-url/#from-your-container)
2. Solution: use external dns e.g. https://gist.github.com/boomshadow/20677ef02f110e448ee058ae6149af3a ✔️
3. Solution: in pro - use LS DNS server and set `DNS_RESOLVE_IP` ✔️
4. Solution: use tags when creating the domain to set a static rest API ID, and add hosts in docker to target that specific subdomain ❌

# setup

```bash
bash ./setup.sh
```

# test execution

```bash
bash ./test.sh
```

# teardown

```bash
bash ./teardown.sh
```

