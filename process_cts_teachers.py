import csv
import json
import os
import re
from datetime import datetime

CSV_PATH = r"D:\GSQAC AND SAT\MIS SITE\CTS DATA\TeacherReport_Block_240402_20261007_1157.csv"
DATA_DIR = r"D:\GSQAC AND SAT\MIS SITE\data"
DASHBOARD_JSON = os.path.join(DATA_DIR, "dashboard_data.json")
DASHBOARD_JS = os.path.join(DATA_DIR, "dashboard_data.js")
TEACHERS_JSON = os.path.join(DATA_DIR, "cts_teachers.json")
TEACHERS_JS = os.path.join(DATA_DIR, "cts_teachers.js")

print("Processing CTS Teacher Report from:", CSV_PATH)

# Load existing schools from dashboard_data.json
schools_map = {}
dashboard_data = {}
if os.path.exists(DASHBOARD_JSON):
    with open(DASHBOARD_JSON, "r", encoding="utf-8") as f:
        dashboard_data = json.load(f)
        for s in dashboard_data.get("school_records", []):
            sid = str(s.get("school_id") or s.get("dise_code") or "").strip()
            if sid:
                schools_map[sid] = s

teachers = []

with open(CSV_PATH, "r", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.reader(f)
    raw_header = next(reader)
    clean_header = [h.strip() for h in raw_header]
    
    col_idx = {name: i for i, name in enumerate(clean_header)}
    
    for row_num, row in enumerate(reader, start=1):
        if not row or not any(row):
            continue
            
        def get_val(col_name):
            idx = col_idx.get(col_name)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return ""

        udise = get_val("School UDISE")
        teacher_code = get_val("Teacher Code")
        teacher_name = get_val("Teacher Name")
        designation = get_val("Designation") or "Teacher"
        joined_as = get_val("Joined_As") or "1 To 5"
        
        subj_6_8 = get_val("Std_6_To_8_Subject")
        if subj_6_8 == "0":
            subj_6_8 = "-"
            
        lang = get_val("Language")
        if lang == "0":
            lang = "-"
            
        post = get_val("Post") or designation.upper()
        rec_mode = get_val("RecruitmentMode_6To8")
        raw_ret_date = get_val("RetiredDate")
        
        ret_date_clean = ""
        ret_year = ""
        if raw_ret_date:
            date_part = raw_ret_date.split(" ")[0]
            parts = date_part.split("/")
            if len(parts) == 3:
                try:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    ret_date_clean = f"{d:02d}/{m:02d}/{y:04d}"
                    ret_year = str(y)
                except Exception:
                    ret_date_clean = date_part
            else:
                ret_date_clean = date_part

        curr_status = get_val("CurrentStatus") or "In School"
        profile_status = get_val("Profile") or "Updated"
        mapping_status = get_val("Subject Mapping") or "Mapped"
        subjects_taught_raw = get_val("Std")
        
        # Parse subjects taught into a structured list
        subjects_list = []
        if subjects_taught_raw:
            parts = [p.strip() for p in subjects_taught_raw.split(",") if p.strip()]
            for p in parts:
                if p not in subjects_list:
                    subjects_list.append(p)
                    
        school_info = schools_map.get(udise, {})
        management = school_info.get("management") or "Local Body"
        school_category = school_info.get("category") or "Primary with Upper Primary"
        village = school_info.get("village") or get_val("Cluster")

        item = {
            "sr_no": row_num,
            "district": get_val("District") or "MAHESANA",
            "block": get_val("Block") or "KADI",
            "cluster": get_val("Cluster") or school_info.get("cluster_name") or "",
            "udise_code": udise,
            "school_name": get_val("School") or school_info.get("school_name") or "",
            "teacher_code": teacher_code,
            "teacher_name": teacher_name,
            "designation": designation,
            "joined_as": joined_as,
            "subject_6_to_8": subj_6_8,
            "language": lang,
            "post": post,
            "recruitment_mode": rec_mode,
            "retire_date": ret_date_clean,
            "retire_year": ret_year,
            "current_status": curr_status,
            "relieving_status": get_val("RelievingStatus"),
            "transfer_school": get_val("TransferToSchoolCode"),
            "not_relieved_reason": get_val("NotRelievedReason"),
            "relieving_remarks": get_val("RelievingRemarks"),
            "profile_status": profile_status,
            "subject_mapping": mapping_status,
            "subjects_taught": subjects_list,
            "subjects_taught_str": subjects_taught_raw,
            "management": management,
            "category": school_category,
            "village": village
        }
        teachers.append(item)

print(f"Parsed {len(teachers)} teacher records.")

# Summary statistics
clusters = sorted(list(set(t["cluster"] for t in teachers if t["cluster"])))
schools = sorted(list(set(t["udise_code"] for t in teachers if t["udise_code"])))
designations = sorted(list(set(t["designation"] for t in teachers if t["designation"])))
joined_levels = sorted(list(set(t["joined_as"] for t in teachers if t["joined_as"])))

summary = {
    "total_teachers": len(teachers),
    "total_schools": len(schools),
    "total_clusters": len(clusters),
    "primary_1_to_5": sum(1 for t in teachers if t["joined_as"] == "1 To 5"),
    "upper_primary_6_to_8": sum(1 for t in teachers if t["joined_as"] == "6 To 8"),
    "principals": sum(1 for t in teachers if "Principal" in t["designation"] or t["joined_as"] == "HTAT"),
    "sahayak": sum(1 for t in teachers if "Sahayak" in t["designation"]),
    "mapped_count": sum(1 for t in teachers if t["subject_mapping"] == "Mapped"),
    "pending_count": sum(1 for t in teachers if t["subject_mapping"] != "Mapped"),
    "clusters": clusters,
    "designations": designations,
    "joined_levels": joined_levels
}

print("Summary Stats:", summary)

# 1. Write data/cts_teachers.json
output_payload = {
    "summary": summary,
    "teachers": teachers
}

with open(TEACHERS_JSON, "w", encoding="utf-8") as f:
    json.dump(output_payload, f, ensure_ascii=False, indent=2)
print("Saved:", TEACHERS_JSON)

# 2. Write data/cts_teachers.js
with open(TEACHERS_JS, "w", encoding="utf-8") as f:
    f.write("// CTS Teachers Dataset for Kadi Block\n")
    f.write("window.ctsTeachersData = ")
    json.dump(output_payload, f, ensure_ascii=False)
    f.write(";\n")
print("Saved:", TEACHERS_JS)

# 3. Update dashboard_data.json and dashboard_data.js
if dashboard_data:
    dashboard_data["cts_teachers_records"] = teachers
    dashboard_data["cts_teachers_summary"] = summary
    with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
    print("Updated:", DASHBOARD_JSON)
    
    with open(DASHBOARD_JS, "w", encoding="utf-8") as f:
        f.write("var globalData = ")
        json.dump(dashboard_data, f, ensure_ascii=False)
        f.write(";\n")
    print("Updated:", DASHBOARD_JS)

print("All CTS Teachers data files generated successfully!")
