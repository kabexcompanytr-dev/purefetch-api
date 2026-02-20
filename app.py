from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

# FFmpeg yolunu buradan kontrol et
FFMPEG_PATH = 'C:/ffmpeg/bin'

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
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
            
            # YouTube haricindeki platformlar için bayrak
            is_youtube = "youtube" in url or "youtu.be" in url

            for f in info.get('formats', []):
                res = f.get('height')
                ext = f.get('ext')
                
                # Sadece hem ses hem görüntü olan (birleşik) veya sistemin birleştirebileceği formatları al
                if f.get('vcodec') != 'none':
                    
                    # YOUTUBE İÇİN: Standart listeyi kontrol et
                    if is_youtube:
                        if res in [360, 480, 720, 1080, 1440, 2160] and res not in seen_resolutions:
                            formats_list.append({
                                "quality": f"{res}p",
                                "ext": "mp4",
                                "url": f.get('url'),
                                "format_id": f.get('format_id'),
                                "type": "video"
                            })
                            seen_resolutions.add(res)
                    
                    # INSTAGRAM, TIKTOK VB. İÇİN: En kaliteli formatı yakala
                    else:
                        quality_label = f"{res}p" if res else "HD Video"
                        # Tekrar eden çözünürlükleri engelle ama her halükarda video ekle
                        if quality_label not in seen_resolutions:
                            formats_list.append({
                                "quality": quality_label,
                                "ext": "mp4",
                                "url": f.get('url') or info.get('url'),
                                "format_id": f.get('format_id'),
                                "type": "video"
                            })
                            seen_resolutions.add(quality_label)

            # EĞER HİÇ VİDEO BULUNAMADIYSA (Acil Durum Modu)
            if not any(item['type'] == 'video' for item in formats_list):
                formats_list.append({
                    "quality": "Yüksek Kalite",
                    "ext": "mp4",
                    "url": info.get('url'),
                    "format_id": "best",
                    "type": "video"
                })

            # MP3 SEÇENEĞİ (Her zaman ekle)
            formats_list.append({
                "quality": "MP3 Ses",
                "ext": "mp3",
                "url": "auto", 
                "format_id": "bestaudio",
                "type": "audio"
            })

            return jsonify({
                "title": info.get('title') or "Sosyal Medya Videosu",
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats_list
            })

    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify({"error": "İçerik analiz edilemedi."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)