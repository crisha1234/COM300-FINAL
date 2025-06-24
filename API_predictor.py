import tensorflow as tf
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import os
import json
import sys

# --- CONFIGURACIÓN (debe coincidir con la Fase 2) ---
MODEL_SAVE_PATH = "C:/Users/59174/Desktop/lighting_classifier_model.h5"
CLASS_MAPPING_FILE = "C:/Users/59174/Desktop/class_mapping.json"
IMG_HEIGHT, IMG_WIDTH = 128, 128

# Cargar el modelo y el mapeo de clases UNA VEZ al iniciar el script
CLASSIFIER_MODEL = None
CLASS_MAPPING = None

try:
    CLASSIFIER_MODEL = load_model(MODEL_SAVE_PATH)
    with open(CLASS_MAPPING_FILE, 'r') as f:
        CLASS_MAPPING = {int(k): v for k, v in json.load(f).items()}
    # print("Modelo y mapeo de clases cargados para predicción externa.")
except Exception as e:
    print(f"ERROR_LOADING_MODEL_OR_MAPPING: {e}", file=sys.stderr) # Enviar error a stderr
    sys.exit(1) # Salir si no se puede cargar lo esencial

def classify_image_lighting_external(image_path):
    """
    Clasifica el tipo de iluminación de una imagen usando el modelo cargado.
    """
    try:
        img = Image.open(image_path)
        img = img.resize((IMG_WIDTH, IMG_HEIGHT))
        img_array = np.array(img).astype(np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        predictions = CLASSIFIER_MODEL.predict(img_array, verbose=0) # verbose=0 para no imprimir progreso
        predicted_class_index = np.argmax(predictions[0])
        predicted_class_name = CLASS_MAPPING.get(predicted_class_index, "Desconocido")
        
        return predicted_class_name

    except Exception as e:
        print(f"ERROR_PREDICTING: {e}", file=sys.stderr)
        return "ERROR_PREDICTING_IMAGE" # Devolver un mensaje de error claro

if __name__ == "__main__":
    # Este script se llamará desde Blender con la ruta de la imagen como argumento
    if len(sys.argv) > 1:
        input_image_path = sys.argv[1]
        result_class = classify_image_lighting_external(input_image_path)
        print(result_class) # Imprime el resultado para que Blender lo lea
    else:
        print("ERROR: No se proporcionó la ruta de la imagen.", file=sys.stderr)
        sys.exit(1)