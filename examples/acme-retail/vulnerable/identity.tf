# CI user with a static key and administrator rights.
resource "aws_iam_user" "ci_deployer" {
  name = "acme-ci-deployer"
}

resource "aws_iam_access_key" "ci_deployer" {
  user = aws_iam_user.ci_deployer.name
}

resource "aws_iam_user_policy_attachment" "ci_admin" {
  user       = aws_iam_user.ci_deployer.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# Role "for the analytics partner" that anyone can assume.
resource "aws_iam_role" "partner_access" {
  name = "acme-partner-access"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { AWS = "*" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_policy" "ops_full" {
  name = "acme-ops-full"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]
  })
}
