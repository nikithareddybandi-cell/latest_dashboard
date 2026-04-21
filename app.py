import os
import re
import json
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime

app = Flask(__name__)

ANALYSIS_FILE = "analysis.json"
DATA = []


def load_analysis():
    if os.path.exists(ANALYSIS_FILE):
        with open(ANALYSIS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_analysis(data):
    with open(ANALYSIS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ================= LOG PARSER =================
def parse_log(file_path):
    data = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

    try:
        with open(file_path, "r", errors="ignore") as f:
            content = f.read()

        total = re.search(r"Total Tests\s*:\s*(\d+)", content)
        passed = re.search(r"Tests Passed\s*:\s*(\d+)", content)
        failed = re.search(r"Tests Failed\s*:\s*(\d+)", content)
        errors = re.search(r"Errors\s*:\s*(\d+)", content)

        data["total"] = int(total.group(1)) if total else 0
        data["passed"] = int(passed.group(1)) if passed else 0
        data["failed"] = int(failed.group(1)) if failed else 0
        data["errors"] = int(errors.group(1)) if errors else 0

    except:
        pass

    return data


def get_status(total, failed, errors):
    if total == 0:
        return "HALTED"
    elif errors >= 1:
        return "ERROR"
    elif failed >= 1:
        return "FAIL"
    return "PASS"


def scan_svn(path):
    results = []

    for root, _, files in os.walk(path):
        module = os.path.basename(root)

        for file in files:
            if file.endswith(".log"):
                full = os.path.join(root, file)

                log = parse_log(full)

                date = datetime.fromtimestamp(
                    os.path.getmtime(full)
                ).strftime("%Y-%m-%d %H:%M")

                status = get_status(
                    log["total"],
                    log["failed"],
                    log["errors"]
                )

                results.append({
                    "file": file,
                    "module": module,
                    "path": full,
                    "date": date,
                    "total": log["total"],
                    "passed": log["passed"],
                    "failed": log["failed"],
                    "errors": log["errors"],
                    "status": status
                })

    return results


@app.route("/", methods=["GET", "POST"])
def home():
    global DATA

    if request.method == "POST":
        path = request.form.get("path")
        if path and os.path.exists(path):
            DATA = scan_svn(path)

    return render_template(
        "dashboard_new.html",
        data=DATA,
        analysis=load_analysis()
    )


@app.route("/save_analysis", methods=["POST"])
def save():
    save_analysis(request.json)
    return jsonify({"ok": True})


# ✅ SAFE LOG OPEN
@app.route("/open_log")
def open_log():
    path = request.args.get("path")

    if not path:
        return "Invalid path"

    path = os.path.normpath(path)

    # ✅ restrict access only to scanned files
    allowed_paths = {d["path"] for d in DATA}

    if path not in allowed_paths:
        return "Access denied"

    if not os.path.exists(path):
        return f"File not found: {path}"

    try:
        with open(path, "r", errors="ignore") as f:
            return Response(f.read(), mimetype='text/plain')
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)