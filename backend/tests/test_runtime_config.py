import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location("runtime_config",Path(__file__).resolve().parents[2]/"deploy/hostinger/configure-runtime.py")
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

def test_runtime_key_install_preserves_database_and_removes_transfer(tmp_path):
    env=tmp_path/".env.sentinelx";key=tmp_path/".sentinelx-meta-key"
    original="SENTINELX_POSTGRES_PASSWORD=existing-private-value\nINFERENCE_PROVIDER=demo\n"
    env.write_text(original);key.write_text("not-a-real-key-test-only")
    assert runtime.configure(env,key)
    content=env.read_text()
    assert "SENTINELX_POSTGRES_PASSWORD=existing-private-value" in content
    assert "INFERENCE_PROVIDER='meta'" in content and "META_APP_BUDGET_CENTS='200'" in content
    assert not key.exists()
    assert env.with_name(".env.sentinelx.before-meta").read_text()==original

def test_runtime_no_key_keeps_demo_and_invalid_key_never_writes(tmp_path):
    env=tmp_path/"env";key=tmp_path/"key";env.write_text("INFERENCE_PROVIDER=demo\n")
    assert runtime.configure(env,key) is False
    key.write_text("invalid\nmultiline")
    with pytest.raises(ValueError,match="Invalid Meta key"):runtime.configure(env,key)
    assert env.read_text()=="INFERENCE_PROVIDER=demo\n" and not key.exists()
