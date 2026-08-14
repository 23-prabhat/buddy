import struct

from bro.audio.vad.energy import EnergyVAD


def _pcm(rms_level: int, samples: int = 480) -> bytes:
    # constant amplitude approx
    return struct.pack(f"<{samples}h", *([rms_level] * samples))


def test_vad_detects_speech_and_end():
    vad = EnergyVAD(sample_rate=16000)
    # loud frames
    for _ in range(20):
        speaking, utt = vad.process(_pcm(3000))
        assert speaking
        assert utt is None
    # silence hangover
    done = None
    for _ in range(30):
        speaking, utt = vad.process(_pcm(0))
        if utt:
            done = utt
            break
    assert done is not None
    assert len(done) > 0
