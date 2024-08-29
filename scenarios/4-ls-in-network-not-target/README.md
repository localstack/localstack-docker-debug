# Scenario 4

I have launched LocalStack in a network as per the troubleshooting docs, but I have launched my application container in the default network. I cannot connect to LocalStack from my application container.
1. Solution: re-launch your container in the docker network of the LocalStack container
2. Solution: attach your container to the docker network of LocalStack (though ideally use option a)

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

