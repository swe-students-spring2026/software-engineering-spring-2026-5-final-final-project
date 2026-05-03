import json
from functools import lru_cache
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import MAX_NEW_TOKENS, LLM_MODEL


@lru_cache(maxsize=1)
def load_model():
    """Cached model loader"""
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL)

    return tokenizer, model


def generate(prompt):
    """Generate prompt"""
    tokenizer, model = load_model()

    messages = [{"role": "user", "content": prompt}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=MAX_NEW_TOKENS,
    )

    return tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True
    ).strip()


def parse_json(text):
    """Parse llm generated json"""
    start = text.find("{")
    end = text.find("}")

    if start == -1 or end == -1:
        raise ValueError("Invalid JSON format")

    return json.loads(text[start : end + 1])


def reverse_query(query):
    """Return the opposite meaning of the attribute query"""
    prompt = f"""
Return the qualities that mean the opposite of the following attribute.
Return only the antonym phrase, with no explanation.

Attribute: {query}
""".strip()

    return generate(prompt)


def split_query(query, debug=False):
    """Split the query, and reverse the attribute query"""
    prompt = f"""
Split the user's request into exactly two parts.
Return exactly one valid JSON object:

Definitions:
- "attribute": the desired qualities, atmosphere, or characteristics.
- "cleaned_query": user's request minus the attribute.

Rules:
- Preserve the user's meaning.
- Output JSON only.
- Do not include explanations or markdown.

User request: {query}
""".strip()

    response = generate(prompt)
    parsed = parse_json(response)

    attribute = parsed["attribute"]
    place_type = parsed["cleaned_query"]
    reversed_attribute = reverse_query(attribute)

    if debug:
        print(response)
        print(attribute, "->", reversed_attribute)
        print(place_type)

    return reversed_attribute, place_type
