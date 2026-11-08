"""Pure business logic (no AWS calls) so it is easy to unit test."""

MIN_HISTORY_DAYS = 3


def find_anomalies(today_costs, history, ratio=1.5, min_delta=1.0):
    """Return services whose cost today is unusually high.

    today_costs: {service: cost_today}
    history:     {service: [past daily costs]}
    ratio:       flag if cost > ratio * average
    min_delta:   ignore spikes smaller than this many dollars (avoids noise)
    """
    anomalies = []
    for service, cost in today_costs.items():
        past = history.get(service, [])
        if len(past) < MIN_HISTORY_DAYS:
            continue  # not enough data to judge
        avg = sum(past) / len(past)
        delta = cost - avg
        if delta < min_delta:
            continue
        if avg == 0 or cost > avg * ratio:
            anomalies.append(
                {
                    "service": service,
                    "cost_today": round(cost, 2),
                    "avg_cost": round(avg, 2),
                    "increase_usd": round(delta, 2),
                    "increase_pct": round(delta / avg * 100, 1) if avg else None,
                }
            )
    return sorted(anomalies, key=lambda a: a["increase_usd"], reverse=True)


def is_protected(tags):
    """tags: list of {'Key':..., 'Value':...}. Protected resources are never touched."""
    for t in tags or []:
        if t.get("Key", "").lower() == "protected" and str(t.get("Value", "")).lower() == "true":
            return True
    return False


def is_idle(avg_cpu, datapoints, threshold=5.0, min_points=3):
    if datapoints < min_points or avg_cpu is None:
        return False
    return avg_cpu < threshold


def build_prompt(anomalies, date):
    lines = [
        f"- {a['service']}: ${a['cost_today']} today vs ${a['avg_cost']} average "
        f"(+${a['increase_usd']})"
        for a in anomalies
    ]
    return (
        f"You are an AWS FinOps assistant. On {date} these AWS services had unusual cost increases:\n"
        + "\n".join(lines)
        + "\n\nFor each one, give the 2-3 most likely causes and one concrete action to check or fix it. "
        "Be concise and plain-spoken. Do not invent exact numbers."
    )


def fallback_summary(anomalies, date):
    lines = [
        f"- {a['service']}: ${a['cost_today']} today vs ${a['avg_cost']} avg (+${a['increase_usd']})"
        for a in anomalies
    ]
    return f"Cost anomalies detected on {date}:\n" + "\n".join(lines)
