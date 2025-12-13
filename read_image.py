import base64
from openai import OpenAI
b64 = base64.b64encode(open('receipt.jpg','rb').read()).decode()
r = OpenAI().chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':[{'type':'text','text':'Extract all text from this receipt'},{'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{b64}'}}]}])
print(r.choices[0].message.content)

