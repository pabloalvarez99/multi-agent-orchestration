r"""Rebuild deterministic fake-specialist UI evidence in ``docs/assets``.

Install once with ``pip install -e ".[docs]"`` and ``playwright install chromium``,
then run ``python scripts/capture_ui.py``. The script starts P3 on a free localhost
port, submits only the fake path, normalizes the request id displayed in the page,
and writes a SHA-256 manifest next to the captures.
"""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from playwright.sync_api import Page

ROOT: Final = Path(__file__).resolve().parents[1]
ASSETS: Final = ROOT / "docs" / "assets"
MANIFEST: Final = ASSETS / "ui-captures.sha256"
HOST: Final = "127.0.0.1"
VIEWPORT: Final = {"width": 1440, "height": 1050}
FIXED_REQUEST_ID: Final = "capture-fixed-request-id"


@dataclass(frozen=True)
class CaptureSpec:
    """Stable inputs and expected labels for one screenshot."""

    filename: str
    task: str
    max_handoffs: int
    expected_status: str
    target: str | None = None


CAPTURE_SPECS: Final = (
    CaptureSpec(
        filename="ui-done.png",
        task="Compare hybrid vs dense retrieval in one paragraph",
        max_handoffs=8,
        expected_status="Done",
    ),
    CaptureSpec(
        filename="ui-budget.png",
        task="Explain bounded orchestration",
        max_handoffs=1,
        expected_status="Budget Exhausted",
    ),
    CaptureSpec(
        filename="ui-trace.png",
        task="Audit retrieval risk",
        max_handoffs=8,
        expected_status="Done",
        target=".outcome",
    ),
)


def _free_port() -> int:
    """Ask the OS for an unused localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind((HOST, 0))
        return int(listener.getsockname()[1])


def _wait_for_api(base_url: str, server: subprocess.Popen[bytes], timeout: float = 30.0) -> None:
    """Wait until Uvicorn is healthy or fail with a bounded diagnostic."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"capture server exited with code {server.returncode}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"capture server was not healthy within {timeout:.0f} seconds")


def _submit(page: Page, base_url: str, spec: CaptureSpec) -> None:
    """Submit one pinned fake-path task and wait for its terminal label."""
    page.goto(base_url, wait_until="networkidle")
    page.locator("#task").fill(spec.task)
    page.locator("#max_handoffs").fill(str(spec.max_handoffs))
    page.get_by_role("button", name="Run specialist team").click()
    page.wait_for_load_state("networkidle")
    page.get_by_role("heading", name=spec.expected_status, exact=True).wait_for(
        state="visible"
    )


def _stabilize(page: Page) -> None:
    """Remove the only dynamic value and disable rendering motion."""
    request_id = page.locator(".diagnostics code")
    request_id.wait_for(state="visible")
    request_id.evaluate("(node, value) => { node.textContent = value; }", FIXED_REQUEST_ID)
    page.add_style_tag(
        content=(
            "* { animation: none !important; transition: none !important; "
            "caret-color: transparent !important; }"
        )
    )
    page.evaluate("document.fonts.ready")


def _write_manifest() -> None:
    """Record the committed byte identity of every generated PNG."""
    lines = []
    for spec in CAPTURE_SPECS:
        path = ASSETS / spec.filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  docs/assets/{spec.filename}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _stop_server(server: subprocess.Popen[bytes]) -> None:
    """Stop only the Uvicorn child created by this invocation."""
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)


def capture() -> None:
    """Start the local app and regenerate all deterministic screenshots."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            'Playwright is documentation-only; install it with pip install -e ".[docs]"'
        ) from error

    port = _free_port()
    base_url = f"http://{HOST}:{port}"
    env = os.environ.copy()
    env.update({"AGENTIC_RAG_URL": "", "OPENAI_API_KEY": ""})
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    server = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mao.main:app",
            "--host",
            HOST,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    ASSETS.mkdir(parents=True, exist_ok=True)
    try:
        _wait_for_api(base_url, server)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport=VIEWPORT,
                device_scale_factor=1,
                locale="en-US",
                color_scheme="dark",
                reduced_motion="reduce",
            )
            for spec in CAPTURE_SPECS:
                _submit(page, base_url, spec)
                _stabilize(page)
                path = ASSETS / spec.filename
                if spec.target is None:
                    page.screenshot(
                        path=path,
                        full_page=True,
                        animations="disabled",
                        caret="hide",
                    )
                else:
                    page.locator(spec.target).screenshot(
                        path=path,
                        animations="disabled",
                        caret="hide",
                    )
            browser.close()
        _write_manifest()
    finally:
        _stop_server(server)


def main() -> int:
    """Regenerate screenshots and print their stable digests."""
    try:
        capture()
    except RuntimeError as error:
        print(f"capture failed: {error}", file=sys.stderr)
        return 1
    print(MANIFEST.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
