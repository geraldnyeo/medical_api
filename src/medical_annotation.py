"""
Medical Annotation

This module has two possible methods for annotating medical notes:
 - Using deepseek LLM to label medical notes.
 - Using a trained NER model to label medical notes.
"""
# Imports
import re
import regex
from Levenshtein import distance

import pandas as pd

import sparknlp
from sparknlp.annotator import NerDLModel
from pyspark.sql import functions as F
from pyspark.ml import PipelineModel

from langchain.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import JsonOutputParser

# Configuration
deepseek_api_key = "sk-9edb6eb971074472814d05f87c9c3d59"

spark = sparknlp.start(gpu=False)

# Substitution for NLTK word tokenize
def word_tokenize(text):
    text = re.sub(r'([.,!?;:])(\S)', r'\1 \2', text)
    text = re.sub(r'(\S)([.,!?;:])', r'\1 \2', text)
    # Split by whitespace
    return text.split()

# Default headers for splitting sections
headers = {
    "HOPC": "C",
    "History of Presenting Complaint": "C",
    "Test Results": "F",
    "On Examination": "F",
    "O/e": "F",
    "Imp": "D",
    "Impression": "D",
    "Plan": "T"
}

# Regex text section splitter
def regex_splitter(text, headers=headers, group=True):
  """
  Splits a document into sections based on the headers provided, categorising each section.

  Parameters
  ----------
  headers: dict, with items of the format
    - header (str): section type (str)

  text: str, text to split

  group: bool, default True
    - determines whether to group sections of the same type in the output

  Returns
  -------
  sections: dict, with items of the format
    - section type (str): text (str) (if group == True)
    - header (str): {
      "type": section type (str)
      "text": section type (str)
    } (if group == False)
  """
  # Construct regex
  r_headers = [fr'(?:{h}:){{e<={len(h.split(" "))}}}' for h in headers.keys()]
  r = r"|".join(r_headers)
  r = fr'(?s)(({r}).*?)(?=(?:{r}|\Z))'

  # Capture sections from text
  section_list = regex.findall(r, text)

  # Create dictionary
  sections = {}
  for s in section_list:
    header_matched = s[1]
    header_actual = min(headers.keys(), key=lambda x: distance(x, header_matched))
    section_type = headers[header_actual]

    if group:
      if section_type in sections.keys():
        sections[section_type] += s[0]
      else:
        sections[section_type] = s[0]

    else:
      sections[header_actual] = {
          "type": section_type,
          "text": s[0]
      }

  return sections

# LLM text section splitter
def llm_splitter(text):
    """
    Splits a document into sections based on the headers provided, categorising each section.
    Note that currently, since the formatting is based on the LLM prompt, headers are pre-determined and sections are always grouped where possible.

    Parameters
    ----------
    text: str, text to split

    Returns
    -------
    sections: dict, with items of the format
    section type (str): text (str)
    """
    llm = ChatDeepSeek(
        model="deepseek-chat",
        # temperature=0,
        max_tokens=None,
        api_key=deepseek_api_key
    )

    llm_prompt_split = open("./prompts/llm_prompt_split.txt").read()
    messages = [
        ("system", llm_prompt_split),
        ("human", "Split the following text: {text}")
    ]
    split_prompt_template = ChatPromptTemplate.from_messages(messages)

    split_chain = split_prompt_template | llm | JsonOutputParser()

    result = split_chain.invoke({"text": text})

    return result

