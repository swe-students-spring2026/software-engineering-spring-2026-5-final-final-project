import time
import sys
import json
import os

# Import core functions directly from your original script
from scraper import (
    search, 
    get_class_details, 
    result_to_document, 
    SCHOOL_CODES, 
    make_id, 
    split_code,
    MongoJSONEncoder
)

TERMS = ["1268", "1266"] # Summer and Fall 2026
DELAY = 0.1
OUTPUT_FILE = "all_classes_backup.ndjson"

def load_completed_ids():
    """Reads the backup file and remembers which classes already have descriptions."""
    seen_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    doc = json.loads(line)
                    # If it has a description, it was successfully fully scraped
                    if "description" in doc: 
                        seen_ids.add(doc["_id"])
                except json.JSONDecodeError:
                    continue
    return seen_ids

def run_local_resumable_scrape():
    seen_ids = load_completed_ids()
    print(f"📂 Loaded {len(seen_ids)} previously scraped classes from {OUTPUT_FILE}")

    # Open in append mode ("a") to safely resume without overwriting
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
        
        for term in TERMS:
            print(f"\n{'='*40}\n🚀 Starting Term: {term}\n{'='*40}")
            
            # Loop directly through your established dictionary of schools
            for school_name, school_code in SCHOOL_CODES.items():
                print(f"\n🏫 Fetching catalog for: {school_name}...")
                
                # Fetch all classes for the school at once using YOUR search function
                results = search(term, [{"field": "coll", "value": school_code}])
                
                if not results:
                    continue
                    
                print(f"   Found {len(results)} classes.")
                
                for i, r in enumerate(results, 1):
                    code_full = r.get("code", "")
                    subject_code, catalog_number = split_code(code_full)
                    section = r.get("no", "")
                    doc_id = make_id(term, subject_code, catalog_number, section)
                    
                    # Skip if we already saved it in a previous run
                    if doc_id in seen_ids:
                        print(f"    [{i}/{len(results)}] ⏩ SKIPPED (Already in file): {code_full}")
                        continue

                    crn = r.get("crn", "")
                    print(f"    [{i}/{len(results)}] ⬇️ FETCHING: {code_full}...")
                    
                    # Fetch details and merge using YOUR functions
                    details = get_class_details(code_full, crn, term)
                    doc = result_to_document(r, term, details)
                    
                    # Save immediately to the file
                    json_string = json.dumps(doc, ensure_ascii=False, cls=MongoJSONEncoder)
                    file.write(json_string + "\n")
                    file.flush() # Force write to disk immediately so crashes don't lose data
                    
                    seen_ids.add(doc_id)
                    time.sleep(DELAY)

if __name__ == "__main__":
    try:
        run_local_resumable_scrape()
        print(f"\n✅ Scrape complete! All data safely saved to {OUTPUT_FILE}")
    except KeyboardInterrupt:
        print(f"\n🛑 Paused manually. Your data up to this point is safe in {OUTPUT_FILE}.")
    except Exception as e:
        print(f"\n❌ Script crashed: {e}. Your data up to the crash is safe.")
        sys.exit(1)