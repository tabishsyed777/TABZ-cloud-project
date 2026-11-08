import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from logic import find_anomalies, is_idle, is_protected  # noqa: E402


def test_detects_spike():
    hist = {"EC2": [2.0, 2.1, 1.9, 2.0, 2.0]}
    out = find_anomalies({"EC2": 6.0}, hist)
    assert out and out[0]["service"] == "EC2"


def test_ignores_small_noise():
    hist = {"S3": [0.1, 0.1, 0.1, 0.1]}
    assert find_anomalies({"S3": 0.3}, hist) == []  # 3x but under $1 delta


def test_needs_history():
    assert find_anomalies({"EC2": 50.0}, {"EC2": [1.0]}) == []


def test_new_cost_from_zero_average():
    hist = {"NAT": [0, 0, 0, 0]}
    assert find_anomalies({"NAT": 5.0}, hist)


def test_protected_tag():
    assert is_protected([{"Key": "protected", "Value": "true"}])
    assert not is_protected([{"Key": "env", "Value": "dev"}])
    assert not is_protected(None)


def test_idle():
    assert is_idle(2.0, 7)
    assert not is_idle(2.0, 1)
    assert not is_idle(40.0, 7)
