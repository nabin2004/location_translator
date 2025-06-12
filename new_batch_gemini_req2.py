import pandas as pd
import google.generativeai as genai
import os
import re
import ast
from dotenv import load_dotenv
from datetime import datetime
import config

# Load environment variables from .env
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("GOOGLE_API_KEY not found in environment or .env file.")
    exit()
else:
    genai.configure(api_key=api_key)

def get_timestamped_path(base_path):
    base, ext = os.path.splitext(base_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}{ext}"

def translate_nepali_to_english_batch(texts_to_translate):
    if not texts_to_translate:
        return []

    try:
        model = genai.GenerativeModel(config.MODEL)
        input_texts_formatted = "\n".join([f"Item {i+1}: {text}" for i, text in enumerate(texts_to_translate)])

        prompt = (
            f"Translate the following Nepali texts to English. "
            f"Return each with the prefix 'Translation for Item X:' where X is the number from the list.\n\n"
            f"{input_texts_formatted}"
        )

        response = model.generate_content(prompt)
        translated_lines = response.text.strip().split('\n')
        translations_dict = {}

        for line in translated_lines:
            match = re.match(r"Translation for Item (\d+): (.*)", line.strip())
            if match:
                idx = int(match.group(1)) - 1
                translations_dict[idx] = match.group(2).strip()

        return [translations_dict.get(i, "Translation not found.") for i in range(len(texts_to_translate))]

    except Exception as e:
        print(f"Error during translation: {e}")
        return [f"API Error: {e}" for _ in texts_to_translate]


if __name__ == "__main__":
    try:
        df = pd.read_csv(config.INPUT_CSV_PATH)
        print(f"Loaded CSV with {len(df)} rows.")

        # Apply row slicing from config
        if config.ROW_END is not None:
            df = df.iloc[config.ROW_START:config.ROW_END]
            print(f"Processing rows {config.ROW_START} to {config.ROW_END}")
        else:
            df = df.iloc[config.ROW_START:]
            print(f"Processing rows from {config.ROW_START} to end")

        # Translate 'sentence' column
        sentences = df['sentence'].astype(str).tolist()
        print("Translating sentences...")
        translated_sentences = translate_nepali_to_english_batch(sentences)
        df['translated_sentence_en'] = translated_sentences
        print("Sentence translation completed.")

        # Save failed sentence translations
        failed_sentence_indices = [
            idx for idx, text in enumerate(translated_sentences)
            if "Translation not found" in text or "API Error" in text
        ]
        if failed_sentence_indices:
            failed_sent_df = df.iloc[failed_sentence_indices]
            failed_sent_df.to_csv(get_timestamped_path(config.FAILED_SENTENCE_PATH), index=False)
            print(f"Saved {len(failed_sent_df)} failed sentence translations.")

        # Translate matched locations
        print("Translating unique matched_locations...")
        all_locations = df['matched_locations'].dropna().astype(str).apply(
            lambda x: ast.literal_eval(x) if x.startswith("[") else [])
        flattened = set(loc.strip() for sublist in all_locations for loc in sublist if loc.strip())
        unique_locations = sorted(flattened)

        print(f"Found {len(unique_locations)} unique location strings.")
        translated_locations = translate_nepali_to_english_batch(unique_locations)
        location_map = dict(zip(unique_locations, translated_locations))

        # Save failed location translations
        failed_location_entries = [
            (orig, trans) for orig, trans in zip(unique_locations, translated_locations)
            if "Translation not found" in trans or "API Error" in trans
        ]
        if failed_location_entries:
            failed_loc_df = pd.DataFrame(failed_location_entries, columns=["original_location", "translation"])
            failed_loc_df.to_csv(get_timestamped_path(config.FAILED_LOCATION_PATH), index=False)
            print(f"Saved {len(failed_loc_df)} failed location translations.")

        # Map matched_locations to their English equivalents
        def translate_location_list(loc_str):
            try:
                loc_list = ast.literal_eval(loc_str)
                return [location_map.get(loc.strip(), "Translation not found.") for loc in loc_list]
            except:
                return []

        df['matched_locations_en'] = df['matched_locations'].astype(str).apply(translate_location_list)

        # Save final output with timestamp
        final_output_path = get_timestamped_path(config.OUTPUT_CSV_PATH)
        df.to_csv(final_output_path, index=False)
        print(f"Saved translated output to '{final_output_path}'.")

        print("\n--- Sample Output ---")
        print(df[['sentence', 'translated_sentence_en', 'matched_locations', 'matched_locations_en']].head())

    except FileNotFoundError:
        print(f"File not found: {config.INPUT_CSV_PATH}")
    except KeyError as ke:
        print(f"Missing column: {ke}")
    except Exception as e:
        print(f"Unexpected error: {e}")
