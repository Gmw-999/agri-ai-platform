import re
import json


def fix_json_escaping(text: str) -> str:
    """修复JSON字符串的转义、括号匹配、多余逗号等问题"""
    # 修复过度转义的反斜杠
    text = text.replace('\\\\\\"', '\\"').replace('\\\\"', '"')

    # 修复引号不匹配
    quote_count = text.count('"')
    if quote_count % 2 != 0:
        text += '"'

    # 修复大括号/中括号不匹配
    brace_balance = text.count('{') - text.count('}')
    if brace_balance > 0:
        text += '}' * brace_balance
    bracket_balance = text.count('[') - text.count(']')
    if bracket_balance > 0:
        text += ']' * bracket_balance

    # 移除末尾多余逗号
    text = re.sub(r',\s*([}\]])', r'\1', text)

    return text