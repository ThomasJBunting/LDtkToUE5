import unreal
import json
import os

# Main import entry point
def import_ldtk_project(ldtk_filename: str):
    # Get path to Content directory
    base_dir = unreal.Paths.project_content_dir()
    ldtk_path = os.path.join(base_dir, "LDtkFiles", ldtk_filename)

    if not os.path.exists(ldtk_path):
        unreal.log_warning(f"[LDtkImporter] Could not find file: {ldtk_path}")
        return

    with open(ldtk_path, 'r') as f:
        data = json.load(f)

    # Optional: store defs (tilesets, enums, entities)
    defs = data.get("defs", {})

    for level in data["levels"]:
        process_level(level)

# Process a single level
def process_level(level_data: dict):
    level_name = level_data["identifier"]
    unreal.log(f"[LDtkImporter] Importing level: {level_name}")

    for layer in level_data["layerInstances"]:
        layer_type = layer["__type"]
        identifier = layer["__identifier"]

        if layer_type == "Entities":
            process_entity_layer(layer)
        elif layer_type == "IntGrid":
            process_intgrid_layer(layer)
        elif layer_type == "Tiles" or layer_type == "AutoLayer":
            process_tile_layer(layer)
        else:
            unreal.log_warning(f"[LDtkImporter] Unknown layer type: {layer_type}")

# Handle entity instances
def process_entity_layer(layer: dict):
    for entity in layer["entityInstances"]:
        name = entity["__identifier"]
        x = entity["px"][0]
        y = entity["px"][1]
        fields = {
            f["__identifier"]: f["__value"]
            for f in entity["fieldInstances"]
        }

        # TODO: Replace this with logic to spawn correct Blueprint or Actor
        unreal.log(f"[Entity] {name} at ({x},{y}) with fields {fields}")

# Handle collision or other int-based data
def process_intgrid_layer(layer: dict):
    width = layer["__cWid"]
    height = layer["__cHei"]
    grid = layer["intGridCsv"]
    tile_size = layer["__gridSize"]

    for index, value in enumerate(grid):
        if value == 0:
            continue  # Skip empty

        col = index % width
        row = index // width
        x = col * tile_size
        y = row * tile_size

        # TODO: Replace with logic to spawn a collision box or visual
        unreal.log(f"[IntGrid] Value {value} at ({x},{y})")

# Handle visual tile layers
def process_tile_layer(layer: dict):
    grid_size = layer["__gridSize"]
    tiles = layer["gridTiles"]  # Tile instances (auto or manual)

    for tile in tiles:
        src_x = tile["src"][0]
        src_y = tile["src"][1]
        pos_x = tile["px"][0]
        pos_y = tile["px"][1"]
        tile_id = tile["t"]

        # TODO: Replace with logic to render tile via Paper2D, sprite, or other
        unreal.log(f"[Tile] Tile ID {tile_id} at ({pos_x},{pos_y}) source ({src_x},{src_y})")

# Run it by calling this from the Unreal Python console:
# import_ldtk_project("YourMap.ldtk")
