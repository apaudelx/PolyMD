import os
import json
from openai import OpenAI

# Config

YOUR_API_KEY = os.environ.get("PAPI_KEY")
input_dir = "ground_truth_627" # Hardcoded , need to change this
output_dir = "predicted_627"
os.makedirs(output_dir, exist_ok=True)

# Initialize Perplexity client
client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

# Loop through all .md files in the input directory
for filename in os.listdir(input_dir):
    if not filename.endswith(".md"):
        continue

    base_name = os.path.splitext(filename)[0]
    parsed_path = os.path.join(output_dir, f"{base_name}.json")
    raw_path = os.path.join(output_dir, f"{base_name}_raw.txt")

    # Skip if parsed JSON already exists
    if os.path.exists(parsed_path):
        print(f"Skipping already processed file: {filename}")
        continue

    # Load markdown content
    markdown_path = os.path.join(input_dir, filename)
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()


    stage_1 = [
    {
        "role": "system",
        "content": (
            "You are an assistant for extracting simulation data from polymer research articles."
            "Your task is to identify numerical results from molecular dynamics (MD) simulations and return them in JSON format."
        )
    },
    {
        "role": "user",
        "content": f"""
        Only include simulation data — do not extract experimental results such as DSC, DMA, tensile testing, or spectroscopy.  

        The JSON output must have these keys:  
        - polymer_system  
        - force_field  
        - Density (g/cm³)  
        - Glass Transition Temperature (K)  
        - Radius of Gyration (nm)  
        - Young's Modulus (GPa)  
        - Diffusion Coefficient (m²/s)  
        - Viscosity (Pa s)  

        If a value is missing, use "NA". Return only a JSON array, with one object per polymer–force-field pair.


        Markdown content:
        ```markdown
        {markdown_content}
        ```"""
        }
    ]

    stage_2 = [
    {
        "role": "system",
        "content": (
            "You are an assistant for extracting polymer simulation data from research articles.  "
            "Your task is to parse the text and return only numerical results from molecular dynamics (MD) simulations in JSON format."
        )
    },
    {
        "role": "user",
        "content": f"""
        Do not include experimental results such as DSC, DMA, tensile testing, spectroscopy, or microscopy.  
        Focus only on values reported from molecular simulations or force-field–based modeling.  

        The JSON output must have these exact keys:
        - "polymer_system"
        - "force_field"
        - "Density (g/cm³)"
        - "Glass Transition Temperature (K)"
        - "Radius of Gyration (nm)"
        - "Young's Modulus (GPa)"
        - "Diffusion Coefficient (m²/s)"
        - "Viscosity (Pa s)"

        Rules:
        - If a value is missing, use "NA".  
        - Convert all values into the correct units before output:  
        - kg/m³ → g/cm³  
        - °C → K  
        - Å → nm  
        - MPa → GPa  
        - cm²/s → m²/s  
        - mPa·s → Pa·s  
        - All values must be returned as quoted strings (e.g., "1.05", "NA").  
        - Return only a valid JSON array, with one object per polymer–force-field pair.
        - Do not include any commentary, explanations, or markdown formatting in your final output. The output must be ONLY the JSON.

        Markdown content:
        ```markdown
        {markdown_content}
        ```"""
        }
    ]


    stage_3 = [
    {
        "role": "system",
        "content": (
            "You are an expert assistant for extracting scientific data from research papers. "
            "Your task is to parse a Markdown document, identify ONLY numerical results from molecular modeling or simulations related to polymers, "
            "and format them into a structured JSON array. You must strictly ignore experimental data."
        )
    },
    {
        "role": "user",
        "content": f"""
        Below are examples of the desired output. Each object in the array represents a single numerical result.

        Example 1:
        [
        {{
            "polymer_system": "Polystyrene (PS)",
            "force_field": "OPLS-AA",
            "Density (g/cm³)": "1.05",
            "Glass Transition Temperature (K)": "100",
            "Radius of Gyration (nm)": "4.1",
            "Young's Modulus (GPa)": "3.3",
            "Diffusion Coefficient (m²/s)": "NA",
            "Viscosity (Pa s)": "NA"
        }}
        ]

        Example 2:
        [
        {{
            "polymer_system": "Polyvinyl Alcohol (PVA)",
            "force_field": "CHARMM36",
            "Density (g/cm³)": "1.19",
            "Glass Transition Temperature (K)": "85",
            "Radius of Gyration (nm)": "NA",
            "Young's Modulus (GPa)": "2.4",
            "Diffusion Coefficient (m²/s)": "3.1e-12",
            "Viscosity (Pa s)": "NA"
        }}
        ]

        Example 3:
        [
        {{
            "polymer_system": "Polyethylene (PE)",
            "force_field": "GROMOS",
            "Density (g/cm³)": "0.94",
            "Glass Transition Temperature (K)": "NA",
            "Radius of Gyration (nm)": "2.8",
            "Young's Modulus (GPa)": "NA",
            "Diffusion Coefficient (m²/s)": "4.7e-11",
            "Viscosity (Pa s)": "9.8e-4"
        }}
        ]

        Instructions:

        First, think step-by-step through the provided text. Identify every potential data point. For each one, reason about whether it is a simulation result or an experimental one.

        - To identify simulation data, look for keywords like: 'molecular dynamics (MD)', 'simulation', 'computational', 'modeling', 'force field', 'GROMACS', 'LAMMPS', 'OPLS-AA', 'COMPASS'.
        - Actively IGNORE data associated with experimental keywords like: 'synthesized', 'measured', 'characterized by', 'DSC', 'TGA', 'XRD', 'experimental setup'. If a value is from an experiment, do not include it.
        - If the polymer system is specified with a variable or varying repeat unit (e.g., DPP2PymT, m=1, 2, 3), use the most specific system designation from the text, such as "DPP2Py1T", "DPP2Py2T", etc.
        - If the paper refers to the system generically as DPP2PymT with an explicit value of m, output it as "DPP2PymT (m=1)".
        - Do not generalize to the base fragment only; always specify the level of detail present in the simulation.
        - Do NOT include multiple abbreviations or other extra information inside parentheses.
        - If no abbreviation exists, omit parentheses entirely.
        - Do NOT include any registered trademark symbols (®), trademark symbols (™), or other special symbols in polymer names.
        - Always adhere to the exact units specified for each property. For example, DEnsity must be in g/cm³, Glass Transition Temperature in K, Radius of Gyration in nm, Young's Modulus in GPa, Diffusion Coefficient in m²/s, and Viscosity in Pa s.
        - When units don't match the key's expected unit, convert the value to match the key's unit before extracting.

        Correct Example: Text says 16.01 × 10⁻⁵ °C⁻¹. Output should be: "property_value": 0.0001601, "units": "°C^-1".
        Incorrect Example: "property_value": "16.01", "units": "×10⁻⁵ °C⁻¹".

        JSON Formatting Rules:
        - Return ONLY a valid JSON array. Each object must represent exactly one property result.
        - Each object must have these keys: "polymer_system", "force_field", "Density (g/cm³)", "Glass Transition Temperature (K)", "Radius of Gyration (nm)", "Young's Modulus (GPa)", "Diffusion Coefficient (m²/s)", "Viscosity (Pa s)".
        - For keys with units, the numerical values must match the specified units exactly. In case of unit conversion, convert the value before including it.
        - If any key's value is not found in the text, strongly use the string "NA". Don't make assumptions.
        - Do not include any commentary, explanations, or markdown formatting in your final output. The output must be ONLY the JSON.

        Markdown content:
        ```markdown
        {markdown_content}
        ```"""
    }
]

    print(f"Processing {filename}...")

    try:
        # Call Perplexity API
        response = client.chat.completions.create(
            model="sonar",
            messages=stage_3,
            stream=False,
            temperature=0,  # Set to 0 for maximum consistency
            max_tokens=8000  # Ensure enough tokens for complete responses
        )

        content = response.choices[0].message.content.strip()

        # Strip <think> section
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()

        # Remove Markdown fences
        if content.startswith("```json"):
            content = content[7:].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        # Try parsing JSON
        parsed_json = json.loads(content)
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
        print(f"Parsed and saved to: {parsed_path}")

    except json.JSONDecodeError as e:
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Failed to parse JSON for {filename}, saved raw content instead to: {raw_path}")
        print("Error:", e)

    except Exception as e:
        print(f"Unexpected error for {filename}: {e}")
