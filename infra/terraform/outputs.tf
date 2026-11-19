output "public_ip" {
  value = aws_instance.vm.public_ip
}

output "secrets_path" {
  description = "SSM path holding generated secrets (read with aws ssm get-parameters-by-path --with-decryption)."
  value       = "/${var.name}"
}
