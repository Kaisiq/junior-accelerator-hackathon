import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import litellm

# --- Configuration & Initialization ---

# Load environment variables from .env file in the current directory
load_dotenv()

# Set the litellm logger to show errors only, to keep the console clean
litellm.set_verbose = False

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='../frontend/static', static_url_path='')
CORS(app) # Enable Cross-Origin Resource Sharing

# --- AI Prompt Definition ---
SYSTEM_PROMPT = """
You are an architectural AI assistant. Your task is to translate a user's description of a building into a structured JSON format that a 3D renderer can understand.

RULES:
- You must only output a single JSON object. Do not include any other text, explanations, or markdown code fences.
- You can only use the following shapes: "box", "sphere", "cylinder", "hexagon", "cone", "torus", "octahedron", "dodecahedron", "icosahedron", "triangle".
- The JSON output MUST follow this structure: {"objects": [{"shape": "...", "position": {"x":0, "y":0, "z":0}, "size": {...}, "color": "#RRGGBB", "details": [{"shape": "...", "position": {"x":0, "y":0, "z":0}, "size": {...}, "operation": "subtract"}]}, ...]}
- For "box", the "size" property must be {"width": w, "height": h, "depth": d}.
- For "sphere", the "size" property must be {"radius": r}.
- For "cylinder", the "size" property must be {"radius": r, "height": h}.
- For "hexagon", the "size" property must be {"radius": r, "height": h}.
- For "cone", the "size" property must be {"radius": r, "height": h}.
- For "torus", the "size" property must be {"radius": r, "tube": t}.
- For "octahedron", the "size" property must be {"radius": r}.
- For "dodecahedron", the "size" property must be {"radius": r}.
- For "icosahedron", the "size" property must be {"radius": r}.
- For "triangle", the "size" property must be {"radius": r, "height": h}.
- The "details" property is an array of sub-objects that can be used to add or remove parts from the main shape. Use the "operation" property to specify "add", "subtract", or "intersect". For example, to create a window, you can subtract a small box from a larger box.
- All coordinate and size values must be numbers.
- The "color" must be a valid hex color string (e.g., "#FF0000").
- Keep the total number of objects between 5 and 20.
- The base of the building should be near the origin y=0.
- Be creative and futuristic in your interpretation of the user's prompt. Add details like windows, doors, and other features to make the buildings more interesting.
- The maximum output should not be more than 60000 tokens
- return json as a string characters
"""

# --- API Endpoints ---
@app.route('/')
def index():
    """Serves the main HTML file."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/generate', methods=['POST'])
def generate_building():
    """
    Receives a user's text description, sends it to the configured LLM provider,
    and returns the generated building structure as JSON.
    """
    try:
        data = request.get_json()
        user_description = data.get('prompt')

        if not user_description:
            return jsonify({"error": "No prompt provided"}), 400

        # --- Select LLM Provider based on environment variable ---
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "openai":
            model_name = "gpt-4o" # Or "gpt-3.5-turbo"
        elif provider == "gemini":
            model_name = "gemini/gemini-2.5-flash"
        else:
            return jsonify({"error": f"Unsupported provider: {provider}"}), 400

        # --- LLM API Call using LiteLLM ---
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_description}
        ]

        response = litellm.completion(
            model=model_name,
            messages=messages,
            temperature=0.8,
            max_tokens=64000,
            response_format={"type": "json_object"} # Use JSON mode if available
        )

        # The response object from litellm is consistent across providers
        llm_response_text = response.choices[0].message.content


        # Validate that the response is not empty
        if not llm_response_text:
            return jsonify({"error": "LLM provider returned an empty response."}), 500

        # Validate and return the JSON
        building_json = json.loads(llm_response_text)
        return jsonify(building_json)

    except Exception as e:
        # litellm raises exceptions from the underlying provider (e.g., openai.APIError)
        error_message = f"An error occurred with the LLM service: {str(e)}"
        print(error_message)
        return jsonify({"error": "Failed to generate building. Please check the server logs."}), 500

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
