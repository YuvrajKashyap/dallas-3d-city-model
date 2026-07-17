"""Build and render the canonical Blender scene.

Usage:
    blender --background --python scripts/render_scene.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
MESH_PATH = ROOT / "data" / "meshes" / "dallas_buildings_lod1.glb"
ORIGIN_PATH = ROOT / "data" / "processed" / "model_origin.json"
PATH_RESULT = ROOT / "data" / "processed" / "path_experiment.json"
VISIBILITY_RESULT = ROOT / "data" / "processed" / "visibility_experiment.json"
RENDER_DIR = ROOT / "screenshots"
BLEND_PATH = ROOT / "blender" / "dallas_urban_geometry_lab.blend"


def hex_color(value: str):
    value = value.lstrip("#")
    rgb = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    return (*rgb, 1.0)


def material(name: str, color: str, metallic: float = 0.0, roughness: float = 0.5, emission=0.0):
    item = bpy.data.materials.new(name)
    item.diffuse_color = hex_color(color)
    item.use_nodes = True
    shader = item.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = hex_color(color)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission:
        shader.inputs["Emission Color"].default_value = hex_color(color)
        shader.inputs["Emission Strength"].default_value = emission
    return item


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_curve(name: str, coordinates, curve_material, width: float):
    curve = bpy.data.curves.new(name, type="CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = width
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(coordinates) - 1)
    for point, coordinate in zip(spline.points, coordinates, strict=True):
        point.co = (*coordinate, 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(curve_material)
    return obj


def add_camera(name: str, location, target, lens=52.0, orthographic_scale=None):
    camera_data = bpy.data.cameras.new(name)
    camera = bpy.data.objects.new(name, camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = location
    camera.data.lens = lens
    camera.data.clip_end = 12_000
    if orthographic_scale:
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = orthographic_scale
    look_at(camera, target)
    return camera


def render(camera, filename: str, resolution=(2000, 1250)):
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(RENDER_DIR / filename)
    bpy.ops.render.render(write_still=True)


def main():
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    city_material = material("City · ice", "#b8d3e3", metallic=0.05, roughness=0.42)
    ground_material = material("Ground · midnight", "#07111f", roughness=0.82)
    path_material = material("A* path · coral", "#ff7d4d", roughness=0.26, emission=2.4)
    marker_material = material(
        "Observers · cyan",
        "#56d8e4",
        metallic=0.15,
        roughness=0.3,
        emission=1.5,
    )

    bpy.ops.import_scene.gltf(filepath=str(MESH_PATH))
    city_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    for obj in city_objects:
        obj.name = "Dallas LOD1 buildings"
        # glTF is Y-up; restore the geospatial mesh to Blender's Z-up convention.
        obj.parent = None
        obj.matrix_parent_inverse.identity()
        obj.location = (0, 0, 0)
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = (math.radians(-90), 0, 0)
        obj.data.materials.clear()
        obj.data.materials.append(city_material)

    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, -2))
    ground = bpy.context.object
    ground.name = "Dallas study area"
    ground.scale = (2200, 2200, 1)
    ground.data.materials.append(ground_material)

    origin = json.loads(ORIGIN_PATH.read_text(encoding="utf-8"))
    origin_x = origin["origin_easting_m"]
    origin_y = origin["origin_northing_m"]
    path_result = json.loads(PATH_RESULT.read_text(encoding="utf-8"))
    local_path = [
        (point[0] - origin_x, point[1] - origin_y, point[2] + 10)
        for point in path_result["coordinates"]
    ]
    add_curve("Fixed-altitude A* route", local_path, path_material, 9.0)

    visibility = json.loads(VISIBILITY_RESULT.read_text(encoding="utf-8"))
    for index, point in enumerate(visibility["selected_observers"], start=1):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2,
            radius=24,
            location=(point[0] - origin_x, point[1] - origin_y, visibility["observer_altitude_m"]),
        )
        observer = bpy.context.object
        observer.name = f"Selected observer {index}"
        observer.data.materials.append(marker_material)

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 2400))
    sun = bpy.context.object
    sun.name = "Dallas sun"
    sun.rotation_euler = (math.radians(32), math.radians(-24), math.radians(-38))
    sun.data.energy = 2.2
    sun.data.angle = math.radians(12)

    bpy.ops.object.light_add(type="AREA", location=(-1200, -700, 1800))
    key = bpy.context.object
    key.name = "Soft key"
    key.data.energy = 1700
    key.data.shape = "DISK"
    key.data.size = 1600
    look_at(key, (0, 0, 120))

    world = bpy.data.worlds.new("Dallas night")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = hex_color("#07111f")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"

    hero = add_camera("Hero camera", (3350, -3800, 2450), (0, 0, 105), lens=58)
    skyline = add_camera("Skyline camera", (2350, -2950, 820), (0, 0, 115), lens=62)
    top = add_camera("Top camera", (0, 0, 5200), (0, 0, 0), orthographic_scale=4300)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    render(hero, "portfolio-hero.png")
    render(skyline, "dallas-skyline.png", resolution=(1800, 1100))
    render(top, "dallas-topdown.png", resolution=(1600, 1600))
    print(f"Saved scene: {BLEND_PATH}")


if __name__ == "__main__":
    main()
