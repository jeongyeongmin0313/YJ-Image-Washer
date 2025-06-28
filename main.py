        from flask import Flask, render_template, request, send_from_directory, url_for
        import os
        import random
        from PIL import Image, ImageSequence
        import piexif
        from datetime import datetime, timedelta
        # 한글/특수문자 URL 처리를 위한 라이브러리 추가
        from urllib.parse import quote

        # --- 이미지 세탁 로직 (변경 없음) ---
        def generate_random_exif():
            camera_models = {
                "Canon": ["Canon EOS 5D Mark IV", "Canon EOS R5"], "NIKON CORPORATION": ["NIKON D850", "NIKON Z 7"],
                "SONY": ["ILCE-7M3", "ILCE-9"], "Apple": ["iPhone 14 Pro", "iPhone 13"]
            }
            make = random.choice(list(camera_models.keys()))
            model = random.choice(camera_models[make])
            now = datetime.now()
            random_date = now - timedelta(days=random.randint(0, 365*5))
            date_str = random_date.strftime("%Y:%m:%d %H:%M:%S")
            exif_dict = {
                "0th": {piexif.ImageIFD.Make: make.encode('utf-8'), piexif.ImageIFD.Model: model.encode('utf-8'), piexif.ImageIFD.DateTime: date_str.encode('utf-8')},
                "Exif": {piexif.ExifIFD.DateTimeOriginal: date_str.encode('utf-8'), piexif.ExifIFD.DateTimeDigitized: date_str.encode('utf-8')},
                "GPS": {}, "1st": {},
            }
            return piexif.dump(exif_dict)

        def wash_image(input_path, output_path):
            try:
                img = Image.open(input_path)
                file_ext = os.path.splitext(input_path)[1].lower()
                if file_ext in ['.jpg', '.jpeg']:
                    new_exif = generate_random_exif()
                    img.save(output_path, 'jpeg', quality=95, exif=new_exif)
                elif file_ext == '.png':
                    img.save(output_path, 'png')
                elif file_ext == '.gif':
                    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                    frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=img.info.get('duration', 100), loop=0, disposal=2)
                else:
                    return False
                return True
            except Exception as e:
                print(f"Error washing image: {e}")
                return False

        # --- Flask 웹 애플리케이션 설정 ---
        app = Flask(__name__)
        UPLOAD_FOLDER = 'uploads'
        WASHED_FOLDER = 'washed'
        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        app.config['WASHED_FOLDER'] = WASHED_FOLDER
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(WASHED_FOLDER, exist_ok=True)

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        # --- 웹페이지 라우트(주소) 설정 ---
        @app.route('/')
        def index():
            return render_template('index.html')

        @app.route('/wash', methods=['POST'])
        def wash_route():
            if 'image_file' not in request.files:
                return render_template('index.html', error='파일이 선택되지 않았습니다.')
            file = request.files['image_file']
            if file.filename == '':
                return render_template('index.html', error='파일이 선택되지 않았습니다.')
            if file and allowed_file(file.filename):
                # 원본 파일에서 확장자만 가져오기
                _, file_extension = os.path.splitext(file.filename)

                # 원본 파일을 임시로 저장
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], "temp" + file_extension)
                file.save(temp_path)

                # 새로운 파일명 생성: washer연월일시분초.확장자
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = f"washer{timestamp}{file_extension}"

                washed_path = os.path.join(app.config['WASHED_FOLDER'], new_filename)
                success = wash_image(temp_path, washed_path)

                if success:
                    # URL에는 ASCII 문자만 있으므로 인코딩이 필수는 아니지만, 안전을 위해 유지합니다.
                    encoded_filename = quote(new_filename)
                    return render_template('index.html', 
                                           washed_image_url=url_for('get_washed_file', filename=encoded_filename),
                                           download_filename=new_filename)
                else:
                    return render_template('index.html', error='이미지 처리 중 오류가 발생했습니다.')
            else:
                return render_template('index.html', error='허용되지 않는 파일 형식입니다.')

        @app.route('/washed/<filename>')
        def get_washed_file(filename):
            return send_from_directory(app.config['WASHED_FOLDER'], filename, as_attachment=True)