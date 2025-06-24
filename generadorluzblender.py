import bpy
import numpy as np
from PIL import Image
import os
import json
import subprocess
import sys 

# --- 1. CONFIGURACIÓN ---
CLASS_PALETTES_FILE = "C:/Users/59174/Desktop/lighting_class_palettes.json" 
PREDICTION_SCRIPT_PATH = "C:/Users/59174/Desktop/predict_lighting_class.py" 
PYTHON_EXECUTABLE_PATH = "C:/Users/59174/AppData/Local/Programs/Python/Python310/python.exe" 

WORLD_BACKGROUND_NODE_NAME = "Background" 
LIGHT_STRENGTH_MULTIPLIER = 2000 
WORLD_BACKGROUND_STRENGTH_MULTIPLIER = 1.0 


# --- 2. VARIABLES GLOBALES PARA RECURSOS CARGADOS ---
CLASS_PALETTES_AND_LUMINOSITY = None 
LAST_PREDICTED_CLASS_COLORS = [] # Almacenar la última paleta de colores para el selector
LAST_PREDICTED_COLOR_ENUM_ITEMS = [] # Opciones para el EnumProperty


# --- 3. FUNCIONES DE CARGA DE RECURSOS ---
def load_class_palettes(filepath):
    global CLASS_PALETTES_AND_LUMINOSITY
    if not os.path.exists(filepath):
        print(f"Error: Archivo de paletas de clases no encontrado en: {filepath}", file=sys.stderr)
        CLASS_PALETTES_AND_LUMINOSITY = None
        return False
    try:
        with open(filepath, 'r') as f:
            all_class_data_raw = json.load(f)
            loaded_data = {}
            for class_name, data in all_class_data_raw.items():
                loaded_data[class_name] = {
                    "colors": (np.array(data["colors"]) / 255.0).tolist(), 
                    "avg_luminosity": data["avg_luminosity"]
                }
            CLASS_PALETTES_AND_LUMINOSITY = loaded_data
        print(f"Paletas de colores de clase y luminosidades cargadas exitosamente ({len(CLASS_PALETTES_AND_LUMINOSITY)} clases).")
        return True
    except Exception as e:
        print(f"Error al cargar las paletas de colores de clase: {e}", file=sys.stderr)
        CLASS_PALETTES_AND_LUMINOSITY = None
        return False

# --- 4. FUNCIONES DE PREDICCIÓN Y APLICACIÓN DE ILUMINACIÓN ---

