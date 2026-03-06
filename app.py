from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import shutil
import subprocess
import uuid
import threading
import time
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

FFMPEG_PATH = 'C:/ffmpeg/bin/ffmpeg.exe' if os.name == 'nt' else shutil.which('ffmpeg')

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def delete_later(file_path):
    time.sleep(300) 
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Sunucu temizlendi: {file_path}")
    except Exception as e:
        logging.error(f"Temizlik hatası: {e}")

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
    is_premium = data.get('is_premium', False)

    if not url:
        return jsonify({"error": "URL gerekli"}), 400

    # YouTube kısıtlamalarını aşmak için yeni seçenekler eklendi
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'ffmpeg_location': FFMPEG_PATH,
        'geo_bypass': True,  # Bölge kısıtlamasını aşmaya çalış
        'geo_bypass_country': 'TR', # Türkiye üzerinden erişiyormuş gibi yap
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats_list = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                res = f.get('height')
                if f.get('vcodec') != 'none' and res:
                    if res in [360, 720, 1080] and res not in seen_resolutions:
                        formats_list.append({
                            "quality": f"{res}p",
                            "ext": "mp4",
                            "format_id": f.get('format_id'),
                            "type": "video",
                            "watermark": not is_premium 
                        })
                        seen_resolutions.add(res)

            return jsonify({
                "title": info.get('title') or "PureFetch Video",
                "thumbnail": info.get('thumbnail'),
                "formats": formats_list,
                "original_url": url
            })
    except Exception as e:
        logging.error(f"Analyze Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download-processed', methods=['POST'])
def download_processed():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    is_premium = data.get('is_premium', False)

    unique_id = str(uuid.uuid4())[:8]
    output_filename = f"purefetch_{unique_id}.mp4"
    output_path = os.path.join(DOWNLOAD_FOLDER, output_filename)

    ydl_opts = {
        'format': f"{format_id}+bestaudio/best",
        'outtmpl': output_path,
        'ffmpeg_location': FFMPEG_PATH,
        'merge_output_format': 'mp4',
        'geo_bypass': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'postprocessor_args': ['-c:v', 'libx264', '-preset', 'veryfast']
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not is_premium:
            temp_output = output_path.replace(".mp4", "_wm.mp4")
            cmd = [
                FFMPEG_PATH, '-y', '-i', output_path,
                '-vf', "drawtext=text='PureFetch':x=w-tw-20:y=h-th-20:fontsize=24:fontcolor=white@0.5",
                '-codec:a', 'copy', temp_output
            ]
            subprocess.run(cmd, check=True)
            if os.path.exists(temp_output):
                os.remove(output_path)
                os.rename(temp_output, output_path)

        threading.Thread(target=delete_later, args=(output_path,)).start()
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        logging.error(f"Download Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port) 