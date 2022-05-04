# Proyecto-1-Ppio-Comms
Proyecto 1
Integrantes: Agustín González y Benjamín Castro
Profesores: César Azurdia y Jorge Sandoval
Auxiliares: Miguel Piña, Ignacio Bugueño, Raimundo Becerra y Pablo Palacios
Versión de Python: 3.10
Librerías usadas para modelo NLP: TensorFlow, Pandas, Scipy, Numpy, librerías nativas (string, json)
LEER, IMPORTANTE:
Para poder correr el código utilizando la función de NLP (variable use_NLP=True en server.py), es importante haber instalado las librerías antes mencionadas en
la terminal donde se vaya a ejecutar el programa. Además, es muy probable que si se activa esta opción, la librería TensorFlow levante advertencias debido a que
el computador en donde se corra el código no presenta GPU, sin embargo, esto no afecta el funcionamiento del modelo, pues este fue pre entrenado y está guardado 
correspondientemente en la carpeta 'saved_model\my_model'. 

Se debe iniciar el servidor antes que el cliente. El servidor se puede ejecutar en la consola del computador con el archivo 'server.py', de igual forma que para el
cliente con 'client.py' en otra terminal. Al ingresar en RUT un dígito impar, se iniciará sesión como usuario, mientras que si se ingresa con un dígito par entre 
1 y 10 (exceptuando el 4), se inicia sesión como ejecutivo. 
