
import pytest
from app.models import User

def test_capping_logic():
    """Test manual capping logic for lists and dicts."""
    
    # 1. List Capping
    history = [{"i": i} for i in range(120)]
    capped_history = history[-100:]
    assert len(capped_history) == 100
    assert capped_history[0]["i"] == 20
    assert capped_history[-1]["i"] == 119
    
    # 2. Dict Capping
    # Verify Python dict insertion order preservation (standard in 3.7+)
    d = {f"k{i}": i for i in range(120)}
    # Logic:
    if len(d) > 100:
        sorted_keys = list(d.keys())
        to_remove = len(d) - 100
        for i in range(to_remove):
             del d[sorted_keys[i]] # removing first inserted
    
    assert len(d) == 100
    assert "k119" in d
    assert "k0" not in d
    assert "k19" not in d
    assert "k20" in d
