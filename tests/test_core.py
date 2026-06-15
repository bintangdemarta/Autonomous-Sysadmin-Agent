from nexus.parser import parse_command
from nexus.safety import evaluate


def sample_commands():
    return {
        "monitoring": [
            {
                "name": "Check RAM",
                "command": "free -h",
                "keywords": ["cek ram", "memory"],
                "description": "Displays memory",
                "risk_level": "low",
            }
        ],
        "proxmox": [
            {
                "name": "Start VM",
                "pattern": "hidupkan vm (\\d+)",
                "command": "qm start {0}",
                "risk_level": "high",
                "requires_confirmation": True,
            }
        ],
    }


def test_keyword_command_parsing():
    parsed = parse_command("tolong cek ram", sample_commands())
    assert parsed is not None
    assert parsed.command == "free -h"
    assert parsed.category == "monitoring"
    assert parsed.requires_confirmation is False


def test_pattern_command_requires_confirmation():
    parsed = parse_command("hidupkan vm 101", sample_commands())
    assert parsed is not None
    assert parsed.command == "qm start 101"
    assert parsed.requires_confirmation is True

    decision = evaluate(parsed, confirmed=False)
    assert decision.allowed is False
    assert decision.requires_confirmation is True

    confirmed_decision = evaluate(parsed, confirmed=True)
    assert confirmed_decision.allowed is True
