"""
Medical Annotation

This module has two possible methods for annotating medical notes:
 - Using deepseek LLM to label medical notes.
 - Using a trained NER model to label medical notes.
"""
# Imports
import os

import nltk
from nltk.tokenize import word_tokenize

from langchain_deepseek import ChatDeepSeek

# Configuration
deepseek_api_key = "sk-9edb6eb971074472814d05f87c9c3d59"

# Annotate single text using deepseek
def annotate_llm(text, 
                 mode="append"):
    """
    Annotate a single medical note using deepseek

    Parameters
    ----------
    text: str
    reason: reason for visit, to select correct LLM prompt for annotation

    Returns
    -------
    tokens: list
    labels: list
    """
    llm = ChatDeepSeek(
        model="deepseek-chat",
        # temperature=0,
        max_tokens=None,
        api_key=deepseek_api_key
    )

    if mode == "direct":
        # Invoke LLM
        llm_prompt = open(f"./prompts/llm_prompt_{mode}.txt").read()
        messages = [
            ("system", llm_prompt),
            ("human", f"Unlabelled Text:\n{text}\nLabelled Text:\n")
        ]
        result = llm.invoke(messages)

        # Process the LLM output
        tokens, labels = [], []
        for line in result.content.split("\n"):
            if line == "":
                continue
            l = line.split()
            t, l = l[0], l[1]
            
            tokens.append(t)
            labels.append(l)
        
        return tokens, labels
    
    elif mode == "append":
        # Invoke LLM
        llm_prompt = open(f"./prompts/llm_prompt_{mode}.txt").read()
        messages = [
            ("system", llm_prompt),
            ("human", f"Unlabelled Text:\n{text}\nLabelled Text:\n")
        ]
        result = llm.invoke(messages)

        tokens, labels = [], []
        new = True
        wait = False
        markers = ["X-SYM", "X-SYM-X", "X-HIS", "X-HIS-X", "X-DIA", "X-TRT"]
        for t in word_tokenize(result.content):
            print(t)
            if t in markers and new:
                labels[-1] = f"B-{t[2:]}"
                new = False
                wait = True
            elif t in markers and not new:
                labels[-1] = f"I-{t[2:]}"
                wait = True
            else:
                tokens.append(t)
                labels.append("O")
                if not wait: new = True
                wait = False

        return tokens, labels
    
    else:
        # Invoke LLM
        llm_prompt = open(f"./prompts/llm_prompt_{mode}.txt").read()
        messages = [
            ("system", llm_prompt),
            ("human", f"Unlabelled Text:\n{text}\nLabelled Text:\n")
        ]
        result = llm.invoke(messages)

        tokens, labels = [], []
        new = True
        wait = False
        markers = ["X-SYM", "X-SYM-X", "X-HIS", "X-HIS-X", "X-DIA", "X-TRT"]
        for t in word_tokenize(result.content):
            if t in markers and new:
                labels[-1] = f"B-{t[2:]}"
                new = False
                wait = True
            elif t in markers and not new:
                labels[-1] = f"I-{t[2:]}"
                wait = True
            else:
                tokens.append(t)
                labels.append("O")
                if not wait: new = True
                wait = False

        return tokens, labels

# Annotate single text using NER model
def annotate_ner():
    pass