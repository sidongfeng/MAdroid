import argparse

import requests
import openai
import json
from typing import List, Optional, Mapping, Any


api_key = ""

class GeneralGPT:
    max_tokens: int = 2048
    temperature: float = 0
    model_type: str = "gpt-4-0613"  # "gpt-4",gpt-35-turbo
    n: int = 1
    streaming: bool = False
    history = []

    def __init__(self, model_type=model_type):
        super().__init__()
        self.model_type = model_type

    def ask_gpt_message(self, prompt="", messages=None):
        openai.api_key = api_key

        if messages is None:
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.2,
            frequency_penalty=0.0,
            presence_penalty=0.0)

        return response['choices'][0]['message']
