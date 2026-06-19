"""
AirWrite Studio - SVG Exporter
========================================
Exports the complete canvas state to a scalable vector graphic (.svg) file.
"""

from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtCore import QSize, QRect, Qt
from PyQt6.QtGui import QPainter, QColor, QPen

from config import CANVAS_BACKGROUND_COLOR

def export_svg(engine, width: int, height: int, filepath: str) -> bool:
    """
    Render the canvas engine state to an SVG file.
    
    Args:
        engine: CanvasEngine instance
        width: Canvas width in pixels
        height: Canvas height in pixels
        filepath: Destination file path
    """
    generator = QSvgGenerator()
    generator.setFileName(filepath)
    generator.setSize(QSize(width, height))
    generator.setViewBox(QRect(0, 0, width, height))
    generator.setTitle("AirWrite Studio Canvas")
    generator.setDescription("Vector export of AirWrite Studio canvas")
    
    painter = QPainter()
    if not painter.begin(generator):
        print(f"Failed to begin painting to SVG generator at {filepath}")
        return False
        
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    # Fill background
    painter.fillRect(0, 0, width, height, QColor(CANVAS_BACKGROUND_COLOR))
    
    # Draw highlighter strokes first (behind)
    for obj in engine.objects:
        if obj.stroke.is_highlighter:
            color = QColor(obj.stroke.color)
            color.setAlpha(80)
            pen = QPen(color, obj.stroke.width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(obj.translated_path())

    # Then draw regular strokes
    for obj in engine.objects:
        if obj.stroke.is_highlighter or obj.stroke.is_laser:
            continue
        pen = QPen(obj.stroke.color, obj.stroke.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Use shape path if recognized
        if obj.stroke.shape_type != "none" and obj.stroke.shape_params:
            try:
                from canvas.shape_recognizer import ShapeRecognizer
                shape_path = ShapeRecognizer.shape_to_path(
                    obj.stroke.shape_type, obj.stroke.shape_params
                )
                if obj.offset.x() != 0 or obj.offset.y() != 0:
                    shape_path.translate(obj.offset)
                painter.drawPath(shape_path)
            except ImportError:
                painter.drawPath(obj.translated_path())
        else:
            painter.drawPath(obj.translated_path())

    # Render images
    for img in engine.images:
        img.render(painter)

    # Render text blocks
    for text_block in engine.text_blocks:
        text_block.render(painter)

    painter.end()
    return True
