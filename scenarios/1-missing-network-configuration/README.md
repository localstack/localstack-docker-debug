# Scenario 1

I am a user who has an application container that needs to talk to LocalStack. For example, I have an API Gateway REST API that I communicate with from my application container. My application container is running in docker but cannot connect to LocalStack. The reason is that I haven’t read the network troubleshooting guide, and my containers are in a different network. I am using the CLI to start LocalStack, and did not start either container in a docker network.
1. Solution: put both docker containers in a user-defined network and use container name to address LS ✔️
2. Solution: use `--network=host` 🤷
3. Solution: use `host.docker.internal` (if available) 🤷
4. Solution: use deprecated `links` API 🤷
5. Solution: use the same network *namespace (*https://docs.docker.com/engine/reference/run/#network-container) ❌

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

