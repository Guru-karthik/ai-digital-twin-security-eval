# Terraform: one-VM deployment (AWS)

Creates a VPC, public subnet, a security group that opens only 80/443 (SSH only if `ssh_cidr` is set), an EC2 instance (IMDSv2, encrypted disk, Session Manager access), and generated secrets in SSM Parameter Store (SecureString). The VM's boot script clones the repo, builds `.env` from SSM and runs `docker compose up -d --build`.

**Status: validated (`terraform validate`), never applied.** No cloud account was used. Review `terraform plan` before applying; this will incur AWS charges.

Known limits: no TLS termination (put a load balancer or Caddy in front before real use), secrets are also readable in Terraform state (use an encrypted remote backend), no remote backend is configured, the compose stack still uses the twin stub until the real agent image exists.

    terraform init && terraform validate
    terraform plan -var 'ssh_cidr=203.0.113.4/32'
