variable "project" {
  type    = string
  default = "ai-cost-guardian"
}

variable "aws_region" {
  type    = string
  default = "ap-south-1" # Mumbai
}

variable "alert_email" {
  type        = string
  description = "Email that receives anomaly and remediation reports."
}

variable "bedrock_region" {
  type        = string
  default     = "us-east-1"
  description = "Region where you enabled Bedrock model access."
}

variable "bedrock_model_id" {
  type        = string
  default     = "amazon.nova-lite-v1:0"
  description = "Check the Bedrock console for a model available to you (some regions need an inference-profile ID like us.amazon.nova-lite-v1:0)."
}

variable "dry_run" {
  type        = bool
  default     = true
  description = "Remediator only reports when true. Keep true until you trust it."
}

variable "allow_delete" {
  type        = bool
  default     = false
  description = "Extra switch needed for deleting EBS volumes / releasing Elastic IPs."
}

variable "anomaly_ratio" {
  type    = number
  default = 1.5
}

variable "min_delta_usd" {
  type    = number
  default = 1.0
}
