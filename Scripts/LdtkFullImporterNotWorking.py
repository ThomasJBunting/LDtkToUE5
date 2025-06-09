import unreal
import json
import os

# === CONFIGURATION SECTION ===

ENTITY_BLUEPRINTS = {
    "Player": "/Game/Blueprints/BP_Player",
    "Enemy": "/Game/Blueprints/BP_Enemy",
    # Add more mappings as needed
}

TILESET_TEXTURE_PATH = "/Game/Sprites/Tileset"  # Texture used for tileset
SPRITE_FOLDER_PATH = "/Game/Sprites/Generated"  # Folder to save sprites
COLLISION_Z_HEIGHT = 64

def import_ldtk_project(ldtk_filename: str):
    base_dir = unreal.Paths.project_content_dir()
    full_path = os.path.join(base_dir, "LDtkFiles", ldtk_filename)

    if not os.path.exists(full_path):
        unreal.log_error(f"[LDtkImporter] Could not find LDtk file: {full_path}")
        return

    with open(full_path, 'r') as f:
        data = json.load(f)

    for level in data["levels"]:
        process_level(level, data)

def process_level(level_data: dict, project_data: dict):
    level_name = level_data["identifier"]
    unreal.log(f"[LDtkImporter] Processing level: {level_name}")

    for layer in level_data["layerInstances"]:
        layer_type = layer["__type"]

        if layer_type == "Entities":
            process_entity_layer(layer)
        elif layer_type == "IntGrid":
            process_intgrid_layer(layer)
        elif layer_type in ["Tiles", "AutoLayer"]:
            process_tile_layer(layer, project_data)
        else:
            unreal.log_warning(f"[LDtkImporter] Unknown layer type: {layer_type}")

def process_entity_layer(layer: dict):
    for entity in layer["entityInstances"]:
        name = entity["__identifier"]
        x = entity["px"][0]
        y = entity["px"][1]
        blueprint_path = ENTITY_BLUEPRINTS.get(name)

        if blueprint_path:
            blueprint = unreal.load_object(None, blueprint_path)
            location = unreal.Vector(x, 0, -y)
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(blueprint.generated_class, location)
            actor.set_actor_label(name)
            unreal.log(f"[Entity] Spawned '{name}' at ({x}, {y})")
        else:
            unreal.log_warning(f"[Entity] No blueprint mapped for entity: {name}")

def process_intgrid_layer(layer: dict):
    width = layer["__cWid"]
    height = layer["__cHei"]
    grid = layer["intGridCsv"]
    tile_size = layer["__gridSize"]

    for index, value in enumerate(grid):
        if value == 0:
            continue
        col = index % width
        row = index // width
        x = col * tile_size
        y = row * tile_size
        spawn_collision_box(x, y, tile_size)

def spawn_collision_box(x, y, tile_size):
    box_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.Actor, unreal.Vector(x, 0, -y))
    box_component = unreal.BoxComponent()
    box_component.set_box_extent(unreal.Vector(tile_size / 2, tile_size / 2, COLLISION_Z_HEIGHT))
    box_component.set_relative_location(unreal.Vector(0, 0, 0))
    box_component.set_collision_profile_name("BlockAll")
    box_actor.add_instance_component(box_component)
    unreal.log(f"[Collision] Box at ({x}, {y})")

def process_tile_layer(layer: dict, project_data: dict):
    tile_size = layer["__gridSize"]
    tiles = layer["gridTiles"]

    for tile in tiles:
        src_x = tile["src"][0]
        src_y = tile["src"][1]
        pos_x = tile["px"][0]
        pos_y = tile["px"][1]
        tile_id = tile["t"]
        sprite = get_or_create_sprite(tile_id, src_x, src_y, tile_size)
        spawn_tile_sprite(pos_x, pos_y, sprite)

def get_or_create_sprite(tile_id, src_x, src_y, tile_size):
    sprite_name = f"LDtk_Tile_{tile_id}"
    sprite_path = f"{SPRITE_FOLDER_PATH}/{sprite_name}"

    if unreal.EditorAssetLibrary.does_asset_exist(sprite_path):
        return unreal.EditorAssetLibrary.load_asset(sprite_path)

    texture = unreal.EditorAssetLibrary.load_asset(TILESET_TEXTURE_PATH)
    factory = unreal.PaperSpriteFactory()
    factory.set_editor_property("initial_texture", texture)
    sprite_asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(sprite_name, SPRITE_FOLDER_PATH, unreal.PaperSprite, factory)
    sprite_asset.set_editor_property("source_uv", unreal.IntPoint(src_x, src_y))
    sprite_asset.set_editor_property("source_dimension", unreal.IntPoint(tile_size, tile_size))
    return sprite_asset

def spawn_tile_sprite(x, y, sprite):
    location = unreal.Vector(x, 0, -y)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PaperSpriteActor.static_class(), location)
    actor.get_editor_property("render_component").set_sprite(sprite)
    actor.set_actor_label(f"Tile_{sprite.get_name()}")
    unreal.log(f"[Tile] Placed tile at ({x}, {y})")

# Optional: Add UI button later using Editor Utility Widget or Blutility
