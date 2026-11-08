"""Compare a day's cost against the previous 7-day average; trigger the explainer on spikes."""
import datetime as dt
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

from logic import find_anomalies

dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")
LOOKBACK_DAYS = 7


def costs_for(table, day):
    resp = table.query(KeyConditionExpression=Key("date").eq(day.isoformat()))
    return {i["service"]: float(i["cost"]) for i in resp["Items"]}


def handler(event, context):
    day = dt.date.fromisoformat(event["date"])
    table = dynamodb.Table(os.environ["COST_TABLE"])

    today = costs_for(table, day)
    history = {}
    for n in range(1, LOOKBACK_DAYS + 1):
        for service, cost in costs_for(table, day - dt.timedelta(days=n)).items():
            history.setdefault(service, []).append(cost)

    anomalies = find_anomalies(
        today,
        history,
        ratio=float(os.environ.get("ANOMALY_RATIO", "1.5")),
        min_delta=float(os.environ.get("MIN_DELTA_USD", "1.0")),
    )
    print(f"{len(anomalies)} anomalies on {day}")

    if anomalies:
        lambda_client.invoke(
            FunctionName=os.environ["EXPLAINER_FUNCTION"],
            InvocationType="Event",
            Payload=json.dumps({"date": day.isoformat(), "anomalies": anomalies}).encode(),
        )
    return {"date": day.isoformat(), "anomalies": anomalies}
