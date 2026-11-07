# CI deploys through GitHub OIDC federation: no static keys, a scoped role.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "ci_deployer" {
  name = "acme-ci-deployer"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = { StringLike = { "token.actions.githubusercontent.com:sub" = "repo:acme-retail/infrastructure:ref:refs/heads/main" } }
    }]
  })
}

resource "aws_iam_role_policy" "ci_deployer" {
  name = "acme-ci-deploy"
  role = aws_iam_role.ci_deployer.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["ecs:UpdateService", "ecs:DescribeServices"], Resource = "arn:aws:ecs:ap-south-1:111122223333:service/acme/*" }]
  })
}

# The analytics partner can assume the role only from its own account with an external ID.
resource "aws_iam_role" "partner_access" {
  name = "acme-partner-access"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::444455556666:root" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "sts:ExternalId" = "acme-partner-2026" } }
    }]
  })
}

resource "aws_iam_policy" "ops_read_only" {
  name = "acme-ops-read-only"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["ec2:Describe*", "rds:Describe*", "cloudwatch:Get*"], Resource = "*" }]
  })
}
