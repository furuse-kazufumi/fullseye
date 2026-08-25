# Generate AI input photos for Fullseye op-category demos (Gemini 2.5 flash image).
import json, io, base64, urllib.request, os, sys, time

key = json.load(io.open(r"C:\dev\api-keys.json", encoding="utf-8"))["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash-image"
OUT = r"C:\dev\projects\imgevolve\studio_assets\sample_sources_ai"

PROMPTS = {
    "parts_tray": "Top-down photograph of assorted small metal machine parts (bolts, nuts, washers, springs) scattered in a light gray plastic tray, even diffuse industrial lighting, sharp focus, realistic, no text, no watermark",
    "gears": "Photograph of five metal gears of different sizes lying flat on a plain white background, top-down view, soft even lighting, crisp high-contrast edges, realistic, no text",
    "fruits": "Photograph of colorful fresh fruits (red apples, oranges, lemons, green grapes) arranged on a light wooden table, natural daylight, vivid colors, sharp focus, no text",
    "steel_balls": "Top-down macro photograph of polished steel ball bearings of three different sizes resting on a matte dark gray surface, even softbox lighting, crisp circular outlines, realistic, no text",
    "fabric_good": "Macro photograph of plain woven light-gray fabric, uniform regular weave pattern filling the whole frame, even lighting, no defects, no text",
    "pcb": "Close-up photograph of a green printed circuit board with many identical small black chips and silver capacitors in a regular grid, top-down view, even lighting, sharp focus, no readable text",
    "road": "Photograph from a car dashboard camera of a straight empty asphalt road with white dashed lane markings receding to the horizon, daytime, clear sky, realistic, no text",
    "statue": "Photograph of a white plaster bust statue on a neutral gray background, dramatic side lighting from the left, strong shadows, realistic, no text",
    "bottle_caps": "Top-down photograph of about thirty colorful plastic bottle caps (red, blue, yellow, green) scattered without overlapping on a white table, even lighting, saturated colors, no text",
    "dark_workshop": "Dimly lit photograph of a workshop wall with hanging hand tools, a single warm lamp on the right side causing strong uneven illumination and deep shadows, realistic, no text",
    "chess_floor": "Photograph of a large black-and-white checkerboard tile floor photographed at a low oblique angle so the squares recede with strong perspective, even lighting, no text",
}

def gen(prompt, out):
    url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (MODEL, key)
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=180))
    except Exception as e:
        print("ERR", os.path.basename(out), e); return False
    for part in r.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            data = base64.b64decode(part["inlineData"]["data"])
            io.open(out, "wb").write(data)
            print("saved", os.path.basename(out), len(data), "bytes"); return True
    print("no image:", os.path.basename(out), json.dumps(r)[:200]); return False

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ok = 0
    for name, prompt in PROMPTS.items():
        p = os.path.join(OUT, name + ".png")
        if os.path.exists(p):
            print("skip (exists)", name); ok += 1; continue
        if gen(prompt, p):
            ok += 1
        time.sleep(1.0)
    print("done %d/%d" % (ok, len(PROMPTS)))
