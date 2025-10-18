# Step 1: Install required packages (run in terminal or notebook)
# pip install transformers torch IPython

# Step 2: Import required libraries
from transformers import VitsModel, AutoTokenizer
import torch
import soundfile as sf
from IPython.display import Audio

# Step 3: Clone and load the pre-trained TTS model from Hugging Face
model = VitsModel.from_pretrained("facebook/mms-tts-vie")  # You may replace this with any compatible TTS model
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")

# Step 4: Function to generate audio from text
def text_to_speech(text):
    # Step 5: Tokenize the input text
    inputs = tokenizer(text, return_tensors="pt")
    
    # Step 6: Perform inference to generate the waveform
    with torch.no_grad():
        output = model(**inputs).waveform
    
    # Return the audio data and sampling rate
    return output.numpy(), model.config.sampling_rate


def save_audio_to_file(text, output_path):

    # Generate audio
    waveform, sampling_rate = text_to_speech(text)
    
    # Save to file
    sf.write(output_path, waveform[0], sampling_rate)
    
    return output_path
