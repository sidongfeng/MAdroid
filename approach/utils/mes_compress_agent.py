import sys
from pathlib import Path

utils_path = Path(__file__).resolve().parent
sys.path.append(str(utils_path))

from base_utils import llm


# In the observer phase, compress excessive information from current user screen.
class Message_compression_agent:
    def __init__(self):
        self.llm = llm.GeneralGPT("gpt-35-turbo")
        self.messages = []

    def messages_compression(self, mes: str, is_multi_agent=False):
        system_prompt = """I want you to act as a information compressor. I would provide you with a string that used on 
        ui automation testing. I want you to compress this string by tenfold. This string will have multiple lines. You 
        simply need to condense and retain the key or essential information from the original string. Do not write 
        'explanations. You should output compressed text only."""
        self.messages = [{"role": "system", "content": system_prompt}]
        t = ""
        if is_multi_agent:
            t = ("I would like you to compress the original string into four parts: Task, Page, Elements, "
                 "and Operation. In Task, provide a brief description of the task. In Page, describe the current "
                 "interface. In Elements, list the ten (or fewer) most important elements on the current interface "
                 "that are helpful for completing the task. with at least half of them being in Chinese (or all in "
                 "English if there are no Chinese elements in the original string). And in Operation, include the "
                 "separate sentence 'Switch Device if needed'.")
        prompt = t + "Here are the string I want you to compress:\nstring:\n"
        prompt += mes
        new_message = {"role": "user", "content": prompt}
        self.messages.append(new_message)
        result = self.llm.ask_gpt_message(messages=self.messages)
        return result['content']
