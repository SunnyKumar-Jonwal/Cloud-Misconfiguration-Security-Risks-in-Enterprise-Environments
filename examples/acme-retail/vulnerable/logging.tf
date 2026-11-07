resource "aws_s3_bucket" "trail_logs" {
  bucket = "acme-retail-cloudtrail-logs"
}

resource "aws_s3_bucket_public_access_block" "trail_logs" {
  bucket                  = aws_s3_bucket.trail_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "trail_logs" {
  bucket = aws_s3_bucket.trail_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_versioning" "trail_logs" {
  bucket = aws_s3_bucket.trail_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Single-region trail without log file validation.
resource "aws_cloudtrail" "main" {
  name                       = "acme-trail"
  s3_bucket_name             = aws_s3_bucket.trail_logs.id
  is_multi_region_trail      = false
  enable_log_file_validation = false
}
