import os
import json
import csv
import time
from pathlib import Path
from openai import OpenAI

# Configuration
OPENAI_API_KEY = os.environ.get("OpenAI_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# Standard units for properties
STANDARD_UNITS = {
    "density": "g/cm³",
    "glass_transition_temp": "K",
    "radius_gyration": "nm",
    "youngs_modulus": "GPa",
    "diffusion_coefficient": "m²/s",
    "viscosity": "Pa s"
}

def load_json_data(json_path):
    """Load the md_file_data.json file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_md_file(md_file_name, base_dir):
    """Load the corresponding MD file from comparison_set_hpc."""
    # Extract folder number from md_file name (e.g., "1.md" -> "1")
    folder_number = md_file_name.replace(".md", "")
    md_path = base_dir / folder_number / md_file_name
    
    if not md_path.exists():
        raise FileNotFoundError(f"MD file not found: {md_path}")
    
    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_verification_prompt(md_content, entries):
    """Create a balanced verification prompt for all entries at once."""
    entries_json = json.dumps(entries, indent=2)
    
    prompt = f"""You are a scientific reviewer verifying extracted data from a polymer research article. Your job is to identify actual errors in the extracted information, not to find problems where none exist.

Here is the full text of the research article:

{md_content}The following information has been extracted from this article and claims to represent simulation data (as a JSON array):

{entries_json}

**Standard Units (extracted values are ALREADY in these units):**
- density: g/cm³
- glass_transition_temp: K
- radius_gyration: nm
- youngs_modulus: GPa
- diffusion_coefficient: m²/s
- viscosity: Pa s

**CRITICAL: Understanding Extracted Values**
The extracted values in the JSON array are ALREADY converted to the standard units listed above. The "Value" field contains ONLY the numerical value (e.g., "1.048", "0.73", "5.37") - it does NOT include unit labels because the units are standardized. This is CORRECT and EXPECTED behavior.

**CRITICAL: Unit Conversion Rules**
When checking if values match, convert the article's value to the standard unit and compare:
- If the article reports density in kg/m³, convert to g/cm³ (divide by 1000). Example: 1048 kg/m³ = 1.048 g/cm³, 730 kg/m³ = 0.73 g/cm³
- If the article reports temperature in °C, convert to K (add 273.15). Example: 25°C = 298.15 K
- If the article reports radius in Å, convert to nm (divide by 10). Example: 15.5 Å = 1.55 nm
- If the article reports modulus in MPa, convert to GPa (divide by 1000). Example: 5370 MPa = 5.37 GPa
- If the article reports diffusion in cm²/s, convert to m²/s (divide by 10000). Example: 1.0×10⁻⁷ cm²/s = 1.0×10⁻¹¹ m²/s
- If the article reports viscosity in mPa·s, convert to Pa·s (divide by 1000). Example: 500 mPa·s = 0.5 Pa·s

**What to Check:**
For each entry, verify:
1. Whether the property was ACTUALLY studied for the specified polymer using the specified force field in this article
2. Whether the extracted numerical value matches the article value AFTER converting the article's value to the standard unit

**Flag as "NO" ONLY if:**
- The polymer name is wrong or doesn't match
- The force field name is wrong or doesn't match (e.g., "OPLS-AA" vs "OPLS-UA" - they are different)
- The property was NOT studied for this polymer-force field combination
- The numerical value doesn't match even after proper unit conversion
- The value is from an experiment, not a simulation
- The value is mentioned but not actually from a simulation study

**DO NOT flag as "NO" if:**
- The extracted value matches the article value after unit conversion (e.g., article says 730 kg/m³, extracted is 0.73 - this is CORRECT)
- The article discusses experimental comparisons or deviations (this doesn't make the simulation value wrong)
- The article mentions other values or conditions (as long as the extracted value is correct for the specified polymer-force field)
- The extracted value lacks unit labels (this is expected - values are in standard units)

**Examples of CORRECT extractions (mark as "YES"):**
- Article reports: "density of 730 kg/m³" → Extracted: 0.73 → CORRECT (730 kg/m³ = 0.73 g/cm³)
- Article reports: "density of 1048 kg/m³" → Extracted: 1.048 → CORRECT (1048 kg/m³ = 1.048 g/cm³)
- Article reports: "Tg = 480°C" → Extracted: 753.15 → CORRECT (480°C = 753.15 K)

**Examples of INCORRECT extractions (mark as "NO"):**
- Article reports: "density of 730 kg/m³" → Extracted: 0.75 → INCORRECT (doesn't match after conversion)
- Article reports: "OPLS-AA force field" → Extracted: "OPLS-UA" → INCORRECT (wrong force field)
- Article reports experimental value → Extracted as simulation value → INCORRECT

**Response Format:**
Return a JSON array with the same length as the input array. Each object should have:
- "entry_index": the index (0-based) of the entry in the input array
- "answer": "YES" or "NO"
- "reasoning": detailed explanation (include unit conversions you performed)

Example format:
[
  {{"entry_index": 0, "answer": "YES", "reasoning": "Verified correct. Article reports 730 kg/m³, which converts to 0.73 g/cm³, matching the extracted value of 0.73."}},
  {{"entry_index": 1, "answer": "NO", "reasoning": "Force field name doesn't match. Article uses 'OPLS-AA' but extracted value is 'OPLS-UA'."}},
  ...
]

Return ONLY valid JSON. Do not include any markdown formatting or explanations outside the JSON.
"""
    return prompt

def call_gpt4o_mini(prompt, max_retries=3):
    #Call GPT-4o-mini API
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                #max_tokens=4000  # Increased for multiple entries
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  
            else:
                raise

def call_deepseek(prompt, max_retries=3):
    #Call DeepSeek API
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=4000  # Increased for multiple entries
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
            else:
                raise

def parse_response(response):
    #Parse AI response to extract YES/NO answer and reasoning.
    if not response:
        return "UNKNOWN", "Empty response"
    
    response = response.strip()
    
    # Try to extract YES/NO from the beginning
    upper_response = response.upper()
    if upper_response.startswith("YES"):
        answer = "YES"
        reasoning = response[3:].strip()
    elif upper_response.startswith("NO"):
        answer = "NO"
        reasoning = response[2:].strip()
    else:
        # Try to find YES/NO in the first 100 characters
        first_part = response[:100].upper()
        if "YES" in first_part and "NO" not in first_part:
            answer = "YES"
            reasoning = response
        elif "NO" in first_part:
            answer = "NO"
            reasoning = response
        else:
            answer = "UNKNOWN"
            reasoning = response
    
    return answer, reasoning

def parse_structured_response(response, num_entries):
    """Parse structured JSON response from AI with answers for all entries."""
    try:
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        results = json.loads(response)
        
        # Create a dictionary indexed by entry_index
        result_dict = {}
        for item in results:
            idx = item.get("entry_index", -1)
            if 0 <= idx < num_entries:
                result_dict[idx] = {
                    "answer": item.get("answer", "UNKNOWN"),
                    "reasoning": item.get("reasoning", "")
                }
        
        # Fill in arrays for all entries
        answers = []
        reasonings = []
        for i in range(num_entries):
            if i in result_dict:
                answers.append(result_dict[i]["answer"])
                reasonings.append(result_dict[i]["reasoning"])
            else:
                answers.append("ERROR")
                reasonings.append("Missing response for this entry")
        
        return answers, reasonings
    except Exception as e:
        # Fallback: return ERROR for all entries
        return ["ERROR"] * num_entries, [f"Failed to parse response: {str(e)}"] * num_entries

def verify_extracted_data():
    
    base_dir = Path(__file__).parent.parent
    json_path = base_dir / "json_outputs" / "md_file_data.json"
    md_base_dir = base_dir / "comparison_set_hpc"
    output_csv = base_dir / "json_outputs" / "verification_results.csv"
    
    # Ensure output directory exists
    output_csv.parent.mkdir(exist_ok=True)
    
    # Load JSON data
    print("Loading JSON data...")
    data = load_json_data(json_path)
    print(f"Loaded {len(data)} md_files")
    
    # Prepare CSV output
    csv_rows = []
    
    # Process each md_file
    total_entries = sum(len(entries) for entries in data.values())
    processed = 0
    counter = 0
    for md_file, entries in data.items():
        if counter <= 31:
            counter += 1
            continue
        counter += 1
        print(f"\nProcessing {md_file} ({len(entries)} entries)...")
        
        # Load MD file content
        try:
            md_content = load_md_file(md_file, md_base_dir)
        except FileNotFoundError as e:
            print(f"Warning: {e}")
            # Still process entries but mark as error
            for entry in entries:
                csv_rows.append({
                    "md_file": md_file,
                    "polymer_name": entry.get("Polymer Name", ""),
                    "force_field": entry.get("Force Field", ""),
                    "properties": entry.get("Properties", ""),
                    "value": entry.get("Value", ""),
                    "ai_model_1_answer": "ERROR",
                    "ai_model_2_answer": "ERROR",
                    "notes_model_1": f"MD file not found: {e}",
                    "notes_model_2": f"MD file not found: {e}"
                })
            continue
        
        # Process all entries for this md_file at once
        print(f"  Verifying {len(entries)} entries", end=" ", flush=True)
        
        # Create verification prompt with ALL entries
        prompt = create_verification_prompt(md_content, entries)
        
        # Call both APIs ONCE for all entries
        gpt_answers = ["ERROR"] * len(entries)
        gpt_reasonings = [""] * len(entries)
        deepseek_answers = ["ERROR"] * len(entries)
        deepseek_reasonings = [""] * len(entries)
        
        try:
            gpt_response = call_gpt4o_mini(prompt)
            gpt_answers, gpt_reasonings = parse_structured_response(gpt_response, len(entries))
            print("GPT-4o-mini", end=" ", flush=True)
        except Exception as e:
            gpt_reasonings = [f"API error: {str(e)}"] * len(entries)
            print(f"GPT-4o-mini ({str(e)[:50]})", end=" ", flush=True)
        
        try:
            deepseek_response = call_deepseek(prompt)
            deepseek_answers, deepseek_reasonings = parse_structured_response(deepseek_response, len(entries))
            print("DeepSeek")
        except Exception as e:
            deepseek_reasonings = [f"API error: {str(e)}"] * len(entries)
            print(f"DeepSeek({str(e)[:50]})")
        
        # Add delay between API calls to avoid rate limiting
        time.sleep(1)
        
        # Add rows to CSV
        for i, entry in enumerate(entries):
            processed += 1
            csv_rows.append({
                "md_file": md_file,
                "polymer_name": entry.get("Polymer Name", ""),
                "force_field": entry.get("Force Field", ""),
                "properties": entry.get("Properties", ""),
                "value": entry.get("Value", ""),
                "ai_model_1_answer": gpt_answers[i],
                "ai_model_2_answer": deepseek_answers[i],
                "notes_model_1": gpt_reasonings[i],
                "notes_model_2": deepseek_reasonings[i]
            })
    
    # Write CSV file
    print(f"\nWriting results to {output_csv}")
    fieldnames = ["md_file", "polymer_name", "force_field", "properties", "value",
                  "ai_model_1_answer", "ai_model_2_answer", "notes_model_1", "notes_model_2"]
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"Written {len(csv_rows)} rows to CSV")
    
    # Print summary statistics
    gpt_no_count = sum(1 for row in csv_rows if row["ai_model_1_answer"] == "NO")
    deepseek_no_count = sum(1 for row in csv_rows if row["ai_model_2_answer"] == "NO")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total entries verified: {len(csv_rows)}")
    print(f"GPT-4o-mini flagged as incorrect: {gpt_no_count} ({100*gpt_no_count/len(csv_rows):.1f}%)")
    print(f"DeepSeek flagged as incorrect: {deepseek_no_count} ({100*deepseek_no_count/len(csv_rows):.1f}%)")
    print("="*50)

if __name__ == "__main__":
    verify_extracted_data()

