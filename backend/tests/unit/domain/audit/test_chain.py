from app.domain.audit.chain import chain, verify_chain, GENESIS

def _events():
    return [
        {"module": "extraction", "action": "read"},
        {"module": "guard", "action": "verdict:ESCALATE"},
        {"module": "execution", "action": "queued"},
    ]

def test_chain_links_prev_hash():
    out = chain(_events())
    assert out[0]["prev_hash"] == GENESIS
    assert out[1]["prev_hash"] == out[0]["hash"]
    assert out[2]["prev_hash"] == out[1]["hash"]

def test_verify_accepts_untampered_chain():
    assert verify_chain(chain(_events())) is True

def test_verify_detects_tampering():
    out = chain(_events())
    out[1]["action"] = "verdict:AUTO_CLEAR"  # someone edits a past event
    assert verify_chain(out) is False

def test_verify_detects_deletion():
    out = chain(_events())
    del out[1]  # drop the middle event
    assert verify_chain(out) is False
