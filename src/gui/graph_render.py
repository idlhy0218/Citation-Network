"""
src/gui/graph_render.py
=======================
High-resolution 2D offscreen renderer for Citation Graph View.
Supports:
- Primary: skia-python (subpixel anti-aliasing, vector curves, hardware-accelerated 2D)
- Fallback: Pillow supersampling (2x static, 1.5x animating downscaling if skia is unavailable)
"""
import math
from PIL import Image, ImageDraw, ImageTk

try:
    import skia
    HAS_SKIA = True
except ImportError:
    HAS_SKIA = False


class GraphRenderer:
    """
    Renders graph geometry (edges, arrows, rings, nodes) off-screen onto a
    subpixel anti-aliased PhotoImage, ensuring high-definition rasterization.
    """
    def __init__(self):
        self.backend = "skia" if HAS_SKIA else "pillow"
        self._w = 0
        self._h = 0
        self._skia_buf = None
        self._skia_surface = None
        self._pil_img = None
        self._color_cache = {}

        if HAS_SKIA:
            import numpy as np
            self._np = np
            self._edge_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
                StrokeCap=skia.Paint.kRound_Cap,
                StrokeJoin=skia.Paint.kRound_Join,
            )
            self._arrow_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
            )
            self._ring_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
            )
            self._fill_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kFill_Style,
            )
            self._stroke_paint = skia.Paint(
                AntiAlias=True,
                Style=skia.Paint.kStroke_Style,
            )
            self._arrow_path = skia.Path()

    def hex_to_skia_color(self, hex_code: str, alpha: float = 1.0) -> int:
        cache_key = (hex_code, alpha)
        cached = self._color_cache.get(cache_key)
        if cached is not None:
            return cached

        h = hex_code.lstrip("#")
        if len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            a = max(0, min(255, int(alpha * 255)))
            col = skia.Color(r, g, b, a)
        elif len(h) == 8:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            a = int(h[6:8], 16)
            col = skia.Color(r, g, b, a)
        else:
            col = skia.ColorBLACK

        self._color_cache[cache_key] = col
        return col

    def render(
        self,
        w: int,
        h: int,
        scene: dict,
        is_animating: bool = False,
        existing_photo: ImageTk.PhotoImage = None
    ) -> ImageTk.PhotoImage:
        """
        Renders the scene dictionary to a Tkinter-compatible PhotoImage.
        If existing_photo matches dimensions, it is updated in-place via paste()
        to eliminate Tk memory churn and image handle swaps.
        """
        w = max(int(w), 10)
        h = max(int(h), 10)

        if self.backend == "skia":
            try:
                return self._render_skia(w, h, scene, existing_photo)
            except Exception:
                # If skia encounters an unexpected runtime fault, fallback to Pillow
                return self._render_pillow(w, h, scene, is_animating, existing_photo)
        else:
            return self._render_pillow(w, h, scene, is_animating, existing_photo)

    def _render_skia(
        self,
        w: int,
        h: int,
        scene: dict,
        existing_photo: ImageTk.PhotoImage = None
    ) -> ImageTk.PhotoImage:
        # Reallocate direct raster buffer only if dimensions changed
        if self._w != w or self._h != h or self._skia_surface is None:
            self._w = w
            self._h = h
            self._skia_buf = self._np.zeros((h, w, 4), dtype=self._np.uint8)
            info = skia.ImageInfo.Make(w, h, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
            self._skia_surface = skia.Surface.MakeRasterDirect(info, self._skia_buf)
            self._pil_img = Image.frombuffer('RGBA', (w, h), self._skia_buf, 'raw', 'RGBA', 0, 1)

        canvas = self._skia_surface.getCanvas()

        # 1. Background fill
        bg_hex = scene.get("bg_color", "#F7F7FA")
        canvas.clear(self.hex_to_skia_color(bg_hex, 1.0))

        # 2. Draw Edges
        edges = scene.get("edges", [])
        edge_paint = self._edge_paint
        arrow_paint = self._arrow_paint
        arrow_path = self._arrow_path

        for edge in edges:
            sx = float(edge["sx"])
            sy = float(edge["sy"])
            ex = float(edge["ex"])
            ey = float(edge["ey"])
            col = self.hex_to_skia_color(edge["color"])
            width = float(edge.get("width", 1.4))

            edge_paint.setColor(col)
            edge_paint.setStrokeWidth(width)
            canvas.drawLine(sx, sy, ex, ey, edge_paint)

            # Draw Arrowhead
            arrow_points = edge.get("arrow_points")
            if arrow_points and len(arrow_points) == 3:
                p1, p2, p3 = arrow_points
                arrow_path.reset()
                arrow_path.moveTo(float(p1[0]), float(p1[1]))
                arrow_path.lineTo(float(p2[0]), float(p2[1]))
                arrow_path.lineTo(float(p3[0]), float(p3[1]))
                arrow_path.close()

                arrow_paint.setColor(col)
                canvas.drawPath(arrow_path, arrow_paint)

        # 3. Draw Rings (Focus / Search Halo)
        rings = scene.get("rings", [])
        ring_paint = self._ring_paint
        for ring in rings:
            rx = float(ring["x"])
            ry = float(ring["y"])
            rad = float(ring["radius"])
            r_col = self.hex_to_skia_color(ring["color"])
            r_w = float(ring.get("width", 2.0))

            ring_paint.setColor(r_col)
            ring_paint.setStrokeWidth(r_w)
            canvas.drawCircle(rx, ry, rad, ring_paint)

        # 4. Draw Nodes
        nodes = scene.get("nodes", [])
        fill_paint = self._fill_paint
        stroke_paint = self._stroke_paint

        for node in nodes:
            nx = float(node["x"])
            ny = float(node["y"])
            rad = float(node["radius"])
            fill_col = self.hex_to_skia_color(node["fill"])

            # Fill
            fill_paint.setColor(fill_col)
            canvas.drawCircle(nx, ny, rad, fill_paint)

            # Stroke / Outline
            outline_col_hex = node.get("outline")
            outline_w = float(node.get("outline_width", 0.0))
            if outline_col_hex and outline_w > 0.0:
                outline_col = self.hex_to_skia_color(outline_col_hex)
                stroke_paint.setColor(outline_col)
                stroke_paint.setStrokeWidth(outline_w)
                canvas.drawCircle(nx, ny, rad, stroke_paint)

        # Flush direct GPU/CPU raster commands into buffer
        self._skia_surface.flushAndSubmit()

        # Update PhotoImage in-place if dimensions match, else create new
        if existing_photo is not None and existing_photo.width() == w and existing_photo.height() == h:
            existing_photo.paste(self._pil_img)
            return existing_photo
        else:
            return ImageTk.PhotoImage(self._pil_img)

    def _render_pillow(
        self,
        w: int,
        h: int,
        scene: dict,
        is_animating: bool = False,
        existing_photo: ImageTk.PhotoImage = None
    ) -> ImageTk.PhotoImage:
        scale = 1.5 if is_animating else 2.0
        sw = max(1, int(round(w * scale)))
        sh = max(1, int(round(h * scale)))

        bg_hex = scene.get("bg_color", "#F7F7FA")
        img = Image.new("RGBA", (sw, sh), bg_hex)
        draw = ImageDraw.Draw(img)

        # 1. Edges & Arrows
        for edge in scene.get("edges", []):
            sx = edge["sx"] * scale
            sy = edge["sy"] * scale
            ex = edge["ex"] * scale
            ey = edge["ey"] * scale
            col = edge["color"]
            w_scaled = max(1, int(round(edge.get("width", 1.4) * scale)))

            draw.line([(sx, sy), (ex, ey)], fill=col, width=w_scaled)

            arrow_points = edge.get("arrow_points")
            if arrow_points and len(arrow_points) == 3:
                pts = [(p[0] * scale, p[1] * scale) for p in arrow_points]
                draw.polygon(pts, fill=col)

        # 2. Rings
        for ring in scene.get("rings", []):
            rx = ring["x"] * scale
            ry = ring["y"] * scale
            rad = ring["radius"] * scale
            col = ring["color"]
            rw_scaled = max(1, int(round(ring.get("width", 2.0) * scale)))
            draw.ellipse([rx - rad, ry - rad, rx + rad, ry + rad], outline=col, width=rw_scaled)

        # 3. Nodes
        for node in scene.get("nodes", []):
            nx = node["x"] * scale
            ny = node["y"] * scale
            rad = node["radius"] * scale
            fill_col = node["fill"]
            outline_col = node.get("outline")
            outline_w = max(1, int(round(node.get("outline_width", 1.0) * scale))) if outline_col else 0

            bbox = [nx - rad, ny - rad, nx + rad, ny + rad]
            if outline_col and outline_w > 0:
                draw.ellipse(bbox, fill=fill_col, outline=outline_col, width=outline_w)
            else:
                draw.ellipse(bbox, fill=fill_col)

        # Downsample with bilinear interpolation for smooth anti-aliased output
        downsampled = img.resize((w, h), Image.Resampling.BILINEAR)
        if existing_photo is not None and existing_photo.width() == w and existing_photo.height() == h:
            existing_photo.paste(downsampled)
            return existing_photo
        return ImageTk.PhotoImage(downsampled)
