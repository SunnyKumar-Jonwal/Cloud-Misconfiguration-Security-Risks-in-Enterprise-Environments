resource "aws_iam_role" "web" {
  name = "acme-web-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

# Read access only to the one prefix the export job needs.
resource "aws_iam_role_policy" "web_s3" {
  name = "acme-web-s3"
  role = aws_iam_role.web.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:aws:s3:::acme-retail-customer-exports/partner-feed/*" }]
  })
}

resource "aws_iam_instance_profile" "web" {
  name = "acme-web-profile"
  role = aws_iam_role.web.name
}

resource "aws_instance" "web" {
  ami                         = "ami-0abcdef1234567890"
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.private.id
  associate_public_ip_address = false
  iam_instance_profile        = aws_iam_instance_profile.web.name
  vpc_security_group_ids      = [aws_security_group.web.id]

  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # The database password is read from Secrets Manager at boot.
  user_data = <<-EOT
    #!/bin/bash
    export DB_SECRET_ARN=arn:aws:secretsmanager:ap-south-1:111122223333:secret:acme/orders-db
    /opt/acme/start-web.sh
  EOT

  root_block_device {
    encrypted = true
  }

  tags = { Name = "acme-web-1", role = "web-proxy" }
}

resource "aws_ebs_volume" "web_data" {
  availability_zone = "ap-south-1a"
  size              = 100
  encrypted         = true
  kms_key_id        = aws_kms_key.app.arn
}

resource "aws_iam_role" "order_sync" {
  name = "acme-order-sync"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_lambda_function" "order_sync" {
  function_name = "acme-order-sync"
  role          = aws_iam_role.order_sync.arn
  handler       = "app.handler"
  runtime       = "python3.12"
  filename      = "order_sync.zip"

  environment {
    variables = {
      PAYMENT_CREDENTIALS_ARN = aws_secretsmanager_secret.payment.arn
      REGION                  = "ap-south-1"
    }
  }
}

resource "aws_secretsmanager_secret" "payment" {
  name       = "acme/payment-api"
  kms_key_id = aws_kms_key.app.arn
}
