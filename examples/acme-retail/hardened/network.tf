resource "aws_vpc" "main" {
  cidr_block = "10.40.0.0/16"
  tags       = { Name = "acme-retail-prod" }
}

resource "aws_flow_log" "main" {
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  log_destination_type = "s3"
  log_destination      = aws_s3_bucket.trail_logs.arn
}

resource "aws_subnet" "private" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.40.10.0/24"
}

# HTTPS only; administration goes through SSM Session Manager, not SSH.
resource "aws_security_group" "web" {
  name   = "acme-web"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "HTTPS from the load balancer"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "alb" {
  name   = "acme-alb"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "HTTPS from the internet to the load balancer only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "acme-db"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "MySQL from the web tier only"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }
}
