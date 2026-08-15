# Daily pg_dump destination + the instance's ONLY AWS permission: writing to
# this bucket. No access keys ever live on the server — the EC2 instance
# profile supplies short-lived credentials automatically.
#
# Worth backing up even though the demo data looks disposable: this database
# holds the captured leads and the funnel history (ADR-0019 §7). Losing it
# means losing the answer to "did the month work", which is the entire point
# of running the public demo.
#
# Note the permission is PutObject and ListBucket — not GetObject and not
# DeleteObject. A compromised server can write backups and cannot read or
# destroy the ones already there. Versioning is the second half of that: even
# an overwrite is recoverable.

resource "aws_s3_bucket" "backups" {
  bucket = var.backups_bucket_name
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Keep 90 days of daily dumps; older ones expire. Storage stays in pennies.
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire-old-dumps"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

data "aws_iam_policy_document" "assume_ec2" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "server" {
  name               = "voxa-stage1-server"
  assume_role_policy = data.aws_iam_policy_document.assume_ec2.json
}

data "aws_iam_policy_document" "backups_write" {
  statement {
    sid       = "WriteBackups"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.backups.arn}/*"]
  }

  statement {
    sid       = "ListBackups"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.backups.arn]
  }
}

resource "aws_iam_role_policy" "backups_write" {
  name   = "backups-write-only"
  role   = aws_iam_role.server.id
  policy = data.aws_iam_policy_document.backups_write.json
}

resource "aws_iam_instance_profile" "server" {
  name = "voxa-stage1-server"
  role = aws_iam_role.server.name
}
