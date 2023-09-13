import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def runtime():
    if os.getenv('ENABLE_PRETRAINED_MODEL') != 'true':
        raise RuntimeError('Explicit model opt-in required')
    import torch
    from torchvision.models import vgg19, VGG19_Weights
    weights = VGG19_Weights.IMAGENET1K_V1
    model = vgg19(weights=weights).eval()
    return torch, model, weights.transforms(), weights.meta['categories']


class Classifier:
    @classmethod
    def classify_file(cls, path):
        from PIL import Image
        torch, model, transform, categories = runtime()
        with Image.open(path) as image:
            tensor = transform(image.convert('RGB')).unsqueeze(0)
        with torch.inference_mode():
            probabilities = model(tensor).softmax(dim=-1)[0]
        index = int(probabilities.argmax().item())
        return {'filename': Path(path).name, 'label': categories[index], 'probability': float(probabilities[index].item()) * 100}
