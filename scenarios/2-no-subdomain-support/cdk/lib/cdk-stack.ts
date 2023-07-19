import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdanode from 'aws-cdk-lib/aws-lambda-nodejs';

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const fn = new lambdanode.NodejsFunction(this, "handler", {
      runtime: lambda.Runtime.NODEJS_18_X,
    });

    const api = new apigateway.LambdaRestApi(this, "api", {
      handler: fn,
    });

    new cdk.CfnOutput(this, "ApiId", {
      value: api.restApiId,
    });
  }
}
