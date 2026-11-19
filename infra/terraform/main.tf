data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_vpc" "this" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.20.1.0/24"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.name}-public" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Only web ports in. Postgres, the gateway's metrics port and Prometheus are never opened.
resource "aws_security_group" "vm" {
  name_prefix = "${var.name}-"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.https_cidrs
  }
  ingress {
    description = "HTTP (redirect/ACME)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.https_cidrs
  }
  dynamic "ingress" {
    for_each = var.ssh_cidr == "" ? [] : [var.ssh_cidr]
    content {
      description = "SSH"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Secrets are generated here and stored encrypted in SSM Parameter Store; the VM reads them at boot.
resource "random_password" "secret" {
  for_each = toset(["DB_PASSWORD", "CONSOLE_SERVICE_TOKEN", "CONSOLE_METRICS_TOKEN", "GATEWAY_API_KEY", "GRAFANA_ADMIN_PASSWORD"])
  length   = 40
  special  = false
}

resource "random_id" "app_key" {
  byte_length = 32
}

resource "aws_ssm_parameter" "secret" {
  for_each = merge(
    { for k, v in random_password.secret : k => v.result },
    { APP_KEY = "base64:${random_id.app_key.b64_std}" },
  )
  name  = "/${var.name}/${each.key}"
  type  = "SecureString"
  value = each.value
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "read_secrets" {
  statement {
    actions   = ["ssm:GetParametersByPath"]
    resources = ["arn:aws:ssm:${var.region}:*:parameter/${var.name}"]
  }
  statement {
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = ["arn:aws:ssm:${var.region}:*:parameter/${var.name}/*"]
  }
}

resource "aws_iam_role" "vm" {
  name_prefix        = "${var.name}-"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "read_secrets" {
  role   = aws_iam_role.vm.id
  policy = data.aws_iam_policy_document.read_secrets.json
}

# Session Manager gives shell access without opening SSH.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.vm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "vm" {
  name_prefix = "${var.name}-"
  role        = aws_iam_role.vm.name
}

resource "aws_instance" "vm" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.vm.id]
  iam_instance_profile   = aws_iam_instance_profile.vm.name

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }
  root_block_device {
    encrypted   = true
    volume_size = 20
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region   = var.region
    name     = var.name
    repo_url = var.repo_url
  })
  user_data_replace_on_change = true

  tags = { Name = var.name }
}
