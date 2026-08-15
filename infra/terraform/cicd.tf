# Automated CD: let GitHub Actions deploy to the server WITHOUT long-lived AWS
# keys and WITHOUT inbound SSH.
#
# Flow: Actions authenticates to AWS via OIDC (federated trust), assumes a
# tightly-scoped role, and sends ONE "pull && restart" command to the instance
# through SSM Run Command. No open port, no stored secret, no key to rotate.

# 1. GitHub's OIDC identity provider — READ, not created.
#
# This is the second real divergence from pps's config, and it is not a style
# choice: an IAM OIDC provider is ACCOUNT-GLOBAL and unique by URL. pps's
# terraform already created this exact provider, so a `resource` block here
# would fail the first apply with EntityAlreadyExists — and the tempting
# "fix" (importing it into Voxa's state) would be worse: two state files
# would then both believe they own one object, and a `destroy` on either
# product would silently break the other's deploys.
#
# Referencing it is the correct model. The provider is shared account
# infrastructure; what is per-product is the ROLE below and its trust
# condition. Ownership stays with pps's state, where it was created.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# 2. The role Actions may assume — ONLY from THIS repo's main branch. The `sub`
#    condition is the security boundary: a fork, a pull request, or another
#    branch cannot assume it, so only a merged-to-main build can deploy.
#
#    Note this is scoped to cvegaz/voxa. The pps role is scoped to
#    cvegaz/playpro_stats and can only reach the pps instance — so even sharing
#    an AWS account, neither repo's workflow can deploy to the other's server.
data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "voxa-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_assume.json
}

# 3. What the deploy role may do: send one shell command to THIS instance and
#    read its result. Least privilege — it cannot touch anything else, pps's
#    server included.
data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid     = "SendDeployCommand"
    actions = ["ssm:SendCommand"]
    resources = [
      aws_instance.server.arn,
      "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
    ]
  }
  statement {
    sid       = "ReadCommandResult"
    actions   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "deploy-via-ssm"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

# 4. Let the server REGISTER with SSM. Its agent already runs on the Ubuntu
#    image; it just needs this managed policy on the instance role to appear
#    as a managed node.
resource "aws_iam_role_policy_attachment" "server_ssm" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
