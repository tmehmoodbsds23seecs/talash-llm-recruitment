# Folder-Based CV Ingestion Design

## Folder Structure:
project/
├── uploads/
│   ├── incoming/     (new CVs dropped here)
│   ├── processing/   (currently being processed)
│   └── processed/    (done)
├── output/
│   ├── extracted_data.csv
│   └── errors.log

## Ingestion Flow:
1. Watchdog library monitors 'uploads/incoming/'
2. When new PDF detected → move to 'processing/'
3. Extract text → send to LLM
4. Save results → move PDF to 'processed/'
5. Update master CSV file

## Code structure for Milestone 2:
def monitor_folder():
    while True:
        files = os.listdir('uploads/incoming/')
        for file in files:
            if file.endswith('.pdf'):
                process_cv(file)
        time.sleep(5)  # check every 5 seconds