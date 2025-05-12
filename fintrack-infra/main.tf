module "security_group" {
  source   = "./modules/security_group"
  key_name = var.key_name
  
}

module "ec2_instance" {
  source            = "./modules/ec2"
  key_name          = var.key_name
  instance_type     = var.instance_type
  security_group_id = module.security_group.security_group_id
  user_data         = file("${path.module}/scripts/user_data.sh")
}