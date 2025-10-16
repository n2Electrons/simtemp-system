#!/usr/bin/env python3
"""
Cleanup script for test artifacts and temporary files.
Removes accumulated test detail files to prevent Jenkins console spam.
"""

import os
import glob
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def clean_timestamped_test_details(directory="/tmp"):
    """Clean up timestamped test_details_*.json files"""
    # Pattern for timestamped files: test_details_*_YYYYMMDD_HHMMSS.json
    pattern = os.path.join(
        directory,
        "test_details_*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_"
        "[0-9][0-9][0-9][0-9][0-9][0-9].json"
    )
    
    files_to_delete = glob.glob(pattern)
    
    if not files_to_delete:
        logger.info(f"No timestamped files found in {directory}")
        return 0
    
    count = len(files_to_delete)
    logger.info(f"Found {count} timestamped test detail files to clean up")
    
    deleted_count = 0
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            logger.debug(f"Deleted: {os.path.basename(file_path)}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
    
    logger.info(f"Successfully deleted {deleted_count} timestamped files")
    return deleted_count


def clean_empty_json_files(directory="/tmp"):
    """Clean up empty or malformed JSON files"""
    pattern = os.path.join(directory, "test_details_*.json")
    files_to_check = glob.glob(pattern)
    
    if not files_to_check:
        logger.info(f"No test detail files found in {directory}")
        return 0
    
    deleted_count = 0
    for file_path in files_to_check:
        try:
            # Check if file is empty
            if os.path.getsize(file_path) == 0:
                os.remove(file_path)
                filename = os.path.basename(file_path)
                logger.info(f"Deleted empty file: {filename}")
                deleted_count += 1
                continue
                
            # Check if file contains valid JSON
            import json
            with open(file_path, 'r') as f:
                json.load(f)
                
        except (json.JSONDecodeError, Exception):
            try:
                os.remove(file_path)
                filename = os.path.basename(file_path)
                logger.info(f"Deleted malformed file: {filename}")
                deleted_count += 1
            except Exception as del_error:
                logger.error(f"Failed to delete malformed file: {del_error}")
    
    if deleted_count > 0:
        logger.info(f"Successfully deleted {deleted_count} bad JSON files")
    else:
        logger.info("No empty or malformed JSON files found")
    
    return deleted_count


def clean_old_reports(reports_dir="reports"):
    """Clean up old report files (keep only the latest)"""
    if not os.path.exists(reports_dir):
        logger.info(f"Reports dir {reports_dir} not found, skipping cleanup")
        return 0
    
    # Pattern for old report files with timestamps
    pattern = os.path.join(reports_dir, "test_report_*_[0-9]*.html")
    old_reports = glob.glob(pattern)
    
    deleted_count = 0
    for report in old_reports:
        try:
            os.remove(report)
            logger.debug(f"Deleted old report: {os.path.basename(report)}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {report}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Successfully deleted {deleted_count} old reports")
    
    return deleted_count


def main():
    """Main cleanup function"""
    logger.info("🧹 Starting test artifacts cleanup...")
    
    total_deleted = 0
    
    # Clean timestamped test detail files
    total_deleted += clean_timestamped_test_details("/tmp")
    
    # Clean empty/malformed JSON files
    total_deleted += clean_empty_json_files("/tmp")
    
    # Clean old report files
    current_dir = Path(__file__).parent
    reports_dir = current_dir / "reports"
    total_deleted += clean_old_reports(str(reports_dir))
    
    logger.info(f"✅ Cleanup completed. Total files deleted: {total_deleted}")
    
    return 0 if total_deleted >= 0 else 1


if __name__ == "__main__":
    exit(main())
