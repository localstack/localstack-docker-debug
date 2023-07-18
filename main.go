package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/api/types/network"
	"github.com/docker/docker/client"
)

// Get the contianer ID of the currently running container
func getSelfID() (string, error) {
	hostname := os.Getenv("HOSTNAME")
	if hostname != "" {
		return hostname, nil
	}
	return "", fmt.Errorf("no $HOSTNAME set")
}

type Container struct {
	id  string
	cli *client.Client

	networkID string
}

func (c *Container) AttachToNetwork(ctx context.Context, networkID string) error {
	err := c.cli.NetworkConnect(ctx, networkID, c.id, &network.EndpointSettings{})
	if err != nil {
		return fmt.Errorf("connecting container to network: %w", err)
	}
	c.networkID = networkID
	return nil
}

func (c *Container) DetachFromNetwork(ctx context.Context) error {
	err := c.cli.NetworkDisconnect(ctx, c.networkID, c.id, true)
	if err != nil {
		return fmt.Errorf("disconnecting container from network: %w", err)
	}
	return nil
}

func (c *Container) PrintInterfaces() {
	ifaces, err := net.Interfaces()
	if err != nil {
		log.Fatalf("getting network interfaces: %v", err)
	}
	for _, i := range ifaces {
		log.Printf("Interface: %s", i.Name)
		addrs, err := i.Addrs()
		if err != nil {
			log.Printf("error getting addresses for interface %v: %v", i, err)
		}
		for _, add := range addrs {
			log.Printf("  %v", add)
		}
	}
}

func main() {
	ctx := context.Background()
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		panic(err)
	}
	defer cli.Close()

	currentID, err := getSelfID()
	if err != nil {
		panic(err)
	}
	log.Printf("container (short) name: %s", currentID)

	c := Container{
		id:  currentID,
		cli: cli,
	}

	// make sure we have a network
	networkName := "testnetwork"
	res, err := cli.NetworkCreate(ctx, networkName, types.NetworkCreate{})
	if err != nil {
		panic(err)
	}
	networkID := res.ID
	defer func() {
		err := cli.NetworkRemove(ctx, networkID)
		if err != nil {
			log.Printf("deleting network: %v", err)
		}
	}()

	log.Printf("1")
	c.PrintInterfaces()

	if err := c.AttachToNetwork(ctx, networkID); err != nil {
		panic(err)
	}
	log.Printf("2")
	c.PrintInterfaces()

	if err := c.DetachFromNetwork(ctx); err != nil {
		log.Printf("disconnecting from network: %v", err)
	}
	log.Printf("3")
	c.PrintInterfaces()
}
