# Customer exports: private, encrypted, versioned; the partner gets a scoped role.
resource "aws_s3_bucket" "customer_exports" {
  bucket = "acme-retail-customer-exports"
  tags   = { data_classification = "confidential", contains = "customer-pii" }
}

resource "aws_s3_bucket_ownership_controls" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "customer_exports" {
  bucket                  = aws_s3_bucket.customer_exports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.app.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_policy" "customer_exports" {
  bucket = aws_s3_bucket.customer_exports.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PartnerDownload"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::444455556666:role/partner-feed-reader" }
      Action    = ["s3:GetObject"]
      Resource  = "arn:aws:s3:::acme-retail-customer-exports/partner-feed/*"
    }]
  })
}

resource "aws_s3_bucket" "marketing_assets" {
  bucket = "acme-retail-marketing-assets"
  tags   = { data_classification = "public" }
}

resource "aws_s3_bucket_public_access_block" "marketing_assets" {
  bucket                  = aws_s3_bucket.marketing_assets.id
  block_public_acls       = true
  block_public_policy     = true
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
