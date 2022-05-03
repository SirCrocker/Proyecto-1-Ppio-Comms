"""
**Proyecto 1**

# intencion.py
# Archivo donde se encuentra el código para hacer uso del modelo de NLP
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

import numpy as np
import string
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
from sklearn.preprocessing import LabelEncoder
from keras.models import load_model
import pandas as pd
import json

tags = []
inputs = []
responses = {}

#Se carga el archivo dataset
with open("modelo.json") as content:
  data1 = json.load(content)

#La funcion carga el modelo desde la carpeta 'saved_model/my_model'
def cargar_modelo():
  m=load_model('saved_model/my_model')
  return m

#Se deja el modelo guardado en la variable m
m=cargar_modelo()

#Se carga el dataset pasando su contenido a una lista
def cargar_dataset():
  global tags
  global inputs
  global responses
  global data1
  #Se llenan los diccionarios a traves de un ciclo for
  for intent in data1["intents"]:
    #Se pasan las respuestas del chatbot a la lista
    responses[intent['tag']]=intent['responses']
    for lines in intent['input']:
      #Se importan las palabras de input y las etiquetas de los mensajes
      inputs.append(lines)
      tags.append(intent['tag'])
      data = pd.DataFrame({"inputs":inputs,"tags":tags})
  return data

#Se define el estimador como variable
le=LabelEncoder()
#El dataframe creado anteriormente se deja como variable
data=cargar_dataset()
#Se crea el codificador de palabras
tokenizer = Tokenizer(num_words=2000)

#Se ajusta el estimador a las dimensiones del dataset
y_train = le.fit_transform(data['tags'])


#Se entrena el modelo con la funcion entrenamiento
#y se retornan los parametros de conjunto de entrenamiento, codificador, estimador
def entrenamiento():
  #Se toman las variables globales que se utilizaran en la funcion
  global le
  global data
  global m
  global tokenizer
  tokenizer.fit_on_texts(data['inputs'])
  train = tokenizer.texts_to_sequences(data['inputs'])
  #Se crea una secuencia de bytes para que sean procesados por la red neuronal
  x_train = pad_sequences(train)
  input_shape = x_train.shape[1]
  return tokenizer,train,x_train,input_shape,le

#La variable input_shape considera las dimensiones del mensaje entregado
#por el potencial usuario
input_shape = entrenamiento()[3]

#La funcion intencion toma un string que corresponde al mensaje entregado
#por el usuario y devuelve un string con la intencion que estima el modelo
def intencion(input):
  global m
  global tokenizer
  global input_shape
  texts_p = []
  #remueve la puntuacion y convierte todo a minuscula
  input = [letters.lower() for letters in input if letters not in string.punctuation]
  input = ''.join(input)
  texts_p.append(input)
  #se asigna un codigo al input y se realiza el padding
  input = tokenizer.texts_to_sequences(texts_p)
  input = np.array(input).reshape(-1)
  input = pad_sequences([input],input_shape)
  #se obtiene el output del modelo con la prediccion de este segun el input
  output = m.predict(input)
  #la prediccion con mayor probabilidad se rescata
  output = output.argmax()
  #el estimador obtiene la transformada inversa de dicha prediccion
  #para pasarla a string
  response_tag = le.inverse_transform([output])[0]
  return response_tag