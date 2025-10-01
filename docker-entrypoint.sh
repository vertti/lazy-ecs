#!/bin/bash
# Docker entrypoint that automatically handles AWS credentials

# Normalize region settings - boto3 uses AWS_DEFAULT_REGION
if [ -n "$AWS_REGION" ] && [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION="$AWS_REGION"
fi

# Check if we have AWS credentials in environment
if [ -n "$AWS_ACCESS_KEY_ID" ] || [ -n "$AWS_PROFILE" ] || [ -f "$HOME/.aws/credentials" ]; then
    # Credentials are available, run lazy-ecs
    exec lazy-ecs "$@"
else
    echo "❌ No AWS credentials found!"
    echo ""
    echo "Please provide AWS credentials using one of these methods:"
    echo ""
    echo "1. Mount your AWS config:"
    echo "   docker run -it --rm -v ~/.aws:/home/lazyecs/.aws:ro vertti/lazy-ecs"
    echo ""
    echo "2. With aws-vault (temporary credentials):"
    echo "   aws-vault exec your-profile -- docker run -it --rm \\"
    echo "     -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AWS_REGION \\"
    echo "     vertti/lazy-ecs"
    echo ""
    echo "3. With IAM credentials (long-lived):"
    echo "   docker run -it --rm \\"
    echo "     -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_REGION \\"
    echo "     vertti/lazy-ecs"
    echo ""
    exit 1
fi