def classify_image_lighting_via_external_script(image_path):
    if not os.path.exists(PREDICTION_SCRIPT_PATH):
        print(f"Error: Script de predicción externo no encontrado: {PREDICTION_SCRIPT_PATH}", file=sys.stderr)
        return "EXTERNAL_SCRIPT_ERROR"
    if not os.path.exists(PYTHON_EXECUTABLE_PATH):
        print(f"Error: Ejecutable de Python externo no encontrado: {PYTHON_EXECUTABLE_PATH}", file=sys.stderr)
        return "EXTERNAL_SCRIPT_ERROR"

    try:
        command = [PYTHON_EXECUTABLE_PATH, PREDICTION_SCRIPT_PATH, image_path]
        
        process = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True 
        )
        
        predicted_class_name = process.stdout.strip()
        
        if process.stderr:
            print(f"Output STDERR from external script: {process.stderr}", file=sys.stderr)
            if "ERROR_LOADING_MODEL_OR_MAPPING" in process.stderr or "ERROR_PREDICTING" in process.stderr:
                return "EXTERNAL_SCRIPT_ERROR" 
                
        print(f"Resultado de la clasificación externa: '{predicted_class_name}'")
        return predicted_class_name

    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el script externo (CalledProcessError): {e}", file=sys.stderr)
        print(f"STDOUT: {e.stdout}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        return "EXTERNAL_SCRIPT_ERROR"
    except Exception as e:
        print(f"Error general al llamar al script externo: {e}", file=sys.stderr)
        return "EXTERNAL_SCRIPT_ERROR"


def set_world_background_color(color_rgb, strength):
    world = bpy.context.scene.world
    if not world:
        print("No se encontró el mundo en la escena.", file=sys.stderr)
        return
    if not world.use_nodes:
        world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    
    background_node = nodes.get(WORLD_BACKGROUND_NODE_NAME)
    if not background_node:
        background_node = nodes.new(type='ShaderNodeBackground')
        background_node.name = WORLD_BACKGROUND_NODE_NAME
        
    output_node = nodes.get("World Output") 
    if not output_node:
        output_node = nodes.new(type='ShaderNodeOutputWorld')
        output_node.name = "World Output"
        output_node.location = (400, 0)
    
    if not any(link.from_node == background_node and link.to_node == output_node and link.to_socket == output_node.inputs['Surface'] for link in links):
        links.new(background_node.outputs['Color'], output_node.inputs['Surface'])
        print("Conectando nodo de Background a World Output Surface.")
    
    color_rgb_alpha = color_rgb + [1.0] 
    background_node.inputs['Color'].default_value = color_rgb_alpha
    background_node.inputs['Strength'].default_value = strength
    print(f"Color de fondo del mundo establecido a: {color_rgb_alpha}, Fuerza: {strength}")

def setup_lights_from_colors(colors, base_strength): 
    lights_to_remove = [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT' and obj.name.startswith("LightMood_Light_")]
    for obj in lights_to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)
        
    light_types = ['POINT', 'AREA', 'SUN'] 
    num_lights_to_create = min(len(colors), len(light_types))

    for i in range(num_lights_to_create):
        color = colors[i]
        light_data = bpy.data.lights.new(name=f"LightMood_Light_{i}", type=light_types[i])
        
        light_data.energy = base_strength * ((color[0] + color[1] + color[2]) / 3.0) 
        if light_data.energy < 0.1: light_data.energy = 0.1 
        
        light_data.color = color 

        light_object = bpy.data.objects.new(name=f"LightMood_Light_Obj_{i}", object_data=light_data)
        bpy.context.scene.collection.objects.link(light_object)
        
        if light_types[i] == 'POINT':
            light_object.location = (i * 3 - 3, i * 3 - 3, 5) 
        elif light_types[i] == 'AREA':
            light_object.location = (i * 3 - 3, 0, 7)
            light_object.rotation_euler = (np.radians(-90), 0, 0) 
            light_data.size = 2.0
        elif light_types[i] == 'SUN':
            light_object.location = (0, 0, 10) 
            light_object.rotation_euler = (np.radians(45), np.radians(-30), 0) 

        print(f"Luz {light_types[i]} creada con color: {color}, Energía: {light_data.energy}")

# --- 5. CLASES DE OPERADORES DE BLENDER ---

class LightMoodLoadResources(bpy.types.Operator):
    """Operador para cargar las paletas de colores de clase."""
    bl_idname = "scene.light_mood_load_resources"
    bl_label = "Cargar Paletas de Colores de Iluminación"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if load_class_palettes(CLASS_PALETTES_FILE):
            self.report({'INFO'}, "Paletas de colores de LightMood cargadas exitosamente!")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Fallo al cargar las paletas de colores de LightMood.")
            return {'CANCELLED'}

class LightMoodSelectImage(bpy.types.Operator):
    """Selecciona la imagen de entrada para LightMood."""
    bl_idname = "scene.light_mood_select_image"
    bl_label = "Seleccionar Imagen de Entrada"

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
    )

    def execute(self, context):
        context.scene.lightmood_image_path = self.filepath
        self.report({'INFO'}, f"Imagen seleccionada: {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class LightMoodGeneratePrediction(bpy.types.Operator):
    """Clasifica la imagen de entrada y prepara los colores de la paleta."""
    bl_idname = "scene.light_mood_generate_prediction"
    bl_label = "Clasificar Imagen y Obtener Paleta" 
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global LAST_PREDICTED_CLASS_COLORS # Acceder a la variable global
        global LAST_PREDICTED_COLOR_ENUM_ITEMS # Acceder a la variable global para el EnumProperty

        image_path = context.scene.lightmood_image_path 

        print(f"DEBUG_BLENDER: image_path recibido: '{image_path}'")
        print(f"DEBUG_BLENDER: ¿Existe la ruta? {os.path.exists(image_path)}")

        if CLASS_PALETTES_AND_LUMINOSITY is None: 
            self.report({'ERROR'}, "Por favor, carga las paletas de colores primero usando 'Cargar Paletas de Colores de Iluminación'.")
            return {'CANCELLED'}

        if not image_path or not os.path.exists(image_path):
            self.report({'ERROR'}, "Por favor, selecciona una imagen válida usando el botón 'Seleccionar Imagen de Entrada'.")
            return {'CANCELLED'}

        print(f"DEBUG_BLENDER: Solicitando clasificación externa para: {image_path}")
        predicted_lighting_class = classify_image_lighting_via_external_script(image_path)
        print(f"DEBUG_BLENDER: Clase predicha recibida: '{predicted_lighting_class}'") 

        if predicted_lighting_class is None or predicted_lighting_class == "EXTERNAL_SCRIPT_ERROR":
            self.report({'ERROR'}, f"Fallo al obtener la clasificación del script externo. Revisa la consola de sistema (Window > Toggle System Console) para errores detallados.")
            return {'CANCELLED'}

        if predicted_lighting_class not in CLASS_PALETTES_AND_LUMINOSITY: 
            print(f"DEBUG_BLENDER: Clase predicha '{predicted_lighting_class}' no encontrada en las paletas de colores cargadas.", file=sys.stderr)
            self.report({'ERROR'}, f"Clase '{predicted_lighting_class}' predicha por el modelo, pero no se encontró la paleta de colores asociada. Revisa los nombres de las carpetas de tu dataset y el archivo class_mapping.json.")
            return {'CANCELLED'}

        class_data = CLASS_PALETTES_AND_LUMINOSITY[predicted_lighting_class] 
        colors_for_scene = class_data["colors"]
        avg_luminosity = class_data["avg_luminosity"]

        print(f"DEBUG_BLENDER: Paleta de colores obtenida para '{predicted_lighting_class}': {colors_for_scene}") 
        print(f"DEBUG_BLENDER: Luminosidad promedio obtenida para '{predicted_lighting_class}': {avg_luminosity}") 

        # Almacenar los datos en las propiedades de la escena y la variable global para el Paso 4
        context.scene.lightmood_last_predicted_class_name = predicted_lighting_class
        context.scene.lightmood_avg_luminosity = avg_luminosity
        
        LAST_PREDICTED_CLASS_COLORS.clear() # Limpiar la lista global de colores
        LAST_PREDICTED_CLASS_COLORS.extend(colors_for_scene) # Añadir los nuevos colores

        # Generar las opciones para el EnumProperty del selector de color
        LAST_PREDICTED_COLOR_ENUM_ITEMS.clear()
        for i, color_rgb in enumerate(colors_for_scene):
            # Formato: (identifier, name, description)
            # El identifier será el índice como string
            LAST_PREDICTED_COLOR_ENUM_ITEMS.append(
                (str(i), f"Color {i+1} ({int(color_rgb[0]*255)}, {int(color_rgb[1]*255)}, {int(color_rgb[2]*255)})", f"Color de la paleta: {i+1}")
            )
        
        # Seleccionar el primer color por defecto si la paleta no está vacía
        if LAST_PREDICTED_COLOR_ENUM_ITEMS:
            context.scene.lightmood_world_color_enum = LAST_PREDICTED_COLOR_ENUM_ITEMS[0][0]
        else:
            context.scene.lightmood_world_color_enum = "" # Vacío si no hay colores

        self.report({'INFO'}, f"Imagen clasificada como '{predicted_lighting_class}'. Paleta de colores lista para selección en Paso 4.")
        return {'FINISHED'}


class LightMoodApplyLighting(bpy.types.Operator):
    """Aplica la iluminación de la paleta seleccionada a la escena."""
    bl_idname = "scene.light_mood_apply_lighting"
    bl_label = "Aplicar Iluminación a la Escena"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Verificar si hay una paleta de colores clasificada
        if not LAST_PREDICTED_CLASS_COLORS:
            self.report({'ERROR'}, "Primero clasifica una imagen en el Paso 3 para obtener una paleta de colores.")
            return {'CANCELLED'}

        # Obtener el índice seleccionado del EnumProperty
        current_index_str = context.scene.lightmood_world_color_enum
        if not current_index_str: # Si no se ha seleccionado nada (ej. paleta vacía)
            self.report({'ERROR'}, "No hay un color seleccionado para el fondo del mundo.")
            return {'CANCELLED'}
        
        current_index = int(current_index_str) # Convertir el identificador de vuelta a int

        colors_for_scene = LAST_PREDICTED_CLASS_COLORS
        avg_luminosity = context.scene.lightmood_avg_luminosity
        predicted_lighting_class = context.scene.lightmood_last_predicted_class_name # Para el mensaje de reporte

        world_strength = avg_luminosity * WORLD_BACKGROUND_STRENGTH_MULTIPLIER
        if world_strength < 0.01: world_strength = 0.01 

        light_base_strength = avg_luminosity * LIGHT_STRENGTH_MULTIPLIER
        if light_base_strength < 10: light_base_strength = 10 
        
        # Usar el color del índice seleccionado para el World Shader
        world_bg_color = [0.8, 0.8, 0.8] # Gris claro por defecto
        if current_index < len(colors_for_scene):
            world_bg_color = colors_for_scene[current_index]
        else: 
            print(f"Advertencia: El índice de color seleccionado ({current_index}) está fuera de rango para la paleta actual de {len(colors_for_scene)} colores. Usando el primer color o gris por defecto.", file=sys.stderr)
            if colors_for_scene: world_bg_color = colors_for_scene[0] # Fallback al primer color

        set_world_background_color(world_bg_color, world_strength) 
        
        # Lógica para las luces: excluir el color usado para el fondo
        lights_colors_list = [c for i, c in enumerate(colors_for_scene) if i != current_index]
        if not lights_colors_list and colors_for_scene: 
            lights_colors_list = list(colors_for_scene) 

        setup_lights_from_colors(lights_colors_list, light_base_strength) 

        self.report({'INFO'}, f"Iluminación aplicada para '{predicted_lighting_class}', color de fondo: {LAST_PREDICTED_COLOR_ENUM_ITEMS[current_index][1]}!")
        return {'FINISHED'}


# --- 6. REGISTRO Y DEREGISTRO DE CLASES Y PROPIEDADES ---

# Propiedad para almacenar la ruta de la imagen seleccionada
bpy.types.Scene.lightmood_image_path = bpy.props.StringProperty(
    name="Ruta de Imagen Seleccionada",
    subtype='FILE_PATH', 
    default=""
)

# CALLBACK para la propiedad EnumProperty del selector de color
def get_world_color_enum_items(self, context):
    # Esta función se llama para poblar las opciones del desplegable.
    # Necesita devolver una lista de tuplas: (identifier, name, description)
    return LAST_PREDICTED_COLOR_ENUM_ITEMS


# Propiedad para seleccionar el color del World Shader usando un desplegable
bpy.types.Scene.lightmood_world_color_enum = bpy.props.EnumProperty(
    name="Color de Fondo (Paleta)",
    description="Selecciona un color de la paleta para el fondo del mundo",
    items=get_world_color_enum_items,
    update=lambda s,c: bpy.ops.scene.light_mood_apply_lighting() # Aplica la iluminación al cambiar la selección
)

# Propiedades para almacenar datos temporales de la clasificación
bpy.types.Scene.lightmood_last_predicted_class_name = bpy.props.StringProperty(default="")
bpy.types.Scene.lightmood_avg_luminosity = bpy.props.FloatProperty(default=0.5)


def register():
    bpy.utils.register_class(LightMoodLoadResources)
    bpy.utils.register_class(LightMoodSelectImage) 
    bpy.utils.register_class(LightMoodGeneratePrediction) 
    bpy.utils.register_class(LightMoodApplyLighting)     
    
    # Propiedades personalizadas
    bpy.types.Scene.lightmood_image_path
    bpy.types.Scene.lightmood_world_color_enum
    bpy.types.Scene.lightmood_last_predicted_class_name
    bpy.types.Scene.lightmood_avg_luminosity


    class LIGHTMOOD_CLASSIFIED_PT_panel(bpy.types.Panel):
        bl_label = "LightMood Clasificación Iluminación"
        bl_idname = "LIGHTMOOD_CLASSIFIED_PT_panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = 'Tool' 

        def draw(self, context):
            layout = self.layout
            
            # Paso 1: Cargar Paletas
            layout.label(text="Paso 1: Cargar Paletas de Colores")
            layout.operator("scene.light_mood_load_resources")
            layout.separator()

            # Paso 2: Seleccionar Imagen
            layout.label(text="Paso 2: Seleccionar Imagen de Entrada")
            layout.prop(context.scene, "lightmood_image_path")
            layout.operator("scene.light_mood_select_image", text="Examinar...")
            layout.separator()

            # Paso 3: Clasificar Imagen y Obtener Paleta
            layout.label(text="Paso 3: Clasificar Imagen")
            layout.operator("scene.light_mood_generate_prediction", text="Clasificar y Obtener Paleta")
            
            # Paso 4: Seleccionar Color de Fondo y Aplicar Iluminación
            # Solo mostrar si hay una paleta de colores disponible
            if LAST_PREDICTED_CLASS_COLORS: 
                layout.separator()
                box = layout.box() # Agrupar los controles del Paso 4 en una caja
                box.label(text="Paso 4: Seleccionar Color de Fondo y Aplicar")
                
                # Desplegable para seleccionar el color
                box.prop(context.scene, "lightmood_world_color_enum")
                
                # Mostrar el color actual seleccionado como un "swatch"
                current_selected_index_str = context.scene.lightmood_world_color_enum
                current_selected_color = [0.8, 0.8, 0.8] # Gris claro por defecto para visualización
                if current_selected_index_str: # Asegurarse de que haya algo seleccionado
                    current_selected_index = int(current_selected_index_str)
                    if current_selected_index < len(LAST_PREDICTED_CLASS_COLORS):
                        current_selected_color = LAST_PREDICTED_CLASS_COLORS[current_selected_index]
                
                row = box.row(align=True)
                row.label(text="Color Actual:")
                row.prop(current_selected_color, "color", text="", event="NONE") # Mostrar el color (no editable)

                # Botón explícito para aplicar la iluminación (por si el update no funciona al mover el slider o para aplicar manualmente)
                box.operator("scene.light_mood_apply_lighting", text="Aplicar Iluminación Ahora")
            else:
                layout.separator()
                layout.label(text="Clasifica una imagen en el Paso 3 para el Paso 4.")
    
    bpy.utils.register_class(LIGHTMOOD_CLASSIFIED_PT_panel)

def unregister():
    bpy.utils.unregister_class(LightMoodLoadResources)
    bpy.utils.unregister_class(LightMoodSelectImage) 
    bpy.utils.unregister_class(LightMoodGeneratePrediction) 
    bpy.utils.unregister_class(LightMoodApplyLighting)     
    bpy.utils.unregister_class(LIGHTMOOD_CLASSIFIED_PT_panel)
    
    # Eliminar todas las propiedades personalizadas al desregistrar
    if hasattr(bpy.types.Scene, "lightmood_image_path"):
        del bpy.types.Scene.lightmood_image_path
    if hasattr(bpy.types.Scene, "lightmood_world_color_enum"):
        del bpy.types.Scene.lightmood_world_color_enum
    if hasattr(bpy.types.Scene, "lightmood_last_predicted_class_name"):
        del bpy.types.Scene.lightmood_last_predicted_class_name
    if hasattr(bpy.types.Scene, "lightmood_avg_luminosity"):
        del bpy.types.Scene.lightmood_avg_luminosity


if __name__ == "__main__":
    register()
    print("LightMood Clasificación de Iluminación: Scripts registrados.")