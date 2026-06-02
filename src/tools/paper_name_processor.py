# name = str(input())
name = """Effective Test Generation Using Pre-trained Large Language Models
and Mutation Testing"""
res = ""
for it in name:
    num = ord(it)
    if not(num >= 48 and num <= 57 or num >= 65 and num <= 90 or num >= 97 and num <= 122):
        res += "_"
    else:
        res += it
print(res)