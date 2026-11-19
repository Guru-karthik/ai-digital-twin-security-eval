variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "name" {
  type    = string
  default = "twin-console"
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "ssh_cidr" {
  description = "CIDR allowed to SSH (e.g. your IP as 203.0.113.4/32). Empty disables SSH; use SSM Session Manager instead."
  type        = string
  default     = ""

  validation {
    condition     = var.ssh_cidr == "" || can(cidrhost(var.ssh_cidr, 0))
    error_message = "ssh_cidr must be empty or a valid CIDR."
  }
}

variable "https_cidrs" {
  description = "CIDRs allowed to reach ports 80/443. Narrow this for a private demo."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "repo_url" {
  type    = string
  default = "https://github.com/Guru-karthik/ai-digital-twin-security-eval.git"
}
