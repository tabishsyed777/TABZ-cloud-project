"""Find (and optionally stop) wasted resources. DRY_RUN=true by default: report only.

Safety rails:
  * resources tagged protected=true are never touched
  * deleting volumes / releasing IPs additionally needs ALLOW_DELETE=true
  * every finding/action is written to the audit table
"""
import datetime as dt
import os
import uuid

import boto3

from logic import is_idle, is_protected

ec2 = boto3.client("ec2")
cw = boto3.client("cloudwatch")
sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
ALLOW_DELETE = os.environ.get("ALLOW_DELETE", "false").lower() == "true"
CPU_THRESHOLD = float(os.environ.get("IDLE_CPU_PERCENT", "5"))
IDLE_DAYS = int(os.environ.get("IDLE_DAYS", "7"))


def audit(resource_type, resource_id, action, executed):
    dynamodb.Table(os.environ["AUDIT_TABLE"]).put_item(
        Item={
            "id": str(uuid.uuid4()),
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "executed": executed,
        }
    )


def idle_instances():
    found = []
    pages = ec2.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    )
    for page in pages:
        for res in page["Reservations"]:
            for inst in res["Instances"]:
                if is_protected(inst.get("Tags")):
                    continue
                now = dt.datetime.now(dt.timezone.utc)
                stats = cw.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": inst["InstanceId"]}],
                    StartTime=now - dt.timedelta(days=IDLE_DAYS),
                    EndTime=now,
                    Period=86400,
                    Statistics=["Average"],
                )["Datapoints"]
                if not stats:
                    continue
                avg = sum(p["Average"] for p in stats) / len(stats)
                if is_idle(avg, len(stats), CPU_THRESHOLD):
                    found.append((inst["InstanceId"], round(avg, 2)))
    return found


def unattached_volumes():
    vols = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])["Volumes"]
    return [(v["VolumeId"], v["Size"]) for v in vols if not is_protected(v.get("Tags"))]


def unused_eips():
    addrs = ec2.describe_addresses()["Addresses"]
    return [
        (a["AllocationId"], a["PublicIp"])
        for a in addrs
        if "AssociationId" not in a and not is_protected(a.get("Tags"))
    ]


def handler(event, context):
    report = []

    for iid, cpu in idle_instances():
        executed = False
        if not DRY_RUN:
            ec2.stop_instances(InstanceIds=[iid])
            executed = True
        audit("ec2", iid, f"stop (avg cpu {cpu}%)", executed)
        report.append(f"EC2 {iid}: idle (avg CPU {cpu}%) -> stop [{'DONE' if executed else 'dry-run'}]")

    for vid, size in unattached_volumes():
        executed = False
        if not DRY_RUN and ALLOW_DELETE:
            ec2.delete_volume(VolumeId=vid)
            executed = True
        audit("ebs", vid, f"delete ({size} GiB unattached)", executed)
        report.append(f"EBS {vid}: unattached {size} GiB -> delete [{'DONE' if executed else 'report only'}]")

    for alloc, ip in unused_eips():
        executed = False
        if not DRY_RUN and ALLOW_DELETE:
            ec2.release_address(AllocationId=alloc)
            executed = True
        audit("eip", alloc, f"release ({ip})", executed)
        report.append(f"EIP {ip}: unassociated -> release [{'DONE' if executed else 'report only'}]")

    if report:
        mode = "DRY RUN" if DRY_RUN else "LIVE"
        sns.publish(
            TopicArn=os.environ["SNS_TOPIC_ARN"],
            Subject=f"[Cost Guardian] Idle resources ({mode})",
            Message="\n".join(report),
        )
    return {"dry_run": DRY_RUN, "findings": len(report)}
