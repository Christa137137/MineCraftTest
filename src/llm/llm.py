from openai import OpenAI
import os
import time
# prohibit use of system proxy
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

class LLM:
    def __init__(self, model="deepseek-chat"):

        if model == "gemini":
            self.client = OpenAI(
                api_key="AIzaSyA1ZFYw2v_HW5wFnOLIOmoVYxPdOIr2IkE", 
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            self.model = "gemini-2.5-flash"
        elif model == "deepseek-chat":
            self.client = OpenAI(
                api_key="sk-a35ac642afb24e3097069b2a66dc1884",
                base_url="https://api.deepseek.com"
            )
            self.model = "deepseek-chat"

    def chat(self, prompt):
        max_retries = 5
        for i in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                if response is None:
                    raise ValueError("[API Error] API returned None object")
                return response.choices[0].message.content
            except Exception as e:
                print(f"[API Error]: {e}")
                time.sleep(10 * (i + 1))
        return "{}"

if __name__ == "__main__":
    llm = LLM()
    result = llm.chat("hello")
    print(result)