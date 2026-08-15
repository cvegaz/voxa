# The Stage 1 server: Ubuntu 24.04 ARM + Docker, with an address that never
# changes. Voxa's own instance — see the blast-radius note in main.tf.

# Latest official Ubuntu 24.04 LTS (arm64) from Canonical.
data "aws_ami" "ubuntu_arm" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# The default VPC — Stage 1 does not need custom networking (that is a
# Stage 2 / ECS concern).
data "aws_vpc" "default" {
  default = true
}

resource "aws_key_pair" "owner" {
  key_name   = "carlos-voxa"
  public_key = var.ssh_public_key
}

resource "aws_security_group" "web" {
  name        = "voxa-stage1-web"
  description = "Caddy is the only public entry; SSH restricted to the owner."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description      = "HTTP (ACME challenge + redirect to HTTPS)"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description      = "HTTPS"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "SSH - owner IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

  egress {
    # No apostrophe in "LetsEncrypt": AWS restricts the characters allowed in a
    # security-group rule description and rejects one.
    description      = "All outbound (GHCR pulls, OpenAI, ACME/LetsEncrypt, apt)"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  # Note what is NOT here: 5432. Postgres has no published host port in
  # docker-compose.prod.yml either — two independent layers saying the same
  # thing, so neither one being wrong on its own exposes the database.
}

resource "aws_instance" "server" {
  ami                    = data.aws_ami.ubuntu_arm.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.owner.key_name
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.server.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  # cloud-init: the ONLY hand-free setup — Docker + the compose plugin. The app
  # itself arrives separately (compose file + .env.production on the server,
  # images pulled from GHCR), which keeps this instance disposable: nothing
  # here knows anything about Voxa.
  user_data = <<-EOT
    #!/bin/bash
    set -euo pipefail
    apt-get update
    apt-get install -y docker.io docker-compose-v2
    systemctl enable --now docker
    usermod -aG docker ubuntu
  EOT

  tags = {
    Name = "voxa-stage1"
  }
}

# Elastic IP: the public address survives instance stops and rebuilds, so the
# DNS records point here once and never chase the server. This matters more
# than usual here — the records live in Route 53 but the DELEGATION lives at
# Porkbun, so an address change that forced a nameserver change would mean
# touching a second vendor.
resource "aws_eip" "server" {
  domain = "vpc"

  tags = {
    Name = "voxa-stage1"
  }
}

resource "aws_eip_association" "server" {
  instance_id   = aws_instance.server.id
  allocation_id = aws_eip.server.id
}
