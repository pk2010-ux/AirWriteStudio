"""
AirWrite Studio - Workspace Serializer
========================================
Saves and loads the complete canvas state (strokes, text blocks, images)
to and from a JSON file format (.air).
"""

import json
import base64
from PyQt6.QtCore import QPointF, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QColor, QImage

from canvas.objects import Stroke, CanvasObject
from canvas.text_object import TextBlock
from canvas.image_object import ImageObject

def _qcolor_to_hex(color: QColor) -> str:
    return color.name(QColor.NameFormat.HexArgb)

def _hex_to_qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)

def _qpoint_to_dict(pt: QPointF) -> dict:
    return {"x": pt.x(), "y": pt.y()}

def _dict_to_qpoint(d: dict) -> QPointF:
    return QPointF(d.get("x", 0.0), d.get("y", 0.0))

def _image_to_base64(image: QImage) -> str:
    if image.isNull():
        return ""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return ba.toBase64().data().decode("utf-8")

def _base64_to_image(b64_str: str) -> QImage:
    if not b64_str:
        return QImage()
    ba = QByteArray.fromBase64(b64_str.encode("utf-8"))
    image = QImage()
    image.loadFromData(ba, "PNG")
    return image

def save_workspace(engine, filepath: str) -> bool:
    """Serialize the canvas engine state to a JSON file."""
    data = {
        "version": 1,
        "strokes": [],
        "text_blocks": [],
        "images": []
    }

    # Serialize strokes
    for obj in engine.objects:
        stroke = obj.stroke
        stroke_dict = {
            "points": [_qpoint_to_dict(p) for p in stroke.points],
            "color": _qcolor_to_hex(stroke.color),
            "width": stroke.width,
            "is_laser": stroke.is_laser,
            "is_highlighter": stroke.is_highlighter,
            "is_galaxy": stroke.is_galaxy,
            "point_widths": stroke.point_widths,
            "shape_type": stroke.shape_type,
            "shape_params": None, # Complex to serialize cleanly, skip for now to simplify
            "offset": _qpoint_to_dict(obj.offset),
            "scale": obj.scale
        }
        data["strokes"].append(stroke_dict)

    # Serialize text blocks
    for tb in engine.text_blocks:
        tb_dict = {
            "text": tb.text,
            "position": _qpoint_to_dict(tb.position),
            "font_size": tb.font_size,
            "color": _qcolor_to_hex(tb.color),
            "offset": _qpoint_to_dict(tb.offset),
            "scale": tb.scale
        }
        data["text_blocks"].append(tb_dict)

    # Serialize images
    for img in engine.images:
        img_dict = {
            "image_data": _image_to_base64(img.image),
            "position": _qpoint_to_dict(img.position),
            "offset": _qpoint_to_dict(img.offset),
            "scale": img.scale
        }
        data["images"].append(img_dict)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"Failed to save workspace: {e}")
        return False

def load_workspace(engine, filepath: str) -> bool:
    """Deserialize the canvas engine state from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if data.get("version") != 1:
            print("Unsupported workspace version")
            return False
            
        engine.clear_all()
        # Clear out the undo stack because it will be invalid
        engine.undo_stack.clear()
        engine.redo_stack.clear()
        
        # Load strokes
        for stroke_dict in data.get("strokes", []):
            points = [_dict_to_qpoint(p) for p in stroke_dict.get("points", [])]
            color = _hex_to_qcolor(stroke_dict.get("color", "#FFFFFF"))
            width = stroke_dict.get("width", 3.0)
            
            stroke = Stroke(points=points, color=color, width=width)
            stroke.is_laser = stroke_dict.get("is_laser", False)
            stroke.is_highlighter = stroke_dict.get("is_highlighter", False)
            stroke.is_galaxy = stroke_dict.get("is_galaxy", False)
            stroke.point_widths = stroke_dict.get("point_widths")
            stroke.shape_type = stroke_dict.get("shape_type", "none")
            
            obj = CanvasObject(stroke)
            obj.offset = _dict_to_qpoint(stroke_dict.get("offset", {"x":0, "y":0}))
            obj.scale = stroke_dict.get("scale", 1.0)
            engine.objects.append(obj)
            
        # Load text blocks
        for tb_dict in data.get("text_blocks", []):
            text = tb_dict.get("text", "")
            pos = _dict_to_qpoint(tb_dict.get("position", {"x":0, "y":0}))
            font_size = tb_dict.get("font_size", 24.0)
            color = _hex_to_qcolor(tb_dict.get("color", "#FFFFFF"))
            
            tb = TextBlock(text=text, position=pos, font_size=font_size, color=color)
            tb.offset = _dict_to_qpoint(tb_dict.get("offset", {"x":0, "y":0}))
            tb.scale = tb_dict.get("scale", 1.0)
            engine.text_blocks.append(tb)
            
        # Load images
        for img_dict in data.get("images", []):
            img_data = img_dict.get("image_data", "")
            pos = _dict_to_qpoint(img_dict.get("position", {"x":0, "y":0}))
            
            qimg = _base64_to_image(img_data)
            if not qimg.isNull():
                img = ImageObject(image=qimg, position=pos)
                img.offset = _dict_to_qpoint(img_dict.get("offset", {"x":0, "y":0}))
                img.scale = img_dict.get("scale", 1.0)
                engine.images.append(img)
                
        engine.objects_changed.emit()
        return True
    except Exception as e:
        print(f"Failed to load workspace: {e}")
        return False
