import io
import sys
import unittest
from pathlib import Path
from PIL import Image
from app import create_app
from crawler import is_allowed_media_url


def png():
    output = io.BytesIO()
    Image.new('RGB', (4, 4), '#8dbda3').save(output, format='PNG')
    output.seek(0)
    return output


class UploadTests(unittest.TestCase):
    def test_status_does_not_import_model_or_browser(self):
        response = create_app().test_client().get('/status')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('torch', sys.modules)
        self.assertNotIn('selenium', sys.modules)

    def test_filename_cannot_control_write_path_and_temp_file_is_removed(self):
        paths = []
        def classify(path):
            paths.append(Path(path))
            self.assertTrue(Path(path).is_file())
            self.assertEqual(Path(path).name, 'upload-image')
            return {'label': 'synthetic-class', 'probability': 42.0}
        client = create_app(classifier=classify).test_client()
        response = client.post('/file', data={'image': (png(), '../../escape.png')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['predictions'], [{'filename':'escape.png','label':'synthetic-class','probability':42.0}])
        self.assertFalse(paths[0].exists())

    def test_each_request_classifies_only_its_own_file(self):
        paths = []
        def classify(path):
            paths.append(Path(path))
            return {'label':'synthetic-class','probability':42.0}
        client = create_app(classifier=classify).test_client()
        for name in ['first.png','second.png']:
            response = client.post('/file', data={'image':(png(),name)})
            self.assertEqual(len(response.json['predictions']),1)
        self.assertNotEqual(paths[0].parent,paths[1].parent)
        self.assertTrue(all(not path.exists() for path in paths))

    def test_missing_invalid_or_multiple_images_are_rejected(self):
        client = create_app().test_client()
        self.assertEqual(client.post('/file').status_code,400)
        self.assertEqual(client.post('/file',data={'image':(io.BytesIO(b'not an image'),'bad.png')}).status_code,400)
        self.assertEqual(client.post('/file',data={'image':[(png(),'one.png'),(png(),'two.png')]}).status_code,400)

    def test_oversized_body_is_rejected(self):
        client = create_app().test_client()
        response = client.post('/file',data={'image':(io.BytesIO(b'x'*(6*1024*1024)),'large.png')})
        self.assertEqual(response.status_code,413)

    def test_default_classifier_and_crawler_are_explicitly_unavailable(self):
        app = create_app()
        app.config.update(CLASSIFIER_ENABLED=False,LEGACY_CRAWLER_ENABLED=False)
        client=app.test_client()
        self.assertEqual(client.post('/file',data={'image':(png(),'sample.png')}).status_code,503)
        self.assertEqual(client.get('/keyword?keyword=synthetic').status_code,503)

    def test_media_allowlist_rejects_lookalike_hosts_and_redirect_sources(self):
        self.assertTrue(is_allowed_media_url('https://pbs.twimg.com/media/synthetic.jpg'))
        for value in ['http://pbs.twimg.com/media/a.jpg','https://pbs.twimg.com.evil.invalid/media/a.jpg','https://evil.invalid/https://pbs.twimg.com/media/a.jpg','file:///etc/passwd','https://pbs.twimg.com:123/media/a.jpg','https://pbs.twimg.com/not-media/a.jpg',None]:
            with self.subTest(value=value):self.assertFalse(is_allowed_media_url(value))
