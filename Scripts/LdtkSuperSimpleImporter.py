import unreal
import math
import json
import pprint
import datetime
import os
import csv
import uuid
from enum import Enum
from typing import Any, List, Optional, Dict, TypeVar, Type, Callable, cast

# Função para carregar um arquivo CSV e convertê-lo em uma grade (grid) de números
def load_csv(file_path):
    grid = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            grid_row = []
            for cell in row:
                if cell.strip() == '':  # Se a célula estiver vazia, adiciona 0
                    grid_row.append(0)
                else:  # Caso contrário, converte o valor para inteiro
                    grid_row.append(int(cell))
            grid.append(grid_row)
    return grid

# Função para criar um componente de colisão (BoxComponent) em um ator
def create_collision(actor: unreal.PaperSpriteActor, x, y, tile_size):
    initial_children_count = actor.root_component.get_num_children_components()  # Conta os componentes filhos existentes

    # Obtém o subsistema para manipular subobjetos (componentes) no Unreal
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root_data_handle = subsystem.k2_gather_subobject_data_for_instance(actor)[0]
    
    # Cria um novo componente de colisão (BoxComponent)
    collision_component = unreal.BoxComponent()
    sub_handle, _ = subsystem.add_new_subobject(params=unreal.AddNewSubobjectParams(parent_handle=root_data_handle, new_class=collision_component.get_class()))
    subsystem.rename_subobject(handle=sub_handle, new_name=unreal.Text(f"LDTK_Collision_{uuid.uuid4()}"))

    # Obtém o novo componente adicionado
    new_component: unreal.BoxComponent = actor.root_component.get_child_component(initial_children_count)

    # Configura o tamanho, posição e rotação do componente de colisão
    new_component.set_box_extent(unreal.Vector(tile_size / 2, tile_size / 2, 64))
    new_component.set_relative_location_and_rotation(unreal.Vector((x + (tile_size / 2)), -32, -(y + (tile_size / 2))), unreal.Rotator(90, 0, 0),False, False)
    new_component.set_collision_profile_name("BlockAll")  # Define o perfil de colisão para "BlockAll"

# Função para criar colisões com base em uma grade (grid)
def spawn_collisions_from_grid(grid, actor: unreal.PaperSpriteActor, composite_width, composite_height):
    tile_size = 16  # Tamanho de cada tile
    for row_index, row in enumerate(grid):  # Itera sobre as linhas da grade
        for col_index, cell in enumerate(row):  # Itera sobre as células da linha
            x = (col_index * tile_size) - (composite_width / 2)  # Calcula a posição X
            y = row_index * tile_size - (composite_height / 2)  # Calcula a posição Y

            if cell == 1:  # Se a célula for 1, cria uma colisão
                create_collision(actor, x, y, tile_size)

# Função para encontrar todas as subpastas em um diretório
def find_all_subfolders(path):
    subfolders = []
    for root, dirs, files in os.walk(path):  # Percorre o diretório
        for dir in dirs:
            subfolders.append(os.path.join(root, dir))  # Adiciona o caminho da subpasta à lista
    return subfolders

# Tipo de dicionário para armazenar o conteúdo de um diretório
DirectoryContents = Dict[str, Dict[str, Any]]

# Função para obter o conteúdo de um diretório, filtrando arquivos específicos
def get_directory_contents(path: str) -> dict:
    directory_contents = {}
    for root, _, files in os.walk(path):  # Percorre o diretório
        root = os.path.normpath(root)
        # Filtra arquivos com extensões específicas
        filtered_files = [file for file in files if file.endswith(('_bg.png', '_composite.png', 'Bg_textures.png', 'Collisions.csv', 'Collisions.png', 'Collisions-int.png', 'data.json', 'Wall_shadows.png'))]
        if filtered_files:
            directory_contents[root] = {file: None for file in filtered_files}  # Armazena os arquivos filtrados
    return directory_contents

