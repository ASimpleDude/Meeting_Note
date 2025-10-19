from pydub import AudioSegment

# Đường dẫn file m4a
input_file = "voice_sample.m4a"
# File output wav
output_file = "voice_sample.wav"

# Đọc file m4a
audio = AudioSegment.from_file(input_file, format="m4a")

# Xuất file wav
audio.export(output_file, format="wav", parameters=["-ar", "24000"])  # 24kHz cho TTS

print(f"Hoàn tất! File WAV đã được tạo: {output_file}")
