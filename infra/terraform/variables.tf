variable "aws_region" {
  description = "Deployment region. Same as pps: Mexico (Querétaro), closest to the owner and to the expected audience."
  type        = string
  default     = "mx-central-1"
}

variable "instance_type" {
  description = <<-EOT
    EC2 instance type. ARM (t4g/Graviton) because the GHCR images are built
    multi-arch — ARM is materially cheaper for the same memory.

    t4g.small (2 GB) rather than t4g.micro (1 GB): this host runs Postgres,
    the FastAPI backend, two nginx containers and Caddy. Postgres alone wants
    breathing room, and an OOM kill during a live demo is the worst possible
    place to save four dollars a month.
  EOT
  type        = string
  default     = "t4g.small"
}

variable "ssh_public_key" {
  description = <<-EOT
    The owner's SSH public key (contents of a .pub file). Generate locally:
      ssh-keygen -t ed25519 -C "carlos@voxa" -f ~/.ssh/voxa
    Only the PUBLIC half ever leaves your machine.

    A separate key from the pps server on purpose: AWS key pairs are unique by
    name per region anyway, and a per-host key means revoking access to one
    machine never touches the other.
  EOT
  type        = string
}

variable "ssh_ingress_cidr" {
  description = <<-EOT
    CIDR allowed to SSH (port 22). Use YOUR current public IP as a /32, e.g.
    "189.130.12.34/32" (check: https://checkip.amazonaws.com). Everything else
    reaches the server only through Caddy on 80/443.

    Home IPs change; when SSH stops working, this is the first thing to
    re-check. Deploys do NOT depend on it — those go through SSM, which needs
    no inbound port at all.
  EOT
  type        = string
}

variable "domain" {
  description = <<-EOT
    Apex domain served by Caddy. Leave empty ("") to create NO DNS records —
    the server still gets its Elastic IP, and the records land later with a
    one-variable change plus an apply.

    Registered at Porkbun (Route 53 Domains registration is blocked on this
    AWS account — see the deploy runbook), with DNS delegated to the Route 53
    hosted zone this configuration reads.
  EOT
  type        = string
  default     = "tryvoxa.com"
}

variable "backups_bucket_name" {
  description = "Globally-unique S3 bucket for the daily pg_dump backups."
  type        = string
  default     = "voxa-backups-275123487888"
}

variable "github_repo" {
  description = <<-EOT
    The repository allowed to deploy, as owner/name. Used to scope the OIDC
    trust policy to THIS repo's main branch — the security boundary that stops
    a fork or a pull request from assuming the deploy role.
  EOT
  type        = string
  default     = "cvegaz/voxa"
}
