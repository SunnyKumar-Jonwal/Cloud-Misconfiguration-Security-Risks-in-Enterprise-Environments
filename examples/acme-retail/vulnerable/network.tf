resource "aws_vpc" "main" {
  cidr_block = "10.40.0.0/16"
  tags       = { Name = "acme-retail-prod" }
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.40.1.0/24"
}

# Web tier: HTTPS is fine, but SSH is open to the world "for the vendor".
resource "aws_security_group" "web" {
  name   = "acme-web"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH for support vendor"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Database security group opened "temporarily" during a migration.
resource "aws_security_group" "db" {
  name   = "acme-db"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "MySQL migration window"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Legacy group created during troubleshooting and never removed.
resource "aws_security_group" "legacy_debug" {
  name   = "acme-legacy-debug"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
