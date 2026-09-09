from ai_observability_lab.metrics import Metrics, percentile


def test_percentiles_and_window_are_consistent():
    assert percentile([], 0.95) == 0
    assert percentile([10, 20, 30, 40], 0.5) == 20
    assert percentile([10, 20, 30, 40], 0.95) == 40
    metrics = Metrics(10)
    for i in range(15):
        metrics.record(None, float(i), "v2")
    assert metrics.summary()["request_count"] == 10
    assert metrics.summary()["error_rate"] == 1
