from langchain_community.tools import DuckDuckGoSearchRun
import json
import boto3

class ReAct_agent:
    def __init__(self, client, system_prompt, role_prompt, max_steps=20, search_max_length=1000):
        self.client = client
        self.SYSTEM_PROMPT = system_prompt
        self.ROLE_PROMPT = role_prompt
        self.ddg_search = DuckDuckGoSearchRun()
        self.max_steps = max_steps
        self.step_num = 0
        self.search_max_length = search_max_length
        self.history = ""

    def ask(self, message, verbose = True):
        self.add_to_memory(message)
        model_response = self.invoke_llm(message)
        model_response_json = json.loads(model_response.replace("```json", "").replace("```", "").strip())
        response_type = model_response_json["type"]
        while self.step_num < self.max_steps:
            self.add_to_memory(model_response)
            if response_type == "Action":
                prefix, content = self.parse_action(model_response_json["content"])
                if prefix == "Finish":
                    return content
                elif prefix == "Search":
                    observation = self.search(content)
                    if verbose:
                        print(json.dumps({"type": "Observation", "content": observation}, indent=4))
                    self.add_to_memory(json.dumps({"type": "Observation", "content": observation}))
            model_response = self.invoke_llm(self.history)
            model_response_json = json.loads(model_response.replace("```json", "").replace("```", "").strip())
            response_type = model_response_json["type"]
            if verbose:
                print(json.dumps(model_response_json, indent=4))
            self.step_num += 1

    def search(self, message):
        return self.ddg_search.invoke(message)[:self.search_max_length]

    def invoke_llm(self, message):
        bedrock_runtime_response = bedrock_runtime.converse(
            modelId = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system = [
                {'text': self.SYSTEM_PROMPT}, 
                {'text': self.ROLE_PROMPT}
            ],
            messages = [{"role": "user", "content": [{"text": message}]}]
        )
        return bedrock_runtime_response["output"]['message']['content'][0]['text']

    def add_to_memory(self, message):
        self.history += ", " + message

    def parse_action(self, message):
        start = message.find('[')
        end = message.find(']')
        prefix = message[:start]
        content = message[start+1:end]
        return prefix, content