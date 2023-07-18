package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	v4 "github.com/aws/aws-sdk-go-v2/aws/signer/v4"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudformation"
	"github.com/google/uuid"
)

func main() {
	awsCfg, err := getAWSConfig()
	if err != nil {
		panic(err)
	}

	queueUrl, err := getQueueUrl(awsCfg)
	if err != nil {
		panic(err)
	}

	messageContents := fmt.Sprintf("message %s", uuid.New())

	signer := v4.NewSigner()
	if err := sendMessage(signer, messageContents, queueUrl); err != nil {
		panic(err)
	}
	if err := waitForMessages(signer, messageContents, queueUrl); err != nil {
		panic(err)
	}
}

func sendMessage(signer *v4.Signer, contents string, url string) error {
	log.Printf("sending message")

	r, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return fmt.Errorf("creating initial request: %w", err)
	}
	q := r.URL.Query()
	q.Add("Action", "SendMessage")
	q.Add("MessageBody", contents)
	q.Add("Version", "2012-11-05")
	r.URL.RawQuery = q.Encode()

	client := &http.Client{}
	if _, err := client.Do(r); err != nil {
		return fmt.Errorf("sending message: %w", err)
	}

	return nil
}

func waitForMessages(signer *v4.Signer, contents string, url string) error {
	log.Printf("receiving messages")
	for i := 0; i < 5; i++ {
		res, err := receiveMessages(signer, url)
		if err != nil {
			return fmt.Errorf("receiving messages: %w", err)
		}
		if strings.Contains(res, contents) {
			log.Printf("found message %s", contents)
			return nil
		}

		time.Sleep(3 * time.Second)
	}

	return fmt.Errorf("could not find expected message")
}

func receiveMessages(signer *v4.Signer, url string) (string, error) {
	r, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("creating initial request: %w", err)
	}
	q := r.URL.Query()
	q.Add("Action", "ReceiveMessage")
	q.Add("Version", "2012-11-05")
	q.Add("MaxNumberOfMessages", "10")
	q.Add("WaitTimeSeconds", "3")
	r.URL.RawQuery = q.Encode()

	client := &http.Client{}
	res, err := client.Do(r)
	if err != nil {
		return "", fmt.Errorf("sending message: %w", err)
	}
	defer res.Body.Close()
	message, _ := io.ReadAll(res.Body)
	if res.StatusCode >= 300 {
		return "", fmt.Errorf("bad response %d: %s", res.StatusCode, string(message))
	}

	return string(message), nil
}

func getAWSConfig() (*aws.Config, error) {
	// Use the AWS SDK to get the API Gateway URL
	awsEndpointURL := os.Getenv("LS_ENDPOINT_URL")
	awsRegion := "us-east-1"
	if awsEndpointURL == "" {
		return nil, fmt.Errorf("getting LocalStack endpoint url")
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
		return nil, fmt.Errorf("Cannot load the AWS configs: %s", err)
	}

	return &awsCfg, nil
}

func getQueueUrl(awsCfg *aws.Config) (string, error) {
	client := cloudformation.NewFromConfig(*awsCfg)
	res, err := client.DescribeStacks(context.TODO(), &cloudformation.DescribeStacksInput{
		StackName: aws.String("CdkStack"),
	})
	if err != nil {
		return "", fmt.Errorf("getting cloudformation stack information: %w", err)
	}

	outputs := res.Stacks[0].Outputs
	for _, output := range outputs {
		if *output.OutputKey == "QueueUrl" {
			log.Printf("found sqs queue url: %s", *output.OutputValue)
			return *output.OutputValue, nil
		}

	}

	return "", fmt.Errorf("could not get SQS queue URL")
}
