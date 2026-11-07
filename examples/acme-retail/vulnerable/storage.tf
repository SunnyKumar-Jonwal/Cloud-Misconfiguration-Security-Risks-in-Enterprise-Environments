# Customer exports bucket: shared publicly "for a partner", with no guard rails.
resource "aws_s3_bucket" "customer_exports" {
  bucket = "acme-retail-customer-exports"
  tags   = { data_classification = "confidential", contains = "customer-pii" }
}

resource "aws_s3_bucket_acl" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  acl    = "public-read"
}

resource "aws_s3_bucket_policy" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PartnerDownload"
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject"]
      Resource  = "arn:aws:s3:::acme-retail-customer-exports/*"
    }]
  })
}

# Marketing assets: public access block present but one setting was switched off.
resource "aws_s3_bucket" "marketing_assets" {
  bucket = "acme-retail-marketing-assets"
  tags   = { data_classification = "public" }
}

resource "aws_s3_bucket_public_access_block" "marketing_assets" {
  bucket                  = aws_s3_bucket.marketing_assets.id
  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "marketing_assets" {
  bucket = aws_s3_bucket.marketing_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "marketing_assets" {
  bucket = aws_s3_bucket.marketing_assets.id
  versioning_configuration {
    status = "Enabled"
  }
}
