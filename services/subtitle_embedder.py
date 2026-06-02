from collections import deque 
import os 
import subprocess
import threading 

class SubtitleEmbedder:
    def __init__(self, video_path, subtitle_path):
        self.__video_path = video_path
        self.__subtitle_path = subtitle_path

    def embed_streaming(self):
        stderr_lines = deque(maxlen=100)
        child_process_completed = False 
        error = None 
        
        process = subprocess.Popen(
            ["ffmpeg",
            "-i", self.__video_path,
            "-vf", f"subtitles={self.__subtitle_path}",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov",
            "-",],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            thread = threading.Thread(target=self.__drain_stderr, args=(process, stderr_lines), daemon=True)
            thread.start()
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    child_process_completed = True
                    break
                yield chunk 
        finally:
            if child_process_completed:
                 return_code = process.wait()
                 thread.join(timeout=1)
                 if return_code != 0:
                     error = RuntimeError(f"failed with code {return_code}: {''.join(stderr_lines)}")
            else:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                        thread.join(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        thread.join()
            if error:
                raise error 
                      

    def __drain_stderr(self, process, stderr_lines):
        for err in process.stderr:
            stderr_lines.append(err)
     