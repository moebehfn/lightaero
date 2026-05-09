import os
import sys
from pathlib import Path


def get_all_python_files(directory):
    files = []
    base_path = Path(directory)
    for p in base_path.rglob("*.py"):
        if p.name.startswith(".") or "/." in str(p):
            continue
        files.append(str(p))
    return sorted(files)


def check_coverage(report_path, source_dir):
    if not os.path.exists(report_path):
        print(f"Error: Report file not found at {report_path}")
        return False

    with open(report_path) as f:
        report_content = f.read()

    python_files = get_all_python_files(source_dir)
    missing_files = []

    for file_path in python_files:
        # Check if the file path is present in the report
        # We look for the file path as a standalone entry in a table or list
        if file_path not in report_content:
            missing_files.append(file_path)

    if missing_files:
        print("Error: The following files are missing from the audit report:")
        for f in missing_files:
            print(f"  - {f}")
        print(f"\nTotal missing: {len(missing_files)}")
        return False

    print(f"Success: All {len(python_files)} files are covered in the report.")
    return True


if __name__ == "__main__":
    report = ".planning/phases/06-doc-audit/AUDIT_REPORT.md"
    src = "src/lightaero"

    if not check_coverage(report, src):
        sys.exit(1)
    sys.exit(0)
