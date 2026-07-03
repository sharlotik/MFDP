import os
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class Model:
    """
    Класс для вызова модели
    model_path (str): путь до модели
    """
    '''  
    def __init__(self, model_path):
        self.model_path = Path(model_path)
        self._load_model()
       
    def _load_model(self):
        if self.model_path.exists():
            self._is_loaded = True
        else:
            print(f'Ошибка загрузки модели')
            self._is_loaded = False
    '''

    def __init__(self):
        self.model_repo = os.getenv("HF_MODEL_REPO", "sharlotik/rubert_base_horeca_reviews_rating")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
       
    def _load_model(self):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_repo)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_repo)
            self.model.to(self.device)
            self.model.eval() 
            self._is_loaded = True
            print(f"Модель загружена на устройство: {self.device}")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self._is_loaded = False

    def predict(self, input_data: str) -> tuple[int, float]:

        if not self._is_loaded:
            raise RuntimeError("Попытка инференса на неинициализированной модели.")

        inputs = self.tokenizer(input_data, truncation=True, max_length=256, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits
            logits = logits.cpu()

        probabilities = torch.softmax(logits, dim=-1).squeeze().numpy()
        predicted_index = np.argmax(probabilities)
        confidence = float(probabilities[predicted_index])

        predicted_rating = int(predicted_index + 1)
        
        return predicted_rating, confidence