import random
import math
import tqdm
import time
import click

from PIL import Image
from datetime import datetime
from vars import *


# MAIN FUNCTIONS
def color_choice(figure,preset):
	if figure in group_basic: return (f"{figure}.png", PRESETS[preset][1])
	elif figure in group_organic: return (f"{figure}.png", PRESETS[preset][2])
	elif figure in group_effects: return (f"{figure}.png", PRESETS[preset][3])

def resize_for_template(template_size) -> int:
	"""Base shape size for the selected resolution"""
	target_w, target_h = template_size
	is_mobile = target_h > target_w

	if is_mobile:
		scale_factor = (target_w * 0.60) / 1024
	else:
		scale_factor = (target_h * 0.45) / 1024

	return (int(1024 * scale_factor), int(1024 * scale_factor))


def _trim(img):
	"""Loads a shape, randomly scales and rotates it, and colors it with a single color"""
	bbox = img.getchannel("A").getbbox()
	return img.crop(bbox) if bbox else img


def prepare_shape(path, base_side, color, scale_range=(0.5, 0.9), rotate=True):
	"""Loads a shape, randomly scales and rotates it, and colors it a single color"""
	img = _trim(Image.open(path).convert("RGBA"))

	# random size; every shapes had own size
	side = int(base_side * random.uniform(*scale_range))
	ratio = side / max(img.size)
	img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)

	# random rotate
	if rotate:
		img = img.rotate(random.uniform(0, 360), resample=Image.BICUBIC, expand=True)
		img = _trim(img)

	# заливка цветом с сохранением альфа-канала
	colored = Image.new("RGBA", img.size, color)
	colored.putalpha(img.getchannel("A"))
	return colored


def _radius(shape) -> float:
	"""The radius of the circumscribed circle (slightly less than the full diagonal, to avoid an excessively large gap)"""
	w, h = shape.size
	
	return (max(w, h) + math.hypot(w, h)) / 4


def random_coord(canvas_size, shape, placed, gap=60, bleed=100, tries=400, candidates=30) -> tuple:
	"""
	Selects a position for the shape such that it does not overlap with any already placed shapes
	placed - a list of circles (cx, cy, r) representing the shapes already placed
	gap - the minimum gap between shapes, in pixels
	bleed - the extent to which a shape can extend beyond the edge of the canvas (as a fraction of its radius); 
		0 = strictly inside
	Among several suitable options, the "freest" one (the one furthest from neighbors) is chosen
	this ensures that the shapes spread out across the canvas rather than clustering together
	Returns the center (cx, cy), or None if no space is available
	"""
	w, h = canvas_size
	r = _radius(shape)

	x_lo, x_hi = r - bleed * r, w - r + bleed * r
	y_lo, y_hi = r - bleed * r, h - r + bleed * r
	if x_lo > x_hi: x_lo = x_hi = w / 2
	if y_lo > y_hi: y_lo = y_hi = h / 2

	best, best_score = None, -1
	found = 0
	for _ in range(tries):
		cx = random.uniform(x_lo, x_hi)
		cy = random.uniform(y_lo, y_hi)

		# distance to the nearest shape (minus the radii)
		clearance = min((math.hypot(cx - px, cy - py) - r - pr for px, py, pr in placed), default=1e9)
		if clearance < gap:
			continue 

		if clearance > best_score:
			best, best_score = (cx, cy), clearance
		found += 1
		if found >= candidates:
			break
	
	return best


def place_shapes(canvas_size, shapes, gap=60, bleed=0.2) -> list:
	"""
	Places the pieces without any overlaps
	If a shape doesn't fit, it gradually shrinks until there is enough space for it
	"""
	placed = []   # (cx, cy, r)
	result = []

	for shape in sorted(shapes, key=lambda s: s.width * s.height, reverse=True):
		for _ in range(12):
			center = random_coord(canvas_size, shape, placed, gap, bleed)
			if center:
				break
			shape = shape.resize((max(1, int(shape.width * 0.9)), max(1, int(shape.height * 0.9))), Image.LANCZOS)
		else:
			print("None space for a figure - pass")
			continue

		cx, cy = center
		placed.append((cx, cy, _radius(shape)))
		result.append((shape, (int(cx - shape.width / 2), int(cy - shape.height / 2))))
		
	return result

@click.command()
@click.option('--theme','-t', default="red", help=f"Themes: {str(PRESETS.keys())[11:-2]} \nAlso u can create own theme (read doc.)")
@click.option('--shapes','-s', default=["Gem", "Gem", "Pill"], help=f"Enter the shapes separated by commas: \n{(", ".join(list_figures))}")
@click.option('--template','-d',default="Phone_QHD", help="Choice the display template:\nPhone_QHD\nPhone_FHD\nDesktop_FHD\nDesktop_QHD")
def generate(theme,shapes,template, seed=None) -> None:
	_theme = None
	
	if seed is not None:
		random.seed(seed)
		
	canvas_size = template_display[template]
	base_side = resize_for_template(canvas_size)[0]
	background = Image.new("RGB", canvas_size, PRESETS[theme][0])

	figures = [color_choice(fig, theme) for fig in shapes.split(',')]
	_shapes = [prepare_shape(SHAPES_DIR + name, base_side, color) for name, color in figures]

	for shape, pos in tqdm.tqdm(place_shapes(canvas_size, _shapes)):
		time.sleep(0.1)
		background.paste(shape, pos, mask=shape)
	
	now = datetime.now()
	name = f"{theme}-{template}-{now.strftime("%d.%m.%Y-%H:%M")}.png"
	print(f"File {name} created")
	background.save(name)


if __name__ == "__main__":
	generate()