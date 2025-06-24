## COM300-FINAL
# Clasificación y Aplicación Automática de Iluminación en Blender

Este proyecto surge de la necesidad de simplificar y acelerar el proceso de iluminación en proyectos de diseño y animación digital. Partiendo de una imagen de referencia, Este clasifica automáticamente el tipo de iluminación usando un modelo de inteligencia artificial externo y aplica esa información para crear un ambiente lumínico coherente dentro de Blender. Así, el artista puede conseguir resultados realistas y creativos sin ajustar manualmente cada luz o color de fondo.

El repositorio integra tres componentes principales: un addon para Blender que facilita la carga de paletas de colores y la interacción con el usuario; un script externo en Python encargado de ejecutar la clasificación de la imagen usando modelos de IA; y un archivo JSON que contiene las paletas de colores y datos de luminosidad predefinidos para cada clase de iluminación reconocida. Estos componentes trabajan en conjunto para que la entrada de una imagen termine traducida en una configuración automática de luces y fondo dentro del entorno 3D.

El proyecto utiliza librerías clave como bpy para la integración con Blender, numpy para el manejo de datos numéricos y colores, subprocess para ejecutar el script externo, y json para la gestión de paletas y parámetros. La técnica principal consiste en la comunicación entre Blender y un modelo IA externo para realizar una predicción y luego aplicar esa información en la escena 3D de forma dinámica y visual.

Esta solución es especialmente relevante para carreras relacionadas con diseño y animación digital, ya que automatiza un paso crítico del workflow creativo: la iluminación. Reduce tiempos, ofrece resultados consistentes y permite a los creadores enfocarse en la composición y el estilo, apoyándose en la inteligencia artificial para mejorar su proceso de producción visual.
