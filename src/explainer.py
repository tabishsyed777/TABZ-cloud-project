"""Ask Amazon Bedrock to explain the anomalies in plain English, then notify via SNS."""
import os

import boto3

from logic import build_prompt, fallback_summary

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION"))
sns = boto3.client("sns")


def explain(anomalies, date):
    try:
        resp = bedrock.converse(
            modelId=os.environ["BEDROCK_MODEL_ID"],
            messages=[{"role": "user", "content": [{"text": build_prompt(anomalies, date)}]}],
            inferenceConfig={"maxTokens": 700, "temperature": 0.2},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as exc:  # never lose the alert because the AI call failed
        print(f"Bedrock failed: {exc}")
        return "(AI explanation unavailable)"


def handler(event, context):
    date, anomalies = event["date"], event["anomalies"]
    body = fallback_summary(anomalies, date) + "\n\n--- AI explanation ---\n" + explain(anomalies, date)
    sns.publish(
        TopicArn=os.environ["SNS_TOPIC_ARN"],
        Subject=f"[Cost Guardian] {len(anomalies)} cost anomaly(ies) on {date}"[:100],
        Message=body,
    )
    return {"sent": True}
