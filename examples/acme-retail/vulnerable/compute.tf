resource "aws_iam_role" "web" {
  name = "acme-web-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

# The web role was given S3 read on everything "to make the export job work".
resource "aws_iam_role_policy" "web_s3" {
  name = "acme-web-s3"
  role = aws_iam_role.web.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"], Resource = "*" }]
  })
}

resource "aws_iam_instance_profile" "web" {
  name = "acme-web-profile"
  role = aws_iam_role.web.name
}

resource "aws_instance" "web" {
  ami                         = "ami-0abcdef1234567890"
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.web.name
  vpc_security_group_ids      = [aws_security_group.web.id]

  metadata_options {
    http_tokens = "optional"
  }

  user_data = <<-EOT
    #!/bin/bash
    export DB_PASSWORD=Acme@Retail2026
    /opt/acme/start-web.sh
  EOT

  tags = { Name = "acme-web-1", role = "web-proxy" }
}

resource "aws_ebs_volume" "web_data" {
  availability_zone = "ap-south-1a"
  size              = 100
  encrypted         = false
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
      PAYMENT_API_TOKEN = "acme-demo-token-not-real-7731"
      REGION            = "ap-south-1"
    }
  }
}
