import json

from js import HTMLButtonElement, document
from pyodide.ffi import create_proxy

from csharpshims.runtime import generate_layer, load_packages, world_summary


async def handle_click(_event):
    button: HTMLButtonElement = document.getElementById("run-btn")
    output = document.getElementById("output")
    layer = int(document.getElementById("layer-select").value)
    button.disabled = True
    output.innerText = f"Generating layer {layer}..."
    try:
        package = load_packages()
        world = await generate_layer(package, layer)
        output.innerText = json.dumps(world_summary(world), indent=2)
    except Exception as error:
        output.innerText = f"Generation failed: {error}"
        raise
    finally:
        button.disabled = False


def setup():
    button: HTMLButtonElement = document.getElementById("run-btn")
    button.innerText = "Generate world"
    button.disabled = False
    button.addEventListener("click", create_proxy(handle_click))


setup()
