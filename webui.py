from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scripts.cli_common import ScriptCommand, build_common_args, normalize_app_name


@dataclass
class Job:
    id: str
    mode: str
    app_name: str
    root_dir: str
    task: str = ""
    demo_name: str = ""
    doc_source: str = "auto_select"
    allow_no_docs: str = "n"
    status: str = "queued"
    started_at: float | None = None
    finished_at: float | None = None
    stop_requested: bool = False
    logs: list[str] = field(default_factory=list)


JOBS: dict[str, Job] = {}
RUNNING_PROCESSES: dict[str, subprocess.Popen[str]] = {}


def create_demo_name(app_name: str) -> str:
    demo_timestamp = int(time.time())
    return datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app_name}_%Y-%m-%d_%H-%M-%S")


def _script_with_args(job: Job) -> list[ScriptCommand]:
    common_args = list(build_common_args(app=job.app_name, root_dir=job.root_dir))
    if job.mode == "run":
        common_args.extend(["--task_desc", job.task, "--doc_source", job.doc_source, "--allow_no_docs", job.allow_no_docs])
        return [ScriptCommand(script_path="scripts/task_executor.py", args=tuple(common_args))]
    if job.mode == "learn_auto":
        common_args.extend(["--task_desc", job.task])
        return [ScriptCommand(script_path="scripts/self_explorer.py", args=tuple(common_args))]

    step_args = ("--app", job.app_name, "--demo", job.demo_name, "--root_dir", job.root_dir)
    return [
        ScriptCommand(script_path="scripts/step_recorder.py", args=step_args),
        ScriptCommand(script_path="scripts/document_generation.py", args=step_args),
    ]


def request_stop_job(job_id: str) -> tuple[bool, str]:
    job = JOBS.get(job_id)
    if not job:
        return False, "Job not found"
    if job.status in {"succeeded", "failed", "stopped"}:
        return False, f"Job already finished with status: {job.status}"

    job.stop_requested = True
    if job.status == "queued":
        job.status = "stopped"
        job.finished_at = time.time()
        job.logs.append("Stop requested before execution.")
        return True, "Job stopped before execution"

    job.status = "stopping"
    process = RUNNING_PROCESSES.get(job_id)
    if process and process.poll() is None:
        process.terminate()
        job.logs.append("Stop requested by user. Sent terminate signal.")
    else:
        job.logs.append("Stop requested by user.")
    return True, "Stop requested"


def _run_job(job: Job) -> None:
    job.status = "running"
    job.started_at = time.time()
    env = dict(os.environ)

    commands = _script_with_args(job)
    for command in commands:
        if job.stop_requested:
            job.status = "stopped"
            job.finished_at = time.time()
            job.logs.append("Job stopped before launching next command.")
            return

        argv = command.to_argv()
        job.logs.append(f"$ {' '.join(argv)}")
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        RUNNING_PROCESSES[job.id] = process

        assert process.stdout is not None
        for line in process.stdout:
            job.logs.append(line.rstrip("\n"))
            if job.stop_requested and process.poll() is None:
                process.terminate()

        code = process.wait()
        RUNNING_PROCESSES.pop(job.id, None)

        if job.stop_requested:
            job.status = "stopped"
            job.finished_at = time.time()
            job.logs.append("Job stopped by user.")
            return

        if code != 0:
            job.status = "failed"
            job.finished_at = time.time()
            job.logs.append(f"Command exited with status {code}.")
            return

    job.status = "succeeded"
    job.finished_at = time.time()


def render_index() -> str:
    rows = "\n".join(
        f"<tr><td>{job.id}</td><td>{job.mode}</td><td>{job.app_name}</td><td>{job.status}</td>"
        f"<td><a href='/jobs/{job.id}'>查看日志</a></td></tr>"
        for job in sorted(JOBS.values(), key=lambda j: j.started_at or 0, reverse=True)
    )
    return f"""<!doctype html>
<html><head><meta charset='UTF-8'><title>AppAgent Web UI</title>
<style>body{{font-family:Arial,sans-serif;margin:24px}} form{{max-width:680px;padding:16px;border:1px solid #ddd;border-radius:8px}} .row{{margin-bottom:12px}} label{{display:block;margin-bottom:6px;font-weight:600}} input,select,textarea{{width:100%;padding:8px;box-sizing:border-box}} table{{margin-top:24px;border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:8px;text-align:left}}</style></head>
<body>
<h1>AppAgent 可视化控制台</h1>
<p>通过网页启动探索/部署流程，交互项包含：模式、应用名、任务描述、root 目录。</p>
<form method='post' action='/start'>
<div class='row'><label>运行模式</label><select name='mode' required>
<option value='learn_auto'>探索阶段 - autonomous exploration</option>
<option value='learn_demo'>探索阶段 - human demonstration</option>
<option value='run'>部署阶段 - task execution</option>
</select></div>
<div class='row'><label>应用名称</label><input name='app' placeholder='例如 DeepSeek' required /></div>
<div class='row'><label>任务描述（autonomous / deployment 必填）</label><textarea name='task' rows='3' placeholder='例如：发送消息 hello'></textarea></div>
<div class='row'><label>部署文档来源（仅 deployment）</label><select name='doc_source'><option value='auto_select'>交互选择（默认）</option><option value='auto'>autonomous docs</option><option value='demo'>demo docs</option><option value='none'>不使用 docs</option></select></div>
<div class='row'><label>无 docs 时是否继续（仅 deployment）</label><select name='allow_no_docs'><option value='n'>否（默认）</option><option value='y'>是</option></select></div>
<div class='row'><label>root_dir</label><input name='root_dir' value='./' required /></div>
<button type='submit'>启动任务</button>
</form>
<h2>最近任务</h2>
<table><thead><tr><th>ID</th><th>模式</th><th>应用</th><th>状态</th><th>详情</th></tr></thead><tbody>{rows}</tbody></table>
</body></html>"""