# Função principal para importar um mundo (nível) do LDtk para o Unreal Engine
def importWorld(folder_name: str):
    level_files_location = "LdtkFiles/simplified"  # Caminho relativo para os arquivos do LDtk
    base_directory = "/Game"  # Diretório base do Unreal Engine
    ldtk_files_directory = "LdtkFiles"  # Diretório dos arquivos LDtk
    ldtk_simplified_directory = "simplified"  # Subdiretório simplificado
    composite_filename = "_composite"  # Nome do arquivo de textura composta
    data_filename = "data.json"  # Nome do arquivo de dados JSON
    collisions_filename = "Collisions.csv"  # Nome do arquivo de colisões CSV

    if len(str(folder_name)) == 0:  # Verifica se o nome da pasta foi fornecido
        print("Unreal LDtk: No folder name provided. Exiting...")
        return
    else:
        folder_name = str(folder_name)

    # Monta o caminho completo para o diretório do nível
    base_path = os.path.join(base_directory, ldtk_files_directory, folder_name, ldtk_simplified_directory)
    content_directory = unreal.Paths.project_content_dir()
    level_directory = os.path.join(content_directory, ldtk_files_directory, folder_name, ldtk_simplified_directory).replace("\\", "/")
    directories = find_all_subfolders(level_directory)  # Encontra todas as subpastas

    if directories.__len__() > 0:  # Verifica se há subpastas
        print(f"Unreal LDtk: Found {len(directories)} directories in {level_directory}. Beginning import...")
    else:
        print(f"Unreal LDtk: No directories found in {level_directory}. \nThis might be because you are missing the LdtkFiles directory, or that the folder level name is wrong. Exiting...")
        return

    entity_index_counter = 0  # Contador para indexar entidades

    # Itera sobre cada subpasta (nível)
    for index, directory in enumerate(directories):
        _, directory_name = os.path.split(directory)
        full_path_composite = os.path.join(base_path, directory_name, composite_filename)
        full_path_data = os.path.join(level_directory, directory_name, data_filename).replace("\\", "/")
        full_path_collisions = os.path.join(level_directory, directory_name, collisions_filename).replace("\\", "/")
        
        # Verifica se os arquivos necessários existem
        composite_exists = unreal.EditorAssetLibrary.does_asset_exist(full_path_composite)
        data_exists = os.path.exists(full_path_data)
        collisions_exists = os.path.exists(full_path_collisions)

        ## Criando o Sprite ##
        if composite_exists:
            composite_texture = load_texture_asset(full_path_composite)  # Carrega a textura composta
            composite_sprite = create_sprite_from_texture(composite_texture, directory_name)  # Cria um sprite a partir da textura
        else:
            print(f"Unreal LDtk: Missing composite texture asset, skipping...")

        ## Lendo o arquivo JSON ##
        if data_exists:
            data_file = open(full_path_data)
            data = json.load(data_file)  # Carrega os dados do JSON
            data_file.close()
            composite_spawn_coords = (data['x'] + (data['width'] / 2), data['y'] + (data['height'] / 2), 0)  # Calcula as coordenadas de spawn
        else:
            print(f"Unreal LDtk: Missing data.json file, skipping...")

        # Se a textura composta e os dados existirem, spawna o ator e as entidades
        if (composite_exists and data_exists):
            spawned_composite_actor = spawn_sprite_in_world(composite_sprite, (composite_spawn_coords))
            ## Spawnando Entidades ##
            for _, entities in data['entities'].items():
                for index, entity in enumerate(entities):
                    spawn_entity_in_world(f"LDtk_{entity['id']}_{entity_index_counter}", data['x'] + entity['x'], data['y'] + entity['y'])
                    entity_index_counter += 1
        else:
            print(f"Unreal LDtk: Missing composite and/or data.json file, skipping entities...")

        ## Spawnando Colisões ##
        if composite_exists and collisions_exists:
            grid = load_csv(full_path_collisions)  # Carrega a grade de colisões do CSV
            spawn_collisions_from_grid(grid, spawned_composite_actor, data['width'], data['height'])  # Cria as colisões
        else: 
            print(f"Unreal LDtk: Missing Composite and/or Collisions.csv file, skipping collisions...")

# Função para verificar e deletar um sprite existente
def check_and_delete_existing_sprite(sprite_name):
    sprite_path = "/Game/LdtkFiles/" + sprite_name

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in all_actors:
        if actor.get_actor_label() == sprite_name:
            unreal.EditorLevelLibrary.destroy_actor(actor)
            print(f"Deleting existing composite sprite: {actor}")
            break

    if unreal.EditorAssetLibrary.does_asset_exist(sprite_path):
        unreal.EditorAssetLibrary.delete_asset(sprite_path)

# Função para verificar e deletar uma entidade existente
def check_and_delete_existing_entity(entity_name):
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in all_actors:
        if actor.get_actor_label() == entity_name:
            unreal.EditorLevelLibrary.destroy_actor(actor)
            print(f"Deleting existing entity: {actor}")
            break

# Função para carregar uma textura do Unreal Engine
def load_texture_asset(texture_path):
    texture = unreal.EditorAssetLibrary.load_asset(texture_path)
    return texture

# Função para criar um sprite a partir de uma textura
def create_sprite_from_texture(texture_asset: unreal.PaperSprite, world_name):
    try:
        sprite_path = "/Game/LdtkFiles"
        sprite_name = f"LDtk_{world_name}_{texture_asset.get_name()}_sprite"

        check_and_delete_existing_sprite(sprite_name=sprite_name)  # Verifica e deleta sprites existentes

        # Cria um novo sprite no Unreal Engine
        sprite_package = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name=sprite_name, package_path=sprite_path, asset_class=unreal.PaperSprite, factory=unreal.PaperSpriteFactory())
        sprite_package.set_editor_property("source_texture", texture_asset)  # Define a textura do sprite

        print("Sprite saved at: ", sprite_path)

        return sprite_package
    except:
        pass

# Função para spawnar uma entidade no mundo
def spawn_entity_in_world(name, x, y):
    location = unreal.Vector(x, 1, -y)  # Define a posição da entidade

    check_and_delete_existing_entity(name)  # Verifica e deleta entidades existentes

    # Spawna o ator no mundo
    actor: unreal.Actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.Actor().get_class(), location)

    if actor:
        actor.set_actor_label(name)  # Define o nome do ator
        print(f"Spawning entity: {actor.get_actor_label()}")

    return actor
         
# Função para spawnar um sprite no mundo
def spawn_sprite_in_world(sprite, location=(0, 0, 0), scale=(1, 1, 1)):
    spawn_location = unreal.Vector(location[0], location[2], -location[1])  # Define a posição de spawn
    scale_vector = unreal.Vector(scale[0], scale[1], scale[2])  # Define a escala
    actor_transform = unreal.Transform(spawn_location, unreal.Rotator(0, 0, 0), scale_vector)  # Define a transformação
    
    # Spawna o ator no mundo
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(sprite, spawn_location)
    if actor:
        sprite_component = actor.render_component
        if sprite_component:
            sprite_component.set_sprite(sprite)  # Define o sprite
            actor.set_actor_scale3d(scale_vector)  # Define a escala
            actor.set_actor_transform(actor_transform, False, True)  # Aplica a transformação
            print(f"Spawning composite sprite: {actor.get_actor_label()}")

            return actor
    return None

# Executa a função principal para importar o mundo
importWorld(folder_name)

# Exibe a data e hora atual
print(datetime.datetime.now())
