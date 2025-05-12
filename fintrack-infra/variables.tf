variable "aws_region" {
  default = "us-east-1"
}

variable "key_name" {
  description = "Key pair name"
}

variable "instance_type" {
  default = "t2.micro"
}
