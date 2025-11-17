from zai import ZhipuAiClient
import os
import re
import json

def extract_code_blocks(content, language='yaml'):   
    """Regular expression to match code blocks"""

    if isinstance(language, str):
        code_block_pattern = re.compile(rf'```{language}\n(.*?)```', re.DOTALL)
    else:
        language = "|".join(language)    
        code_block_pattern = re.compile(rf'```(?:{language})\n(.*?)```', re.DOTALL)
    code_blocks = code_block_pattern.findall(content)

    return code_blocks

def extract_blocks(text):
    pattern = r'```(\w+)\s*(?://\s*file[_-]?name:\s*([^\n]+)\s*)?(.+?)\s*```'
    
    matches = re.findall(pattern, text, re.DOTALL)
    
    result = []
    for match in matches:
        lang, filename, content = match
        result.append({
            'language': lang.strip(),
            'filename': filename.strip() if filename else None,
            'content': content.strip() 
        })
    return result

class GlmAgent:
    def __init__(self, **kwargs):
        self.client = ZhipuAiClient(timeout=600.0) 

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model="glm-4.5",
            messages=messages,
            thinking={
                "type": "disabled",    # 启用深度思考模式
                #"type": "enabled",    # 启用深度思考模式
            },
            max_tokens=65536,          # 最大输出tokens
            temperature=0.1           # 控制输出的随机性
        )   

        #json_result = extract_code_blocks(response.choices[0].message.content, ["json", "cpp"])
        result = extract_blocks(response.choices[0].message.content)
        return result

class GPTAgent:
    def __init__(self):
        self.url = 'https://api2.road2all.com/v1/chat/completions'        
        self.model = "gpt-4o"
        self.temperature = 0.1
        self.stream = False
    def chat(self, messages):
        import urllib
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": self.stream
        }    
        data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header('Content-Type', 'application/json')
        access_key = os.environ.get("OPENAI_API_KEY")
        req.add_header('Authorization', access_key)
        try: 
            with urllib.request.urlopen(req) as response:
                response_content = response.read().decode('utf-8')
                response_content = json.loads(response_content)
                content = response_content["choices"][0]["message"]["content"]
                result = extract_blocks(content)
                return result
        except Exception as e:
            print(e)        
            return []

            
        
if __name__ == '__main__':
    agent = GlmAgent()
    messages = \
"""
Please generate a dict, where keys are numbers from 1 to 12 and values are corresponding ordinal numbers.

### Output Requirement
Your output must be formatted in JSON. No other redundant content is allowed to be output.
"""
    agent.chat(messages)