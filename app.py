import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(path):
    with Image.open(path) as image:
        if image.format not in {'JPEG', 'PNG'}:
            raise ValueError('Use a PNG or JPEG image')
        if image.width * image.height > 20_000_000:
            raise ValueError('Image exceeds the pixel limit')
        image.verify()


def create_app(classifier=None):
    application = Flask(__name__)
    application.config['MAX_CONTENT_LENGTH'] = MAX_IMAGE_BYTES + 64 * 1024
    application.config['CLASSIFIER_ENABLED'] = os.getenv('ENABLE_PRETRAINED_MODEL') == 'true'
    application.config['LEGACY_CRAWLER_ENABLED'] = os.getenv('ENABLE_LEGACY_CRAWLER') == 'true'

    def classify(path, filename):
        predictor = classifier
        if predictor is None:
            if not application.config['CLASSIFIER_ENABLED']:
                raise RuntimeError('Classifier is not enabled')
            from classifier import Classifier
            predictor = Classifier.classify_file
        result = predictor(path)
        return {'filename': filename, 'label': result['label'], 'probability': result['probability']}

    @application.get('/status')
    def status():
        return jsonify(status='API is up and running', classifier_enabled=application.config['CLASSIFIER_ENABLED'], legacy_crawler_enabled=application.config['LEGACY_CRAWLER_ENABLED'])

    @application.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(message='Image must be no larger than 5 MiB'), 413

    @application.post('/file')
    def upload():
        image = request.files.get('image')
        if image is None or not image.filename or len(request.files) != 1 or len(request.files.getlist('image')) != 1:
            return jsonify(message="Provide one image using the 'image' field"), 400
        try:
            with tempfile.TemporaryDirectory(prefix='tweet-image-') as directory:
                path = Path(directory) / 'upload-image'
                image.save(path)
                if path.stat().st_size > MAX_IMAGE_BYTES:
                    raise RequestEntityTooLarge()
                validate_image(path)
                result = classify(path, secure_filename(image.filename) or 'upload-image')
                return jsonify(predictions=[result])
        except RequestEntityTooLarge:
            raise
        except (UnidentifiedImageError, ValueError, OSError):
            return jsonify(message='Provide a valid PNG/JPEG image within the size and pixel limits'), 400
        except (ImportError, RuntimeError):
            return jsonify(message='Image classifier is not enabled or available on this server'), 503
        except Exception:
            return jsonify(message='Image classification failed'), 500

    @application.get('/keyword')
    def keyword():
        if not application.config['LEGACY_CRAWLER_ENABLED'] or not application.config['CLASSIFIER_ENABLED']:
            return jsonify(message='Legacy profile-image crawling is disabled on this server'), 503
        handle = request.args.get('keyword', '')
        import re
        if not re.fullmatch(r'[A-Za-z0-9_]{1,32}', handle):
            return jsonify(message='Provide a simple profile handle'), 400
        try:
            from crawler import Crawler, is_allowed_media_url
            import requests
            crawler = Crawler()
            try:
                links = crawler.get_image_links(handle)
            finally:
                crawler.close()
            predictions = []
            with tempfile.TemporaryDirectory(prefix='tweet-crawl-') as directory:
                for index, link in enumerate(links[:5]):
                    if not is_allowed_media_url(link):
                        continue
                    path = Path(directory) / f'image-{index}'
                    with requests.get(link, stream=True, allow_redirects=False, timeout=(3, 10)) as response:
                        if response.status_code != 200:
                            raise ValueError('Media request failed')
                        total = 0
                        with path.open('wb') as output:
                            for chunk in response.iter_content(32 * 1024):
                                total += len(chunk)
                                if total > MAX_IMAGE_BYTES:
                                    raise ValueError('Media exceeds limit')
                                output.write(chunk)
                    validate_image(path)
                    predictions.append(classify(path, f'image-{index}'))
            return jsonify(predictions=predictions)
        except Exception:
            return jsonify(message='Legacy profile-image collection failed'), 502

    return application


flask_app = create_app()

if __name__ == '__main__':
    flask_app.run(host='127.0.0.1')
