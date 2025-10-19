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

# =========================
# TTS libraries
# =========================
from transformers import VitsModel, AutoTokenizer
import torch
import soundfile as sf
import os, uuid

# Load TTS model (một lần khi khởi động server)
tts_model = VitsModel.from_pretrained("facebook/mms-tts-vie")
tts_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
TTS_OUTPUT_DIR = "api/artifacts/audio"
os.makedirs(TTS_OUTPUT_DIR, exist_ok=True)

def generate_tts_audio(session_id: str, text: str) -> str:
    """
    Sinh file TTS và trả về đường dẫn tuyệt đối để mở bằng file:///...
    """
    print("Generating TTS audio...")

    # Tokenize và inference
    inputs = tts_tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = tts_model(**inputs).waveform
    sampling_rate = tts_model.config.sampling_rate

    # Tạo tên file an toàn
    filename = f"{session_id}_{uuid.uuid4().hex}.wav"
    output_path = os.path.join(TTS_OUTPUT_DIR, filename)

    # Lưu file
    sf.write(output_path, waveform[0].numpy(), sampling_rate)

    # Trả về đường dẫn tuyệt đối cho file:///...
    return os.path.abspath(output_path)
