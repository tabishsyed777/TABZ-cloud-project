"""Daily: pull yesterday's cost per service from Cost Explorer and store in DynamoDB."""
import datetime as dt
import json
import os
from decimal import Decimal

import boto3

# Cost Explorer is only available in us-east-1
ce = boto3.client("ce", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")


def get_daily_costs(day):
    start = day.isoformat()
    end = (day + dt.timedelta(days=1)).isoformat()
    costs, token = {}, None
    while True:
        kwargs = dict(
            TimePeriod={"Start": start, "End": end},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        if token:
            kwargs["NextPageToken"] = token
        resp = ce.get_cost_and_usage(**kwargs)
        for period in resp["ResultsByTime"]:
            for g in period["Groups"]:
                costs[g["Keys"][0]] = float(g["Metrics"]["UnblendedCost"]["Amount"])
        token = resp.get("NextPageToken")
        if not token:
            return costs


def handler(event, context):
    event = event or {}
    day = (
        dt.date.fromisoformat(event["date"])
        if event.get("date")
        else dt.date.today() - dt.timedelta(days=1)
    )
    costs = get_daily_costs(day)
    table = dynamodb.Table(os.environ["COST_TABLE"])
    with table.batch_writer() as batch:
        for service, cost in costs.items():
            batch.put_item(
                Item={"date": day.isoformat(), "service": service, "cost": Decimal(str(cost))}
            )
    print(f"Stored {len(costs)} services for {day}")

    if not event.get("skip_detection"):
        lambda_client.invoke(
            FunctionName=os.environ["DETECTOR_FUNCTION"],
            InvocationType="Event",
            Payload=json.dumps({"date": day.isoformat()}).encode(),
        )
    return {"date": day.isoformat(), "services": len(costs)}
