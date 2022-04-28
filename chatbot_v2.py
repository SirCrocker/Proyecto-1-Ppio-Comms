# -*- coding: utf-8 -*-
"""chatbot_v2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Fpu3NJ9DgxvWG4GJY49L2JVPw_jai2GO

**Proyecto 1**

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

#Chatbot con TensorFlow
#Se importan las librerias necesarias
import string
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import json
import nltk
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.layers import Input, Embedding, LSTM, Dense, \
GlobalMaxPooling1D, Flatten
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import random

#Se carga la data de entrenamiento
with open("modelo.json") as data:
    data1 = json.load(data)

#Se llevan los datos a una lista
tags = []
inputs = []
responses={}
for intent in data1['intents']:
  responses[intent['tag']]=intent['responses']
  for lines in intent['input']:
    inputs.append(lines)
    tags.append(intent['tag'])

#Se convierte a dataframe
data2 = pd.DataFrame({"inputs":inputs,
                     "tags":tags})
#Se imprimen el dataframe para verificar que la importacion haya sido correcta
print(data2)

#Se remueven las puntuaciones
data2['inputs'] = data2['inputs'].apply(lambda wrd:[ltrs.lower() for ltrs in wrd if ltrs not in string.punctuation])
data2['inputs'] = data2['inputs'].apply(lambda wrd: ''.join(wrd))

#Se crean tokens para el dataframe "data2"
tokenizer = Tokenizer(num_words=2000)
tokenizer.fit_on_texts(data2['inputs'])
train = tokenizer.texts_to_sequences(data2['inputs'])

#Se aplica "padding" (hacer que la data tenga el mismo largo para
#enviarlo a la red neuronal)
x_train = pad_sequences(train)

#Se codifican los outputs
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
y_train = le.fit_transform(data2['tags'])

#largo del input
input_shape = x_train.shape[1]
print("input length: ",input_shape)
#Se define el vocabulario (palabras unicas)
vocabulary = len(tokenizer.word_index)
print("number of unique words : ",vocabulary)
#largo del output
output_length = le.classes_.shape[0]
print("output length: ",output_length)

#Se crea el modelo
i = Input(shape=(input_shape,))
x = Embedding(vocabulary+1,10)(i)
x = LSTM(10,return_sequences=True)(x)
x = Flatten()(x)
x = Dense(output_length,activation="softmax")(x)
model  = Model(i,x)

#Se compila el modelo
model.compile(loss="sparse_categorical_crossentropy",optimizer='adam',metrics=['accuracy'])

#Se pasa al entrenamiento del modelo
train = model.fit(x_train,y_train,epochs=300)

#Se pone a prueba el modelo con la funcion intencion

#funcion que toma un string como input y devuelve un string entregando el intent
#o intencion del mensaje
def intencion(input):
  texts_p = []
  #remueve la puntuacion y convierte todo a minuscula
  input = [letters.lower() for letters in input if letters not in string.punctuation]
  input = ''.join(input)
  texts_p.append(input)
  #se realiza el token del input y el padding
  input = tokenizer.texts_to_sequences(texts_p)
  input = np.array(input).reshape(-1)
  input = pad_sequences([input],input_shape)
  #se obtiene el output del modelo
  output = model.predict(input)
  output = output.argmax()
  response_tag = le.inverse_transform([output])[0]
  return response_tag