"""Install an operator-provided Meta key into the private Compose env file."""
import os
from pathlib import Path
import shutil
import sys


def configure(env_path:Path,key_path:Path)->bool:
    if not key_path.exists():return False
    try:
        key=key_path.read_text().strip()
        if not key or len(key)>16000 or any(c in key for c in "\r\n\x00"):
            raise ValueError("Invalid Meta key format")
        original=env_path.read_text()
        updates={"MODEL_API_KEY":key,"INFERENCE_PROVIDER":"meta","SENTINELX_MODE":"live",
                 "ALLOW_PAID_INFERENCE":"true","ENABLE_LIVE_MULTIMODAL":"true",
                 "META_APP_BUDGET_CENTS":"200","META_WORKSPACE_BUDGET_CENTS":"200",
                 "META_RUN_BUDGET_CENTS":"50","CAMPAIGN_WORKSPACE_MAX_ATTEMPTS":"20",
                 "ENABLE_PUBLIC_DEMO_SESSION":"true"}
        # dotenv single-quoted values are literal, never evaluated as shell code.
        def quote(value):return "'"+value.replace("\\","\\\\").replace("'","\\'")+"'"
        lines=[line for line in original.splitlines() if line.split("=",1)[0].strip() not in updates]
        lines.extend(name+"="+quote(value) for name,value in updates.items())
        backup=env_path.with_name(env_path.name+".before-meta")
        if not backup.exists():shutil.copyfile(env_path,backup);os.chmod(backup,0o600)
        temporary=env_path.with_name(env_path.name+".tmp")
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,"w") as stream:stream.write("\n".join(lines)+"\n")
        os.chmod(temporary,0o600)
        os.replace(temporary,env_path)
        return True
    finally:
        key_path.unlink(missing_ok=True)


if __name__=="__main__":
    configure(Path(sys.argv[1]),Path(sys.argv[2]))
