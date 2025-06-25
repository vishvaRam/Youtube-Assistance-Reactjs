from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api.formatters import TextFormatter
import re
from datetime import datetime
import os
import time

def get_video_id(url):
    """Extract video ID from YouTube URL"""
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def merge_transcript_segments(transcript_list, max_gap_seconds=1.5):
    """
    Merge transcript segments into full sentences.
    Uses punctuation and small gaps between entries to detect sentence ends.
    """
    if not transcript_list:
        return []

    merged = []
    current_segment = {
        "start": transcript_list[0]['start'],
        "end": transcript_list[0]['end'],
        "text": transcript_list[0]['text'].strip()
    }

    sentence_end_punct = {'.', '?', '!', '"', "'", ')'}
    
    for entry in transcript_list[1:]:
        prev_text = current_segment['text']
        current_text = entry['text'].strip()

        # Check if previous segment ends with sentence-ending punctuation
        ends_with_sentence_end = len(prev_text) > 0 and prev_text[-1] in sentence_end_punct
        # Or check if there's a gap larger than threshold between entries
        starts_new = entry['start'] > current_segment['end'] + max_gap_seconds

        if ends_with_sentence_end or starts_new:
            # Finalize current segment
            merged.append(current_segment)
            # Start new segment
            current_segment = {
                "start": entry['start'],
                "end": entry['end'],
                "text": current_text
            }
        else:
            # Continue building segment
            current_segment['text'] += " " + current_text
            current_segment['end'] = entry['end']

    # Add the last one
    merged.append(current_segment)
    return merged


def get_clean_transcript(url, max_retries=3, retry_delay=2):
    """Get clean transcript with full sentences and correct timestamps with retry mechanism"""
    for attempt in range(max_retries):
        try:
            video_id = get_video_id(url)
            if not video_id:
                return "Error: Invalid YouTube URL"
            
            print(f"Fetching transcript for video ID: {video_id} (Attempt {attempt + 1})")
            
            transcript_list = None
            error_message = None
            
            try:
                # Get transcript list object first
                transcript_obj = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Get all available transcripts first
                available_transcripts = transcript_obj._manually_created_transcripts
                available_transcripts.update(transcript_obj._generated_transcripts)
                
                if not available_transcripts:
                    return "Error: No transcripts available for this video"
                
                print(f"Available languages: {list(available_transcripts.keys())}")
                
                # Try direct transcript fetch first
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                    print("✅ Successfully fetched English transcript directly")
                except Exception as e:
                    print(f"Direct transcript fetch failed: {str(e)}")
                    
                    # Try to get any English variant
                    english_variants = [lang for lang in available_transcripts.keys() 
                                        if lang.startswith('en')]
                    
                    if english_variants:
                        print(f"Found English variants: {english_variants}")
                        for lang in english_variants:
                            try:
                                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                                if transcript_list:
                                    print(f"✅ Successfully fetched {lang} transcript")
                                    break
                            except Exception as e:
                                print(f"Failed to fetch {lang} transcript: {str(e)}")
                                continue
                            
                    # If still no transcript, try non-English transcripts
                    if not transcript_list:
                        for lang in available_transcripts.keys():
                            if not lang.startswith('en'):
                                try:
                                    transcript = transcript_obj.find_transcript([lang])
                                    translated = transcript.translate('en')
                                    transcript_list = translated.fetch()
                                    print(f"✅ Successfully translated {lang} transcript to English")
                                    break
                                except Exception as e:
                                    print(f"Failed to translate {lang} transcript: {str(e)}")
                                    continue
                
            except TranscriptsDisabled:
                return "Error: Transcripts are disabled for this video"
            except Exception as e:
                error_message = str(e)
                print(f"Error accessing transcripts: {error_message}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue  # Retry the loop
                else:
                    return f"Error: Could not access video transcripts. {error_message}"

            if not transcript_list:
                if attempt < max_retries - 1:
                    print(f"No transcript found. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return "Error: Could not fetch any transcript for this video. Please check if the video has captions enabled."

            # Add missing 'end' field where necessary
            for entry in transcript_list:
                if 'end' not in entry:
                    entry['end'] = entry['start'] + entry.get('duration', 0)

            # Merge broken-up segments into full sentences
            cleaned_segments = merge_transcript_segments(transcript_list)
            
            if not cleaned_segments:
                return "Error: No transcript segments were generated"

            # Save to file
            os.makedirs('transcripts', exist_ok=True)
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcripts/transcript_{video_id}_{current_time}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                for seg in cleaned_segments:
                    text = seg['text'].strip()
                    line = f"{text}\n"
                    # print(line.strip())
                    f.write(line)

            return f"✅ Transcript saved to '{filename}' successfully"

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                return f"Error: {str(e)}"

    return "Error: Failed to fetch transcript after multiple retries."

# # Example usage
# if __name__ == "__main__":
#     youtube_url = "https://www.youtube.com/watch?v=HNpYAz_I4yY"
    
#     result = get_clean_transcript(youtube_url)
#     print(result)
