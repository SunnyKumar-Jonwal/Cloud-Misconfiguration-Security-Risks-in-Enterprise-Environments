resource "aws_iam_role" "eks" {
  name = "acme-eks-cluster"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "eks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_eks_cluster" "platform" {
  name     = "acme-platform"
  role_arn = aws_iam_role.eks.arn

  vpc_config {
    subnet_ids              = [aws_subnet.private.id]
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}
