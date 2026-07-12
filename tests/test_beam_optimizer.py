from pyoranris.algorithms.beam_optimizer import BeamIndexOptimizer, BeamSearch


def test_optimizer_ranges():
    o = BeamIndexOptimizer(
        max_ris_index=20,
        max_rx_index=10,
        current_ris_index=5,
        current_rx_index=2,
        num_index_interval=2,
    )
    rr = o.get_ris_beam_index_range()
    assert 3 in rr and 7 in rr


def test_beam_search():
    o = BeamIndexOptimizer(max_ris_index=10, current_ris_index=4, num_index_interval=1)
    bs = BeamSearch(o)

    def fake_get(b):
        return -b

    best, results = bs.sweep(fake_get)
    assert best in results
    assert isinstance(results, dict)
