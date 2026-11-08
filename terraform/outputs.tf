output "collector_function" {
  value = aws_lambda_function.fn["collector"].function_name
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