def render_job(job: Job) -> str:
    return f"""<!doctype html><html><head><meta charset='UTF-8'><title>任务日志</title>
<style>body{{font-family:Arial,sans-serif;margin:24px}} pre{{background:#111;color:#0f0;padding:12px;height:60vh;overflow:auto}} button{{padding:8px 12px}}</style></head>
<body><a href='/'>← 返回首页</a>
<h1>任务 {job.id}</h1>
<p>模式：{job.mode} | 应用：{job.app_name} | 状态：<span id='status'>{job.status}</span></p>
<button id='stop-btn' onclick='stopTask()'>停止任务</button>
<pre id='logs'></pre>
<script>
async function stopTask(){{
 const resp = await fetch('/jobs/{job.id}/stop', {{ method: 'POST' }});
 const data = await resp.json();
 if (!resp.ok) {{ alert(data.error || '停止失败'); }}
}}

async function refresh(){{
 const resp=await fetch('/jobs/{job.id}/status');
 if(!resp.ok) return;
 const data=await resp.json();
 document.getElementById('status').textContent=data.status;
 const logs=document.getElementById('logs');
 logs.textContent=data.logs.join('\\n');
 logs.scrollTop=logs.scrollHeight;
 document.getElementById('stop-btn').disabled = ['succeeded', 'failed', 'stopped'].includes(data.status);
 if(data.status==='running'||data.status==='queued'||data.status==='stopping') setTimeout(refresh,1200);
}}
refresh();
</script></body></html>"""


class AppAgentHandler(BaseHTTPRequestHandler):
    def _send_text(self, text: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        self._send_text(json.dumps(payload), status=status, content_type="application/json")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_text(render_index())
            return

        if path.startswith("/jobs/") and path.endswith("/status"):
            job_id = path.split("/")[2]
            job = JOBS.get(job_id)
            if not job:
                self._send_json({"error": "Job not found"}, status=404)
                return
            self._send_json(
                {
                    "id": job.id,
                    "mode": job.mode,
                    "status": job.status,
                    "logs": job.logs,
                    "started_at": job.started_at,
                    "finished_at": job.finished_at,
                }
            )
            return

        if path.startswith("/jobs/"):
            job_id = path.split("/")[2]
            job = JOBS.get(job_id)
            if not job:
                self._send_text("Job not found", status=404)
                return
            self._send_text(render_job(job))
            return

        self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/start":
            self._handle_start()
            return
        if path.startswith("/jobs/") and path.endswith("/stop"):
            job_id = path.split("/")[2]
            ok, message = request_stop_job(job_id)
            if ok:
                self._send_json({"ok": True, "message": message})
            else:
                self._send_json({"error": message}, status=400)
            return

        self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

    def _handle_start(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)
        mode = form.get("mode", [""])[0].strip()
        app_name_raw = form.get("app", [""])[0].strip()
        root_dir = form.get("root_dir", ["./"])[0].strip() or "./"
        task = form.get("task", [""])[0].strip()
        doc_source = form.get("doc_source", ["auto_select"])[0].strip() or "auto_select"
        allow_no_docs = form.get("allow_no_docs", ["n"])[0].strip() or "n"

        if mode not in {"learn_auto", "learn_demo", "run"}:
            self._send_json({"error": "Unsupported mode."}, status=400)
            return
        if not app_name_raw:
            self._send_json({"error": "App name is required."}, status=400)
            return
        if mode in {"learn_auto", "run"} and not task:
            self._send_json({"error": "Task description is required for this mode."}, status=400)
            return

        app_name = normalize_app_name(app_name_raw)
        Path(root_dir).mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex[:10]
        job = Job(
            id=job_id,
            mode=mode,
            app_name=app_name,
            root_dir=root_dir,
            task=task,
            demo_name=create_demo_name(app_name) if mode == "learn_demo" else "",
            doc_source=doc_source,
            allow_no_docs=allow_no_docs,
        )
        JOBS[job_id] = job

        threading.Thread(target=_run_job, args=(job,), daemon=True).start()

        self.send_response(303)
        self.send_header("Location", f"/jobs/{job_id}")
        self.end_headers()


def run_server(host: str = "0.0.0.0", port: int = 5000) -> None:
    server = ThreadingHTTPServer((host, port), AppAgentHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"AppAgent web UI running at http://{display_host}:{port}")
    if host == "0.0.0.0":
        print("Tip: use 127.0.0.1 or localhost in your browser. 0.0.0.0 is only a bind address.")
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AppAgent web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", default=5000, type=int, help="Bind port (default: 5000)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_server(host=args.host, port=args.port)
