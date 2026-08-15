# DNS — three A records, all pointing at the one Elastic IP.
#
# Hostname split, matching deploy/Caddyfile:
#   tryvoxa.com       -> the marketing landing
#   app.tryvoxa.com   -> the demo SPA
#   www.tryvoxa.com   -> 301 to the apex (Caddy does the redirect; DNS just
#                        has to resolve, and Caddy needs a cert for it)
#
# With var.domain = "" nothing here exists and the server still gets its
# Elastic IP — the records land later with a one-variable change and an apply.

# The hosted zone is read, NOT managed.
#
# This is the one real divergence from pps's dns.tf, and it is deliberate.
# There, Route 53 Domains created the zone as a side effect of registering the
# domain. Here the registration is at Porkbun (Route 53 Domains registration
# is blocked on this account — see the deploy runbook), so the zone was created
# by hand and Porkbun's nameservers point at it.
#
# It stays a `data` source rather than an imported `resource` on purpose:
# a hosted zone's nameservers are assigned by AWS at creation, and they are
# referenced EXTERNALLY at the registrar. If Terraform owned the zone, a
# `destroy` would delete it and a recreate would hand back a DIFFERENT set of
# four nameservers — silently breaking delegation until someone remembered to
# go re-paste them at Porkbun. Keeping the zone outside Terraform's destroy
# path makes that failure impossible rather than merely unlikely.
data "aws_route53_zone" "site" {
  count = var.domain == "" ? 0 : 1
  name  = var.domain
}

resource "aws_route53_record" "apex" {
  count   = var.domain == "" ? 0 : 1
  zone_id = data.aws_route53_zone.site[0].zone_id
  name    = var.domain
  type    = "A"
  ttl     = 300
  records = [aws_eip.server.public_ip]
}

resource "aws_route53_record" "www" {
  count   = var.domain == "" ? 0 : 1
  zone_id = data.aws_route53_zone.site[0].zone_id
  name    = "www.${var.domain}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.server.public_ip]
}

# app.<domain> — the demo SPA. Caddy's app.<domain> block obtains its
# certificate only once this resolves, so the record must exist BEFORE the
# stack comes up or the ACME challenge fails and burns a Let's Encrypt retry.
resource "aws_route53_record" "app" {
  count   = var.domain == "" ? 0 : 1
  zone_id = data.aws_route53_zone.site[0].zone_id
  name    = "app.${var.domain}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.server.public_ip]
}
