"""Deploy updated Chat UI app source code and create a deployment.

The conversation module is copied into the chat_ui source directory so the
App runtime (which only downloads chat_ui/) can import it.
"""
import pathlib
import shutil
import tempfile

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppDeployment
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient(profile="Ecommerce-Agent")

SOURCE_PATH = (
    "/Workspace/Users/trietlm0306@gmail.com/.bundle/ecommerce-agent/dev/files"
    "/ecommerce_agent/apps/chat_ui"
)
LOCAL_APP_DIR = pathlib.Path("ecommerce_agent/apps/chat_ui")
LOCAL_CONV_DIR = pathlib.Path("ecommerce_agent/conversation")

# Build the file set to upload: all chat_ui files + all conversation files
files_to_upload = []

# Chat UI files (except __pycache__)
for f in sorted(LOCAL_APP_DIR.rglob("*")):
    if f.is_file() and f.suffix in (".py", ".yaml", ".txt") and "__pycache__" not in f.parts:
        files_to_upload.append(("chat_ui", f, f.name))

# Conversation files
for f in sorted(LOCAL_CONV_DIR.rglob("*")):
    if f.is_file() and f.suffix == ".py" and "__pycache__" not in f.parts:
        # Upload as conversation/<name>.py so it's importable
        files_to_upload.append(("conversation", f, f"{LOCAL_CONV_DIR.name}/{f.name}"))

# (NO pyproject.toml — the App runtime uses requirements.txt for deps)

# Upload all files to the workspace
seen_dirs = set()


def ensure_parent_dir(path_str: str):
    parent = "/".join(path_str.rstrip("/").split("/")[:-1])
    if not parent or parent in seen_dirs:
        return
    try:
        w.workspace.mkdirs(parent)
    except Exception:
        pass
    seen_dirs.add(parent)


for group, local_path, remote_name in files_to_upload:
    dest = f"{SOURCE_PATH}/{remote_name}"
    ensure_parent_dir(dest)
    print(f"Uploading {group}/{local_path.name} -> {dest}")
    with open(local_path, "rb") as fh:
        w.workspace.upload(dest, fh, overwrite=True, format=ImportFormat.AUTO)

# Create deployment
print("\nCreating deployment...")
dep = w.apps.deploy(
    app_name="ecommerce-agent-chat-ui",
    app_deployment=AppDeployment(source_code_path=SOURCE_PATH),
).result()

print(f"Deployment result: {dep}")
print("Deployment successful!")
