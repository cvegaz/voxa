# Voxa — Stage 1 infrastructure.
#
# One small ARM EC2 instance in mx-central-1 running the docker-compose
# production stack behind Caddy. The server is DESCRIBED, not hand-built:
# `terraform apply` can rebuild it any day (immutable infrastructure applied
# to the metal).
#
# This is playPro Stats' Stage 1 pattern, adapted — not reinvented. The
# divergences from `../../../playpro_stats/infra/terraform` are deliberate and
# each one is commented where it appears.
#
# THE BIG ONE: Voxa gets its OWN EC2 instance, not a share of the pps host.
# pps serves a paying client; a shared host would couple that client's uptime
# to a portfolio project's deploys, restarts and public-demo load. Blast
# radius, not cost, is the deciding factor — sharing saves ~$15/month and buys
# a coupling that is expensive to undo later.
#
# State: remote in S3 with DynamoDB locking. The bucket and lock table already
# exist (created once by pps's ../bootstrap), so there is NO bootstrap root
# here — this product only adds its own state KEY inside the shared bucket,
# which is exactly the account-governance decision in the shared deployment
# plan: one AWS account, both products, separated by state key and cost tag.

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "playpro-tfstate-275123487888"
    key            = "voxa/stage1/terraform.tfstate" # one state key per product
    region         = "mx-central-1"
    dynamodb_table = "playpro-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "voxa" # cost-allocation tag: per-product spend in Cost Explorer
      Stage     = "stage1"
      ManagedBy = "terraform"
    }
  }
}
