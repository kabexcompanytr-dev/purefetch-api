from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import shutil

app = Flask(__name__)
CORS(app)

# ORTAM KONTROLÜ: Render (Linux) mı yoksa Windows mu?
# Render'da ffmpeg sistem yolundadır, Windows'ta senin belirttiğin yerdedir.
FFMPEG_PATH = 'C:/ffmpeg/bin' if os.name == 'nt' else shutil.which('ffmpeg')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
    
    # PREMIUM KONTROLÜ (İleride burayı kullanıcı girişine bağlayacağız)
    # Şimdilik varsayılan olarak False yapıyoruz ki filigran mantığı çalışsın
    is_premium = data.get('is_premium', False)

    if not url:
        return jsonify({"error": "URL gerekli"}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats_list = []
            seen_resolutions = set()
            
            is_youtube = "youtube" in url or "youtu.be" in url

            for f in info.get('formats', []):
                res = f.get('height')
                
                if f.get('vcodec') != 'none':
                    if is_youtube:
                        if res in [360, 480, 720, 1080] and res not in seen_resolutions:
                            # FİLİGRAN NOTU: 
                            # Eğer kullanıcı premium değilse, video linkinin sonuna 
                            # bir işaret koyabilir veya backend'de işleyebiliriz.
                            # Şimdilik doğrudan url'leri dönüyoruz.
                            formats_list.append({
                                "quality": f"{res}p",
                                "ext": "mp4",
                                "url": f.get('url'),
                                "format_id": f.get('format_id'),
                                "type": "video",
                                "watermark": not is_premium # Frontend'e bilgi veriyoruz
                            })
                            seen_resolutions.add(res)
                    
                    else:
                        quality_label = f"{res}p" if res else "HD Video"
                        if quality_label not in seen_resolutions:
                            formats_list.append({
                                "quality": quality_label,
                                "ext": "mp4",
                                "url": f.get('url') or info.get('url'),
                                "format_id": f.get('format_id'),
                                "type": "video",
                                "watermark": not is_premium
                            })
                            seen_resolutions.add(quality_label)

            # MP3 SEÇENEĞİ
            formats_list.append({
                "quality": "MP3 Ses",
                "ext": "mp3",
                "url": "auto", 
                "format_id": "bestaudio",
                "type": "audio",
                "watermark": False # Sese filigran koymuyoruz
            })

            return jsonify({
                "title": info.get('title') or "PureFetch Video",
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats_list,
                "is_premium_user": is_premium
            })

    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify({"error": "İçerik analiz edilemedi."}), 500

if __name__ == '__main__':
    # Render için portu dinamik almalıyız
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)