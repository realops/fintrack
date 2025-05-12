terraform {
  backend "s3" {
    bucket = "fintrack-tf-state-bucket"
    key    = "fintrack/terraform.tfstate"
    region = "us-east-1"
    # Optional locking
    # dynamodb_table = "terraform-locks"
  }
}
