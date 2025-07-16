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
from prompts import return_system_instructions

load_dotenv()


FuelType = Literal["VLSFO", "MGO", "IFO", "LSBF", "LSGO"]

class FuelEngineValue(BaseModel):
    me1: Optional[float] = None
    me2: Optional[float] = None
    me3: Optional[float] = None
    me4: Optional[float] = None
    me5: Optional[float] = None

class KeyValuePair(BaseModel):
    fuel_type: FuelType
    value: Union[float, FuelEngineValue]

class LLMParserResponse(BaseModel):
    date: datetime
    # List of fuel type-value pairs instead of a dict
    fuel_consumed: List[KeyValuePair]

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


def llm_keywrds(plain_text: str):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=plain_text,
        config=types.GenerateContentConfig(
            temperature=0.01,
            max_output_tokens=1000,
            response_mime_type="application/json",
            response_schema=LLMParserResponse,
            system_instruction=return_system_instructions()
        )
    )
    return response.text

def main(gcs_path):
    plain_text = download_and_parse_eml(gcs_path)
    if not plain_text:
        return {}
    #print(plain_text)

    response = llm_keywrds(plain_text)
    if not response:
        return {}

    return response
    
if __name__ == "__main__":
    # Example usage
    gcs_path1 = "gs://noon-reports-dev/year=2025/month=01/day=24/LIBRA SUN RICHMOND TO LONG BEACH _108SV32_ - Daily Noon Report.eml"
    gcs_path2 = "gs://noon-reports-dev/year=2025/month=01/day=24/LIBRA SUN RICHMOND TO LONG BEACH_108SV32_ Q88 - Daily Noon Report.eml"

    parsed_response = main(gcs_path1)
    print(parsed_response)

    parsed_response = main(gcs_path2)
    print(parsed_response)

