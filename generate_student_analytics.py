import csv
import json
import os
from collections import defaultdict

CSV_PATH = os.path.join("CTS DATA", "Total Students-240402 (6).csv")
OUTPUT_JSON = os.path.join("data", "student_analytics.json")
OUTPUT_JS = os.path.join("data", "student_analytics.js")

print("Processing student dataset from:", CSV_PATH)

total_students = 0
boys = 0
girls = 0
cwsn_count = 0

class_order = ["Balvatika", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
class_counts = {c: 0 for c in class_order}

cluster_counts = defaultdict(int)
cluster_gender = defaultdict(lambda: {"boys": 0, "girls": 0, "total": 0})
social_counts = defaultdict(int)
management_counts = defaultdict(int)

# 2D Pivots
cluster_class_pivot = defaultdict(lambda: {c: 0 for c in class_order})
mgt_class_pivot = defaultdict(lambda: {c: 0 for c in class_order})
social_class_pivot = defaultdict(lambda: {c: 0 for c in class_order})

# Cluster gender pivot
cluster_gender_pivot = defaultdict(lambda: {"Male": 0, "Female": 0, "Total": 0})
# Management gender pivot
mgt_gender_pivot = defaultdict(lambda: {"Male": 0, "Female": 0, "Total": 0})

school_summaries = {}
initial_students = []

def normalize_class(val):
    v = str(val or "").strip()
    if v in ["0", "101", "102", "103", "", "Balvatika"]:
        return "Balvatika"
    if v in class_order:
        return v
    return "Balvatika"

with open(CSV_PATH, mode="r", encoding="utf-8-sig", errors="replace") as f:
    reader = csv.DictReader(f)
    for idx, row in enumerate(reader):
        total_students += 1
        gender = (row.get("Gender") or "").strip().title()
        if gender == "Male":
            boys += 1
        elif gender == "Female":
            girls += 1

        std_class = normalize_class(row.get("StudyingClass"))
        class_counts[std_class] += 1

        cluster = (row.get("Cluster") or "").strip() or "Unknown"
        cluster_counts[cluster] += 1
        if gender == "Male":
            cluster_gender[cluster]["boys"] += 1
            cluster_gender_pivot[cluster]["Male"] += 1
        else:
            cluster_gender[cluster]["girls"] += 1
            cluster_gender_pivot[cluster]["Female"] += 1
        cluster_gender[cluster]["total"] += 1
        cluster_gender_pivot[cluster]["Total"] += 1

        cluster_class_pivot[cluster][std_class] += 1

        soc = (row.get("SocialCategory") or "").strip() or "General"
        social_counts[soc] += 1
        social_class_pivot[soc][std_class] += 1

        mgt = (row.get("Management") or "").strip() or "Other"
        management_counts[mgt] += 1
        mgt_class_pivot[mgt][std_class] += 1
        if gender == "Male":
            mgt_gender_pivot[mgt]["Male"] += 1
        else:
            mgt_gender_pivot[mgt]["Female"] += 1
        mgt_gender_pivot[mgt]["Total"] += 1

        disability = (row.get("DisabilityName") or "").strip()
        is_cwsn = (row.get("IsCWSNCertificate_Desc") or "").strip()
        if disability or is_cwsn:
            cwsn_count += 1

        sch_id = (row.get("SchoolId") or "").strip()
        sch_name = (row.get("School") or "").strip()
        if sch_id not in school_summaries:
            school_summaries[sch_id] = {
                "school_id": sch_id,
                "school_name": sch_name,
                "cluster": cluster,
                "village": (row.get("Village") or "").strip(),
                "management": mgt,
                "category": (row.get("SchoolCategory") or "").strip(),
                "total": 0,
                "boys": 0,
                "girls": 0,
                "balvatika": 0
            }
        sch = school_summaries[sch_id]
        sch["total"] += 1
        if gender == "Male":
            sch["boys"] += 1
        else:
            sch["girls"] += 1
        if std_class == "Balvatika":
            sch["balvatika"] += 1

        # Keep initial 300 students for instant client rendering
        if len(initial_students) < 300:
            uid = (row.get("AadhaarUID") or "").strip().replace('"', '').replace("'", "")
            initial_students.append({
                "AadhaarUID": uid,
                "StudentName": (row.get("StudentName") or "").strip(),
                "FatherName": (row.get("FatherName") or "").strip(),
                "MotherName": (row.get("MotherName") or "").strip(),
                "SurName": (row.get("SurName") or "").strip(),
                "Gender": gender,
                "DOB": (row.get("DOB") or "").strip(),
                "StudentAge": (row.get("StudentAge") or "").strip(),
                "SocialCategory": soc,
                "StudyingClass": (row.get("StudyingClass") or "").strip(),
                "NormalizedClass": std_class,
                "Section": (row.get("Section") or "").strip(),
                "GRNo": (row.get("GRNo") or "").strip(),
                "SchoolId": sch_id,
                "School": sch_name,
                "Cluster": cluster,
                "Village": (row.get("Village") or "").strip(),
                "Management": mgt,
                "SchoolCategory": (row.get("SchoolCategory") or "").strip(),
                "Religion": (row.get("Religion") or "").strip(),
                "DisabilityName": disability,
                "WhetherHomeLess": (row.get("WhetherHomeLess") or "").strip(),
                "StudentStatus": (row.get("StudentStatus") or "").strip()
            })

primary_1_5 = sum(class_counts[str(i)] for i in range(1, 6))
upper_primary_6_8 = sum(class_counts[str(i)] for i in range(6, 9))
secondary_9_10 = sum(class_counts[str(i)] for i in range(9, 11))
higher_sec_11_12 = sum(class_counts[str(i)] for i in range(11, 13))
sec_higher_sec_9_12 = secondary_9_10 + higher_sec_11_12
balvatika_total = class_counts["Balvatika"]

analytics_data = {
    "kpis": {
        "total_students": total_students,
        "total_schools": len(school_summaries),
        "total_clusters": len(cluster_counts),
        "boys": boys,
        "girls": girls,
        "boys_percentage": round((boys / total_students) * 100, 2) if total_students else 0,
        "girls_percentage": round((girls / total_students) * 100, 2) if total_students else 0,
        "balvatika": balvatika_total,
        "primary_1_5": primary_1_5,
        "upper_primary_6_8": upper_primary_6_8,
        "secondary_9_10": secondary_9_10,
        "higher_sec_11_12": higher_sec_11_12,
        "sec_higher_sec_9_12": sec_higher_sec_9_12,
        "cwsn": cwsn_count
    },
    "class_order": class_order,
    "class_counts": class_counts,
    "clusters_list": sorted(list(cluster_counts.keys())),
    "cluster_counts": dict(cluster_counts),
    "cluster_gender": dict(cluster_gender),
    "social_counts": dict(social_counts),
    "management_counts": dict(management_counts),
    "cluster_class_pivot": {k: dict(v) for k, v in cluster_class_pivot.items()},
    "mgt_class_pivot": {k: dict(v) for k, v in mgt_class_pivot.items()},
    "social_class_pivot": {k: dict(v) for k, v in social_class_pivot.items()},
    "cluster_gender_pivot": {k: dict(v) for k, v in cluster_gender_pivot.items()},
    "mgt_gender_pivot": {k: dict(v) for k, v in mgt_gender_pivot.items()},
    "schools_summary": list(school_summaries.values()),
    "initial_students": initial_students
}

os.makedirs("data", exist_ok=True)

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(analytics_data, f, ensure_ascii=False, indent=2)

with open(OUTPUT_JS, "w", encoding="utf-8") as f:
    f.write("// Student Analytics Data for Offline and Fast Client Load\n")
    f.write("window.studentAnalyticsData = ")
    json.dump(analytics_data, f, ensure_ascii=False)
    f.write(";\n")

print("Generated:", OUTPUT_JSON, f"({os.path.getsize(OUTPUT_JSON)} bytes)")
print("Generated:", OUTPUT_JS, f"({os.path.getsize(OUTPUT_JS)} bytes)")
print("Total students processed:", total_students)
