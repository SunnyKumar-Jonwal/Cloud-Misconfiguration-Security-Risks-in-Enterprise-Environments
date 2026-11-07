# Reconstruction of the misconfiguration pattern publicly reported for the
# 2019 Capital One breach: a web application firewall (WAF) running on EC2,
# reachable from the internet, vulnerable to server-side request forgery,
# with IMDSv1 enabled and an instance role that could list and read S3
# buckets. Names and values are illustrative; only the pattern is real.
# DO NOT DEPLOY.

resource "aws_security_group" "waf" {
  name = "waf-public"

  ingress {
    description = "HTTPS from the internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role" "waf" {
  name = "waf-instance-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

# The role could list buckets and read objects far beyond what a WAF needs.
resource "aws_iam_role_policy" "waf_s3" {
  name = "waf-s3-access"
  role = aws_iam_role.waf.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetObject"], Resource = "*" }]
  })
}

resource "aws_iam_instance_profile" "waf" {
  name = "waf-instance-profile"
  role = aws_iam_role.waf.name
}

resource "aws_instance" "waf" {
  ami                         = "ami-0abcdef1234567890"
  instance_type               = "m5.large"
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.waf.name
  vpc_security_group_ids      = [aws_security_group.waf.id]

  metadata_options {
    http_tokens = "optional"
  }

  tags = { Name = "waf-reverse-proxy" }
}

resource "aws_s3_bucket" "credit_applications" {
  bucket = "example-bank-credit-applications"
  tags   = { data_classification = "restricted", contains = "customer-pii" }
}

resource "aws_s3_bucket" "card_statements" {
  bucket = "example-bank-card-statements"
  tags   = { data_classification = "confidential" }
}

resource "aws_s3_bucket" "web_assets" {
  bucket = "example-bank-web-assets"
  tags   = { data_classification = "public" }
}

resource "aws_cloudtrail" "main" {
  name                       = "bank-trail"
  s3_bucket_name             = "example-bank-trail-logs"
  is_multi_region_trail      = true
  enable_log_file_validation = true
}
