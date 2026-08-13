import modal 
import os 
import tempfile
import boto3
import subprocess 
from subprocess import CalledProcessError

cuda_version = "12.8.1"
flavor = "devel"
operating_sys = "ubuntu24.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"

image = (
    modal.Image.from_registry(
        f"nvidia/cuda:{tag}", add_python="3.11"
    )
    .apt_install("ffmpeg")
    .pip_install("faster-whisper", "boto3")
)

app = modal.App("transcriber")

@app.cls(gpu="L4", secrets=[modal.Secret.from_name("transcript-maker")], image=image)
class TranscriptMaker:

    @modal.enter()
    def startup(self): 
        from faster_whisper import WhisperModel # type: ignore
        self.model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")

    @modal.method()
    def get_transcript(self, bucket, s3_key):
        s3_bucket_info = {"bucket" : bucket, "s3_key" : s3_key}
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
            aws_access_key_id=os.environ["AWS_S3_ACCESS_KEY"],
            aws_secret_access_key=os.environ["AWS_S3_SECRET_KEY"],
            region_name=os.environ["AWS_REGION"],
        ) 
        s3_client.download_file(s3_bucket_info.get("bucket"), s3_bucket_info.get("s3_key"), vid_file)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", vid_file,
                    "-vn",
                    "-ac", "1",
                    "-ar", "16000",
                    "-c:a", "libmp3lame",
                    "-b:a", "32k",
                    audio_file,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True
                )
        except CalledProcessError as exc:
           raise RuntimeError(f"ffmpeg failed: {exc.stderr}") from exc
        
    def __transcribe(self, audio_file):
        segments, _ = self.model.transcribe(audio_file, beam_size=1, word_timestamps=True)
        transcript_json = self.__parse_whisper_response_json(segments)
        return transcript_json
    
    def __parse_whisper_response_json(self, segments):
        transcript_json = {"segments" : [], "words" : []}
        for segment in segments:
            transcript_json["segments"].append(
                {
                    "id" : segment.id,
                    "start" : segment.start,
                    "end" : segment.end,
                    "text" : segment.text,
                    "words" : [
                       { "start" : word.start,
                         "end" : word.end,
                         "word" : word.word
                        } for word in (segment.words or [])
                    ]
                }
            )
            for word in (segment.words or []):
                transcript_json["words"].append(
                    {
                        "start" : word.start,
                         "end" : word.end,
                         "word" : word.word
                    }
                )
        return transcript_json
         
