import pytest

from biggieflow.cadence import CadenceVector, swing_offset_ms


def test_defaults_valid():
    v = CadenceVector()
    assert v.to_list() == [0.20, 0.10, 0.6, 2.0, 4.5, 0.4]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"swing_8th": 0.7},
        {"swing_16th": -0.1},
        {"anacrusis_prob": 1.2},
        {"cross_bar_span": 4},
        {"rhyme_pair_beat": 3.0},
        {"unstressed_accent": 2.0},
    ],
)
def test_out_of_range_rejected(kwargs):
    with pytest.raises(ValueError):
        CadenceVector(**kwargs)


def test_swing_offset_ms():
    # 90 BPM -> beat = 666.67 ms, half-beat = 333.33 ms, 0.2 swing = 66.67 ms
    assert swing_offset_ms(90, 0.2) == pytest.approx(66.667, abs=0.01)
    with pytest.raises(ValueError):
        swing_offset_ms(0, 0.2)
