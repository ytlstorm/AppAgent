import re
from abc import abstractmethod
from typing import List
from http import HTTPStatus

import requests
import dashscope

from utils import print_with_color, encode_image


class BaseModel:
    def __init__(self):
        pass

    @abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        pass


class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        for img in images:
            base64_img = encode_image(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            })
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        response = requests.post(self.base_url, headers=headers, json=payload).json()
        if "error" not in response:
            usage = response["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            print_with_color(
                f"Request cost is ${'{0:.2f}'.format(prompt_tokens / 1000 * 0.01 + completion_tokens / 1000 * 0.03)}",
                "yellow",
            )
        else:
            return False, response["error"]["message"]
        return True, response["choices"][0]["message"]["content"]


class QwenModel(BaseModel):
    def __init__(self, api_key: str, model: str):
        super().__init__()
        self.model = model
        dashscope.api_key = api_key

    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        content = [{"text": prompt}]
        for img in images:
            img_path = f"file://{img}"
            content.append({"image": img_path})
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        response = dashscope.MultiModalConversation.call(model=self.model, messages=messages)
        if response.status_code == HTTPStatus.OK:
            return True, response.output.choices[0].message.content[0]["text"]
        else:
            return False, response.message


def _extract_field(rsp: str, label: str, next_labels: list[str]) -> str:
    if next_labels:
        escaped = [re.escape(x) for x in next_labels]
        lookahead = "|".join(rf"^\s*{x}\s*:" for x in escaped)
        pattern = rf"^\s*{re.escape(label)}\s*:\s*(.*?)\s*(?=(?:{lookahead})|\Z)"
    else:
        pattern = rf"^\s*{re.escape(label)}\s*:\s*(.*?)\s*\Z"
    matched = re.search(pattern, rsp, flags=re.MULTILINE | re.DOTALL)
    if not matched:
        raise ValueError(f"Missing field: {label}")
    return matched.group(1).strip()


def parse_explore_rsp(rsp):
    try:
        observation = _extract_field(rsp, "Observation", ["Thought", "Action", "Summary"])
        think = _extract_field(rsp, "Thought", ["Action", "Summary"])
        act = _extract_field(rsp, "Action", ["Summary"])
        last_act = _extract_field(rsp, "Summary", [])
        print_with_color("Observation:", "yellow")
        print_with_color(observation, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        print_with_color("Action:", "yellow")
        print_with_color(act, "magenta")
        print_with_color("Summary:", "yellow")
        print_with_color(last_act, "magenta")
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            area = int(re.findall(r"tap\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "text":
            input_str = re.findall(r"text\((.*?)\)", act)[0][1:-1]
            return [act_name, input_str, last_act]
        elif act_name == "long_press":
            area = int(re.findall(r"long_press\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0]
            area, swipe_dir, dist = params.split(",")
            area = int(area)
            swipe_dir = swipe_dir.strip()[1:-1]
            dist = dist.strip()[1:-1]
            return [act_name, area, swipe_dir, dist, last_act]
        elif act_name == "grid":
            return [act_name]
        else:
            print_with_color(f"ERROR: Undefined act {act_name}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_grid_rsp(rsp):
    try:
        observation = _extract_field(rsp, "Observation", ["Thought", "Action", "Summary"])
        think = _extract_field(rsp, "Thought", ["Action", "Summary"])
        act = _extract_field(rsp, "Action", ["Summary"])
        last_act = _extract_field(rsp, "Summary", [])
        print_with_color("Observation:", "yellow")
        print_with_color(observation, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        print_with_color("Action:", "yellow")
        print_with_color(act, "magenta")
        print_with_color("Summary:", "yellow")
        print_with_color(last_act, "magenta")
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            params = re.findall(r"tap\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "long_press":
            params = re.findall(r"long_press\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0].split(",")
            start_area = int(params[0].strip())
            start_subarea = params[1].strip()[1:-1]
            end_area = int(params[2].strip())
            end_subarea = params[3].strip()[1:-1]
            return [act_name + "_grid", start_area, start_subarea, end_area, end_subarea, last_act]
        elif act_name == "grid":
            return [act_name]
        else:
            print_with_color(f"ERROR: Undefined act {act_name}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_reflect_rsp(rsp):
    try:
        decision = _extract_field(rsp, "Decision", ["Thought", "Documentation"])
        think = _extract_field(rsp, "Thought", ["Documentation"])
        print_with_color("Decision:", "yellow")
        print_with_color(decision, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        if decision == "INEFFECTIVE":
            return [decision, think]
        elif decision == "BACK" or decision == "CONTINUE" or decision == "SUCCESS":
            doc = _extract_field(rsp, "Documentation", [])
            print_with_color("Documentation:", "yellow")
            print_with_color(doc, "magenta")
            return [decision, think, doc]
        else:
            print_with_color(f"ERROR: Undefined decision {decision}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]
