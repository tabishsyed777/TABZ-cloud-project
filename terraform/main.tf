data "aws_caller_identity" "me" {}

locals {
  prefix = var.project
  fn     = { for k in ["collector", "detector", "explainer", "remediator"] : k => "${local.prefix}-${k}" }
  fn_arn = { for k, v in local.fn : k => "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.me.account_id}:function:${v}" }

  common_env = {
    COST_TABLE       = aws_dynamodb_table.costs.name
    AUDIT_TABLE      = aws_dynamodb_table.audit.name
    SNS_TOPIC_ARN    = aws_sns_topic.alerts.arn
    BEDROCK_REGION   = var.bedrock_region
    BEDROCK_MODEL_ID = var.bedrock_model_id
    ANOMALY_RATIO    = tostring(var.anomaly_ratio)
    MIN_DELTA_USD    = tostring(var.min_delta_usd)
    DRY_RUN          = tostring(var.dry_run)
    ALLOW_DELETE     = tostring(var.allow_delete)
    DETECTOR_FUNCTION  = local.fn["detector"]
    EXPLAINER_FUNCTION = local.fn["explainer"]
  }

  schedules = {
    collector  = "cron(0 3 * * ? *)"  # 03:00 UTC daily
    remediator = "cron(30 3 * * ? *)" # 03:30 UTC daily
  }
}

# ---------- Storage ----------
resource "aws_dynamodb_table" "costs" {
  name         = "${local.prefix}-costs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"
  range_key    = "service"
  attribute {
    name = "date"
    type = "S"
  }
  attribute {
    name = "service"
    type = "S"
  }
}

resource "aws_dynamodb_table" "audit" {
  name         = "${local.prefix}-audit"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
}

# ---------- Notifications ----------
resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email # you must click the confirmation link in your inbox
}

# ---------- IAM (one role for now) ----------
# TODO (good interview topic): split into one least-privilege role per function.
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "app" {
  statement {
    actions   = ["ce:GetCostAndUsage"]
    resources = ["*"]
  }
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:BatchWriteItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.costs.arn, aws_dynamodb_table.audit.arn]
  }
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }
  statement {
    actions = ["lambda:InvokeFunction"]
    resources = [local.fn_arn["detector"], local.fn_arn["explainer"]]
  }
  statement {
    actions   = ["bedrock:InvokeModel"]
    resources = ["*"] # TODO: restrict to the specific model ARN
  }
  statement {
    actions = [
      "ec2:DescribeInstances", "ec2:DescribeVolumes", "ec2:DescribeAddresses",
      "cloudwatch:GetMetricStatistics",
    ]
    resources = ["*"]
  }
  statement {
    # Destructive actions: only meaningful when dry_run=false
    actions   = ["ec2:StopInstances", "ec2:DeleteVolume", "ec2:ReleaseAddress"]
    resources = ["*"]
    condition {
      test     = "StringNotEquals"
      variable = "aws:ResourceTag/protected"
      values   = ["true"]
    }
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${local.prefix}-app"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.app.json
}

# ---------- Lambda functions ----------
data "archive_file" "src" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
  excludes    = ["__pycache__"]
}

resource "aws_lambda_function" "fn" {
  for_each         = local.fn
  function_name    = each.value
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "${each.key}.handler"
  filename         = data.archive_file.src.output_path
  source_code_hash = data.archive_file.src.output_base64sha256
  timeout          = 60
  memory_size      = 256
  environment {
    variables = local.common_env
  }
}

resource "aws_cloudwatch_log_group" "fn" {
  for_each          = local.fn
  name              = "/aws/lambda/${each.value}"
  retention_in_days = 14
}

# ---------- Schedules ----------
resource "aws_cloudwatch_event_rule" "schedule" {
  for_each            = local.schedules
  name                = "${local.prefix}-${each.key}-schedule"
  schedule_expression = each.value
}

resource "aws_cloudwatch_event_target" "schedule" {
  for_each = local.schedules
  rule     = aws_cloudwatch_event_rule.schedule[each.key].name
  arn      = aws_lambda_function.fn[each.key].arn
}

resource "aws_lambda_permission" "events" {
  for_each      = local.schedules
  statement_id  = "AllowEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[each.key].arn
}
