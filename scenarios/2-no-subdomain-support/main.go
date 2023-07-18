package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudformation"
)

func main() {
	lsContainerName := os.Getenv("LS_CONTAINER_NAME")
	upstreamURL, err := getEndpointUrl(lsContainerName)
	if err != nil {
		panic(err)
	}
	log.Printf("upstream URL: %s", upstreamURL)

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

func getEndpointUrl(containerName string) (string, error) {
	// Use the AWS SDK to get the API Gateway URL
	awsEndpointURL := os.Getenv("LS_ENDPOINT_URL")
	awsRegion := "us-east-1"
	if awsEndpointURL == "" {
		return "", fmt.Errorf("getting LocalStack endpoint url")
	}
	customResolver := aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
		return aws.Endpoint{
			PartitionID:   "aws",
			URL:           awsEndpointURL,
			SigningRegion: awsRegion,
		}, nil
	})
	awsCfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion(awsRegion),
		config.WithEndpointResolverWithOptions(customResolver),
	)
	if err != nil {
		log.Fatalf("Cannot load the AWS configs: %s", err)
	}

	client := cloudformation.NewFromConfig(awsCfg)
	res, err := client.DescribeStacks(context.TODO(), &cloudformation.DescribeStacksInput{
		StackName: aws.String("CdkStack"),
	})
	if err != nil {
		return "", fmt.Errorf("getting cloudformation stack information: %w", err)
	}

	outputs := res.Stacks[0].Outputs
	for _, output := range outputs {
		if strings.Contains(*output.OutputValue, "execute-api") {
			// workaround URL returning - replace localhost.localstack.cloud with the container name of LocalStack as per the troubleshooting guide
			fixedURL := strings.Replace(*output.OutputValue, "localhost.localstack.cloud", containerName, 1)
			return fixedURL, nil
		}
	}

	return "", fmt.Errorf("could not get API Gateway URL")
}
