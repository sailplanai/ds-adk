import email
from email import policy
from google.cloud import storage
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional, List, Literal, Union
from datetime import date, datetime
from prompts import return_email_instructions, return_pdf_instructions, return_dream_specific_instructions
import io
import json

load_dotenv()


FuelType = Literal["VLSFO", "MGO", "IFO", "LSBF", "LSGO"]

class EngineValue(BaseModel):
    me1: Optional[float] = None
    me2: Optional[float] = None
    me3: Optional[float] = None
    me4: Optional[float] = None
    me5: Optional[float] = None

class FuelKeyValuePair(BaseModel):
    fuel_type: FuelType
    value: Union[float, EngineValue]

class LLMParserResponse(BaseModel):
    date: datetime
    # List of fuel type-value pairs instead of a dict
    fuel_consumed: List[FuelKeyValuePair]
    power_generated: Optional[float] = None

def download_and_parse_eml(gcs_path: str):
    bucket_name, blob_name = gcs_path.replace("gs://", "").split("/", 1)
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    eml_string = blob.download_as_text()

    msg = email.message_from_string(eml_string, policy=policy.default)
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            return part.get_content()
    return ""

def download_pdf(gcs_path: str):
    bucket_name, blob_name = gcs_path.replace("gs://", "").split("/", 1)
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    pdf_bytes = blob.download_as_bytes()
    
    return io.BytesIO(pdf_bytes)

def download_and_parse_gcs(gcs_path: str):
    if gcs_path.lower().endswith('.eml'):
        return download_and_parse_eml(gcs_path)
    elif gcs_path.lower().endswith('.pdf'):
        return download_pdf(gcs_path)
    else:
        raise ValueError("Unsupported file type: must be .eml or .pdf")

def llm_keywrds_eml(plain_text: str):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=plain_text,
        config=types.GenerateContentConfig(
            thinking_config = types.ThinkingConfig(thinking_budget=0),
            temperature=0.01,
            max_output_tokens=1000,
            response_mime_type="application/json",
            response_schema=LLMParserResponse,
            system_instruction=return_email_instructions()
        )
    )
    return response.text

def llm_keywrds_pdf(file, example_file=None, example_output=None):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    content_file = client.files.upload(file=file, config=types.UploadFileConfigDict(mime_type="application/pdf"))

    contents = [return_dream_specific_instructions()]
    
    # If we have an example file and output, include them in the prompt
    if example_file and example_output:
        example_content_file = client.files.upload(file=example_file, config=types.UploadFileConfigDict(mime_type="application/pdf"))
        contents.append(f"Example PDF 1 [attached]:")
        contents.append(example_content_file)
        contents.append(f"Example PDF 1 expected output: {example_output}")
    
    # Add the main prompt and target file
    contents.append("Target PDF [attached]:")
    contents.append(content_file)
    
    # Improved printing of contents for debugging
    # for i, content in enumerate(contents):
    #     if isinstance(content, str):
    #         print(f"Item {i}: Text - {content}")
    #     else:
    #         # This is likely a file object
    #         print(f"Item {i}: File object - {type(content)}")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0), # Striaghtforward request, no complex reasoning needed "Fact Retrieval or classification"
            temperature=0.01,
            max_output_tokens=1000,
            response_mime_type="application/json",
            response_schema=LLMParserResponse,
            system_instruction=return_pdf_instructions()
        )
    )
    # print(f"Request tokens: {response.usage_metadata.prompt_token_count}")
    # print(f"Response tokens: {response.usage_metadata.candidates_token_count}")
    # print(f"Total tokens: {response.usage_metadata.total_token_count}")
    

    return response.text

def main(target_gcs_path: str, example_gcs_path: str = None, example_output: str = None):
    target_noon_report = download_and_parse_gcs(target_gcs_path)
    example_noon_report = download_and_parse_gcs(example_gcs_path) if example_gcs_path else None
    
    if not target_noon_report:
        return {}
    #print(plain_text)
    if target_gcs_path.lower().endswith('.pdf'):
        response = llm_keywrds_pdf(target_noon_report, example_noon_report, example_output)
    elif target_gcs_path.lower().endswith('.eml'):
        response = llm_keywrds_eml(target_noon_report)

    if not response:
        return {}

    return response
    
if __name__ == "__main__":
    # Example usage
    gcs_path1 = "gs://noon-reports-dev/year=2025/month=01/day=24/LIBRA SUN RICHMOND TO LONG BEACH _108SV32_ - Daily Noon Report.eml"
    gcs_path2 = "gs://noon-reports-dev/year=2025/month=01/day=24/LIBRA SUN RICHMOND TO LONG BEACH_108SV32_ Q88 - Daily Noon Report.eml"
    gcs_path3 = 'gs://noon-reports-dev/year=2024/month=01/day=11/11 JAN .pdf'
    example_gcs_path = 'gs://noon-reports-dev/year=2023/month=12/day=29/29 December .pdf'
    
    with open ('python/agents/noon-parser/disney_dream_example_output.json', 'r') as f:
        example_output = f.read()

    parsed_response = main(gcs_path1)
    print(parsed_response)

    parsed_response = main(gcs_path2)
    print(parsed_response)

    parsed_response = main(gcs_path3, example_gcs_path, example_output)
    print(parsed_response)

