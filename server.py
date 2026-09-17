#!/usr/bin/env python3
"""
SS Gujarat MIS Portal - Local Web Server & Data API
Author: Antigravity AGY Engine
Description: Serves the Web Application, handles Authentication, Excel File Uploads & Scraper APIs.
"""

import sys
import os
import json
import http.server
import socketserver
import urllib.parse
from scraper import sync_now, DATA_FILE_PATH
from auto_watcher import start_folder_watcher

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

STUDENTS_CSV = os.path.join(DIRECTORY, "CTS DATA", "Total Students-240402 (6).csv")
STUDENT_ANALYTICS_JSON = os.path.join(DIRECTORY, "data", "student_analytics.json")

_students_cache = None
_students_by_uid = None

def get_students_data():
    global _students_cache, _students_by_uid
    if _students_cache is not None:
        return _students_cache, _students_by_uid
    
    _students_cache = []
    _students_by_uid = {}
    if os.path.exists(STUDENTS_CSV):
        import csv
        with open(STUDENTS_CSV, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = (row.get("AadhaarUID") or "").strip().replace('"', '').replace("'", "")
                item = {
                    "AadhaarUID": uid,
                    "StudentName": (row.get("StudentName") or "").strip(),
                    "FatherName": (row.get("FatherName") or "").strip(),
                    "MotherName": (row.get("MotherName") or "").strip(),
                    "SurName": (row.get("SurName") or "").strip(),
                    "Gender": (row.get("Gender") or "").strip().title(),
                    "DOB": (row.get("DOB") or "").strip(),
                    "StudentAge": (row.get("StudentAge") or "").strip(),
                    "AadhaarID": (row.get("AadhaarID") or "").strip(),
                    "SocialCategory": (row.get("SocialCategory") or "").strip(),
                    "SubCaste": (row.get("SubCaste") or "").strip(),
                    "StudyingClass": (row.get("StudyingClass") or "").strip(),
                    "Section": (row.get("Section") or "").strip(),
                    "GRNo": (row.get("GRNo") or "").strip(),
                    "SchoolId": (row.get("SchoolId") or "").strip(),
                    "School": (row.get("School") or "").strip(),
                    "Cluster": (row.get("Cluster") or "").strip(),
                    "Village": (row.get("Village") or "").strip(),
                    "Management": (row.get("Management") or "").strip(),
                    "SchoolCategory": (row.get("SchoolCategory") or "").strip(),
                    "Religion": (row.get("Religion") or "").strip(),
                    "DisabilityName": (row.get("DisabilityName") or "").strip(),
                    "WhetherHomeLess": (row.get("WhetherHomeLess") or "").strip(),
                    "StudentStatus": (row.get("StudentStatus") or "").strip(),
                    "Stream_Desc": (row.get("Stream_Desc") or "").strip()
                }
                if uid:
                    _students_by_uid[uid] = item
                _students_cache.append(item)
    return _students_cache, _students_by_uid

class MISRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"

        if parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if os.path.exists(DATA_FILE_PATH):
                with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"error": "Data file not found"}).encode("utf-8"))
            return

        if parsed.path == "/api/student_analytics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if os.path.exists(STUDENT_ANALYTICS_JSON):
                with open(STUDENT_ANALYTICS_JSON, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"error": "Student analytics file not found"}).encode("utf-8"))
            return

        if parsed.path == "/api/student_by_uid":
            query_params = urllib.parse.parse_qs(parsed.query)
            uid = query_params.get("uid", [""])[0].strip().replace('"', '').replace("'", "")
            _, by_uid = get_students_data()
            st = by_uid.get(uid)
            self.send_response(200 if st else 404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if st:
                self.wfile.write(json.dumps({"success": True, "student": st}, ensure_ascii=False).encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"success": False, "message": f"Student with AadhaarUID '{uid}' not found"}, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/student_search":
            query_params = urllib.parse.parse_qs(parsed.query)
            q = query_params.get("q", [""])[0].strip().lower()
            cluster = query_params.get("cluster", [""])[0].strip()
            std_class = query_params.get("class", [""])[0].strip()
            try:
                limit = int(query_params.get("limit", [50])[0])
            except Exception:
                limit = 50

            students, by_uid = get_students_data()

            if q and q in by_uid:
                results = [by_uid[q]]
            else:
                results = []
                for s in students:
                    if cluster and s["Cluster"] != cluster:
                        continue
                    if std_class and s["StudyingClass"] != std_class:
                        continue
                    if q:
                        if (q in s["AadhaarUID"].lower() or
                            q in s["StudentName"].lower() or
                            q in s["FatherName"].lower() or
                            q in s["SurName"].lower() or
                            q in s["GRNo"].lower() or
                            q in s["School"].lower() or
                            q in s["SchoolId"].lower()):
                            results.append(s)
                            if len(results) >= limit:
                                break
                    else:
                        results.append(s)
                        if len(results) >= limit:
                            break

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "count": len(results), "records": results}, ensure_ascii=False).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        if parsed.path == "/api/upload_excel":
            records = payload.get("records", [])
            filename = payload.get("filename", "uploaded_file.xlsx")

            if os.path.exists(DATA_FILE_PATH):
                with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"tab_datasets": {}}

            if "tab_datasets" not in data:
                data["tab_datasets"] = {}

            data["tab_datasets"]["student_tracking_history"] = records

            with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            response_data = {
                "success": True,
                "message": f"Successfully uploaded {len(records)} records from {filename} into Student Tracking History!",
                "count": len(records)
            }
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/login":
            username = payload.get("username", "admin")
            sync_res = sync_now()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            response_data = {
                "success": True,
                "message": f"Welcome {username}! Authentication successful.",
                "user": username,
                "sync_details": sync_res
            }
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/sync":
            cookie = payload.get("cookie", "")
            result = sync_now(cookie=cookie)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    start_folder_watcher(interval_seconds=3)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MISRequestHandler) as httpd:
        print(f"==================================================")
        print(f"  SS Gujarat MIS Portal - Excel Upload Server Active")
        print(f"  Dashboard: http://localhost:{PORT}/index.html")
        print(f"  Auto-Watcher Active on CTS DATA Folder!")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    run_server()