# Annotate single text using deepseek
def annotate_llm(text, 
                 mode="append"):
    """
    Annotate a single medical note using deepseek

    Parameters
    ----------
    text: str
    mode: (str) reason for visit, to select correct LLM prompt for annotation

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
        print(mode)
        # Invoke LLM
        llm_prompt = open(f"./prompts/llm_prompt_{mode}.txt").read()
        print(llm_prompt)
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
def annotate_ner(mode,
                 text = None,
                 sections = None,
                 splitting_mode = "regex"):
    """
    Annotate a single medical note using NER models

    Parameters
    ----------
    mode: (str) reason for visit, to select correct LLM prompt for annotation
    text: (str) raw text of entire clinical note
        must be set if parameter "sections" is None
    sections: (dict) pre-split sections of clinical note, in the format:
        { section_type: text }
        must contain at least diagnosis (D) and treatment (T) sections
        must be set if parameter "text" is None
    splitting_mode: (str): (str) "regex" or "llm", determines whether to use regex or LLM for splitting text
        regex by default

    Returns
    -------
    tokens: list
    labels: list
    """
    if text == None and sections == None:
       raise ValueError("Either one of 'text' or 'sections' parameters must be set!")
    
    if text != None:
        if splitting_mode == "regex":
            sections = regex_splitter(text)
        elif splitting_mode == "llm":
            sections = llm_splitter(text)
        else:
            raise ValueError("Invalid splitting mode!")

    pipe_path = "./models/ner_pipe"
    ner_pipe = PipelineModel.load(pipe_path)

    SYM_models = {
        "ffi_dental": "./models/ner_SYM_dental_52"
    }
    SYM_model_path = SYM_models[mode]
    SYM_model = NerDLModel.load(SYM_model_path)

    DIA_models = {
        "ffi_dental": "./models/ner_DIA_dental_52"
    }
    DIA_model_path = DIA_models[mode]
    DIA_model = NerDLModel.load(DIA_model_path)

    TRT_models = {
        "ffi_dental": "./models/ner_TRT_dental_52"
    }
    TRT_model_path = TRT_models[mode]
    TRT_model = NerDLModel.load(TRT_model_path)
    
    section_annotators = {
        "C": SYM_model,
        "F": SYM_model,
        "D": DIA_model,
        "T": TRT_model
    }

    tokens, labels = [], []
    for section_type, text in sections.items():
        if section_type not in section_annotators.keys():
            t = word_tokenize(text)
            l = ["O"] * len(t)
        else:
            text_spark_df = spark.createDataFrame([[text]]).toDF("text")

            preprocessed = ner_pipe.transform(text_spark_df)
            result = section_annotators[section_type].transform(preprocessed)
            # result.show()

            ner_result = result.select("ner").first().ner
            t = [r.metadata['word'] for r in ner_result]
            l = [r.result for r in ner_result]

        tokens.extend(t)
        labels.extend(l)

    return tokens, labels

# Summarize single text using deepseek
def summarize_llm(text = None,
                  sections = None,
                  splitting_mode = "regex"):
    """
    Summarizes a single note using deepseek

    Parameters
    ----------
    text: (str) raw text of entire clinical note
        must be set if parameter "sections" is None
    sections: (dict) pre-split sections of clinical note, in the format:
        { section_type: text }
        must contain at least diagnosis (D) and treatment (T) sections
        must be set if parameter "text" is None
    splitting_mode: (str) "regex" or "llm", determines whether to use regex or LLM for splitting text
        regex by default
        # TODO: Add 'None' mode for when using LLM to summarize directly, without pre-extraction of diagnosis and treatment sections.
    
    Returns
    -------
    category: str
    summary: str
    """
    if text == None and sections == None:
       raise ValueError("Either one of 'text' or 'sections' parameters must be set!")

    if text != None:
        if splitting_mode == "regex":
            sections = regex_splitter(text)
        elif splitting_mode == "llm":
            sections = llm_splitter(text)
        else:
            raise ValueError("Invalid splitting mode!")

    try:
        dt = sections["D"] + sections["T"]
    except Exception as e:
        raise KeyError("Diagnosis or Treatment section is missing.")

    llm = ChatDeepSeek(
        model="deepseek-chat",
        # temperature=0,
        max_tokens=None,
        api_key=deepseek_api_key
    )
    
    llm_prompt = open("./prompts/llm_prompt_summarize_dt.txt").read()
    messages = [
        ("system", llm_prompt),
        ("human", f"Summarize the following text:\n{dt}\n")
    ]
    result = llm.invoke(messages)

    category = re.search(r'Category: (.+)\n', result.content).group(1)
    category = category.strip()

    return category, result.content



HELLO_FUTURE_ME_HERE_ARE_SOME_NOTES = """ \
Currently the api for annotation does this:
 - generate labels (annotate_llm)
 - generate summary (summarize_llm)

This is inefficient because in the future annotate_llm may be upgraded to use multiple mode or swapped to annotate_NER, resulting in two instances of section splitting, which is expensive LLM-token wise. To solve this, we will change the api structure in the future to
 - generate sections (regex / llm splitter)
 - generate labels from sections
 - generate summary from sections

No changes need to be made to the current functions, as they can already accept section input instead of raw text input.
"""