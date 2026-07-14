from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICACHE = (ROOT / "spinal/src/main/scala/openla500/memory/OpenLa500ICache.scala").read_text(encoding="utf-8")
DCACHE = (ROOT / "spinal/src/main/scala/openla500/memory/OpenLa500DCache.scala").read_text(encoding="utf-8")


def _assert_recovery_contract(source: str, *, cache_name: str) -> None:
    assert "mode0 || mode1 || mode2" in source, cache_name
    assert ".elsewhen(requestCacop)" not in source, cache_name
    assert "cacheHit || requestCacop" not in source, cache_name
    assert "requestCacop &&" in source, cache_name


def test_icache_cacop_uses_passing_d22_state_path() -> None:
    _assert_recovery_contract(ICACHE, cache_name="icache")


def test_dcache_cacop_uses_passing_d22_state_path() -> None:
    _assert_recovery_contract(DCACHE, cache_name="dcache")
    assert "!(requestPreld || requestCacop)" in DCACHE
