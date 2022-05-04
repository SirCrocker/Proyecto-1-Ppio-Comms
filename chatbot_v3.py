"""
**Proyecto 1**

# chatbot_v3.py
# Archivo donde se encuentra el código para entrenar al modelo de NLP
# Versión: Python 3.10
# Agustín González y Benjamín Castro

Curso: Principios de comunicaciones

Profesores:
*   Cesar Azurdia
*   Jorge Sandoval


Auxiliares:
*   Ignacio Bugueño
*   Miguel Piña
*   Pablo Palacios
*   Raimundo Becerra


Integrantes: 
*   Agustín González
*   Benjamín Castro
"""

# Chatbot con TensorFlow
# Se importan las librerías necesarias
import string
import pandas as pd
import json
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.layers import Input, Embedding, LSTM, Dense, \
GlobalMaxPooling1D, Flatten
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.preprocessing import LabelEncoder

# Se importa el dataset
with open("modelo.json") as content:
  data1 = json.load(content)

# Se enlistan todos los datos del dataset en una lista 
# para luego convertirlos a un dataframe de pandas (tabla)
tags = []
inputs = []
responses = {}

# Se llenan los diccionarios a través de un ciclo for
for intent in data1["intents"]:
  # Se pasan las respuestas del chatbot a la lista
  responses[intent['tag']]=intent['responses']
  for lines in intent['input']:
    # Se importan las palabras de input y las etiquetas de los mensajes
    inputs.append(lines)
    tags.append(intent['tag'])

# Se realiza la conversión a dataframe
data = pd.DataFrame({"inputs":inputs,"tags":tags})

# Entrenamiento

# Se remueven las puntuaciones y
# se dejan los mensajes de input en minúscula
data['inputs'] = data['inputs'].apply(lambda wrd:[ltrs.lower() for ltrs in wrd if ltrs not in string.punctuation])
data['inputs'] = data['inputs'].apply(lambda wrd: ''.join(wrd))

# Asignamos un token a cada dato (dígito identificador) para distinguir cada
# palabra
tokenizer = Tokenizer(num_words=2000)
tokenizer.fit_on_texts(data['inputs'])
train = tokenizer.texts_to_sequences(data['inputs'])

# Se realiza un padding para la data (crea una secuencia de bytes para que sea procesado
# por la red neuronal)
x_train = pad_sequences(train)

# Se etiquetan los output asignandoles un codigo
le = LabelEncoder()
y_train = le.fit_transform(data['tags'])

# Dimensiones del input
input_shape = x_train.shape[1]
# Se define el vocabulario o número de palabras distintas
# disponibles para el chatbot
vocabulary = len(tokenizer.word_index)
# Dimensiones del output
output_length = le.classes_.shape[0]

# Se crea el modelo
i = Input(shape=(input_shape,))
x = Embedding(vocabulary+1,10)(i) # Se crea la matriz que contiene el vocabulario
x = LSTM(10,return_sequences=True)(x)
x = Flatten()(x)
x = Dense(output_length,activation="softmax")(x) # Función de activación softmax
model  = Model(i,x)

# Se compila el modelo
model.compile(loss="sparse_categorical_crossentropy",optimizer='adam',metrics=['accuracy'])

# Se entrena el modelo
train = model.fit(x_train,y_train,epochs=500)

# Se guarda el modelo en una carpeta (saved_model/my_model)
model.save('saved_model/my_model')
