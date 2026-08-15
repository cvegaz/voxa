output "public_ip" {
  description = "The server's permanent public address (Elastic IP). The three A records already point here."
  value       = aws_eip.server.public_ip
}

output "ssh_command" {
  description = "How the owner connects. Needs var.ssh_ingress_cidr to match your current public IP."
  value       = "ssh -i ~/.ssh/voxa ubuntu@${aws_eip.server.public_ip}"
}

output "ami_used" {
  description = "Resolved Ubuntu 24.04 arm64 AMI (traceability: which image this server was actually built from)."
  value       = data.aws_ami.ubuntu_arm.id
}

output "backups_bucket" {
  value = aws_s3_bucket.backups.bucket
}

# The two values the GitHub Actions deploy workflow needs. They are repo
# VARIABLES, not secrets — an IAM role ARN and an instance id are identifiers,
# not credentials, and the OIDC trust condition is what actually gates access.
output "github_deploy_role_arn" {
  description = "Set as the AWS_DEPLOY_ROLE_ARN repository variable in GitHub."
  value       = aws_iam_role.github_deploy.arn
}

output "server_instance_id" {
  description = "Set as the SSM_INSTANCE_ID repository variable in GitHub."
  value       = aws_instance.server.id
}
