# config.py

# Row slicing (inclusive start, exclusive end)

# DONE
# ROW_START = 0
# ROW_END = 200

ROW_START = 200
ROW_END = 400  # WE CAN CHANGE THIS TO NONE FOR PROCESSING ALL ROWS

# CSV paths
INPUT_CSV_PATH = './final_locations-1.csv'
OUTPUT_CSV_PATH = './output/translated_10k_with_locations.csv'
FAILED_SENTENCE_PATH = './output/failed_sentence_translations.csv'
FAILED_LOCATION_PATH = './output/failed_location_translations.csv'
MODEL = "gemini-2.0-flash"
