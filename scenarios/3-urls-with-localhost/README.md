# Scenario 3

I am trying to access an SQS queue created by LocalStack from my application container. I have received a queue url of `http://localhost:4566/000000000000/<queue-name>`. I try to connect to this endpoint from my application container, but I cannot access the queue. This is because the domain name returned is `localhost` (the current default), and of course LS is not available in the application container. I want to use the URL returned to access the SQS queue from the host and my application container.
1. Partial solution: set `HOSTNAME_EXTERNAL` to the docker container name for intra-docker communication, but won’t work at the same time from the host
2. Solution: set `HOSTNAME_EXTERNAL` to [`localhost.localstack.cloud`](http://localhost.localstack.cloud) for the host and add network aliases to the docker network

```yaml
networks:
  default:
  aliases:
    - localhost.localstack.cloud
```

3. Wait for https://github.com/moby/moby/pull/43444 to be merged ❌

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

