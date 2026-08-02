import modal 
from dotenv import load_dotenv
import os 
import tempfile
import boto3
import subprocess 


app = modal.App()

@app.cls(cpu=8)
class TranscriptMaker:

    @modal.enter()
    def startup(self):
        from faster_whisper import WhisperModel # type: ignore
        self.model = WhisperModel("distil-large-v3", device="cuba")

    @modal.method
    def get_transcript(self, bucket, video_id):
        s3_bucket_info = {"bucket" : bucket, "obj_name" : video_id}
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as temp_vid:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                try:
                    self.__convert_to_audio(s3_bucket_info, temp_vid.name ,temp_audio.name)
                    transcript = self.__transcribe(temp_audio.name) 
                except Exception as err:
                    return str(err)
        if os.path.exists(temp_audio.name):
            os.unlink(temp_audio.name)
        return transcript


    def __convert_to_audio(self, s3_bucket_info, vid_file, audio_file):
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION"),
        ) 
        s3_client.download_file(s3_bucket_info.get("bucket"), s3_bucket_info.get("obj_name"), vid_file)
        subprocess.run(
            [
                "ffmpeg",
                "-i", vid_file,
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "libmp3lame",
                "-b:a", "32k",
                audio_file,
            ],
            check=True
        )
        


    def __transcribe(self, audio_file):
        segments, info = self.model.transcribe(audio_file, beam_size=1)
         
