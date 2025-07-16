import email
from email import policy
from google.cloud import storage
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

def download_and_parse_eml(gcs_path):
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
            response_schema={
                'required': ['date', 'fuel_consumed'],
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date-time'},
                    'fuel_consumed': {
                        'type': 'object',
                        'properties': {
                            "VLSFO": {'type': 'number', "nullable": True},
                            "MGO": {'type': 'number', "nullable": True},
                            "IFO": {'type': 'number', "nullable": True},
                            "LSBF": {'type': 'number', "nullable": True},
                            "LSGO": {'type': 'number', "nullable": True}
                        }
                    }
                }
            },
            system_instruction='''
            You are required to extract data from the provided text, which is from a maritime noon report email text.
            The email is a daily report from a shipping company, containing information about the ships, their
            locations, and other relevant details. I will provide you with the text of the email in the contents parameter, and you will extract the required information.


            <TASK>
            Extract the following information from the email text:
            
            - Date of the email report
            - Fuel consumed by fuel types present in the report

            **Key Reminder:**
            * ** Date formats might vary but look for date formats like:
            *   - "24th Jan'25" 
            *   - "24/01/2025"
            *   - "January 24, 2025"
            * ** Look for variations in how fuel consmption might be reported, such as:
            *   - "Bunkers consumed in last 24 hours: VLSFO - 0.1mt, MGO - 2.4mt"
            *   - "24hr consumption: VLSFO: 1.2 MT, MGO: 0.4 MT"
            *   - "Consumed: HSFO: nil / VLSFO: 22.4mt / LSGO: nil"
            *   - "Fuel Used: 10.2MT VLSFO"
            </TASK>

            <CONSTRAINTS>
                * **Schema Adherence:**  **Strictly adhere to the provided schema in the response_schema variable.**  Do not invent or assume any data or schema elements beyond what is given.
                * **If the email does not contain any relevant information, return an empty JSON object.
                * **Do not include any additional text or explanations, just return the JSON object.
                * **Ensure that the date is in the format YYYY-MM-DD and the fuel amounts are numerical values.
                * **If any information is missing or cannot be determined, leave that field out of the JSON object.


            </CONSTRAINTS>

            <FEW_SHOT_EXAMPLES>
            1. **Example of an email text:**
            ```
            To: Core Petroleum

            Cc: Zodiac Maritime Ltd. London
            Attn: OPS/EC

            Fm: Libra Sun

            Good day,


            24th Jan'25/Noon 12:00LT (20:00UTC)
            ===============
            Vessel's position (Lat/Long): 37-12.4N/122-41.9W
            ETA: 25th Jan 2025 // 1900 Lt (26th Jan 2025 // 03:00 UTC)
            Average speed in knots for the last 24 hours : 11.1
            Average slip in the last 24 hours: -6.3
            Distance transited in the last 24 hours (in nautical miles): 30
            Distance miles remaining (in nautical miles) : 345
            Bunkers ROB (all grades): VLSFO(S<0.5%) - 418.50mt, MGO - 343.7mt
            Bunkers consumed in last 24 hours: VLSFO - 0.1mt, MGO - 2.4mt
            Weather:
            ��� -Wind direction and force.:� NW X 3
            ��� -Sea state direction and maximum sea state.: NW X 2
            ��� -Swell direction and height.: NW X 2.0 mtrs
            ��� -Visibility in miles.: 10nm
            Slops on board and percentage full (tank locations and remarks): NA
            Cargo temperatures (if applicable-report in C and F).: NA
            Remarks:


            Thanks & Best Regards,

            Capt. Fedotov Mikhail

            Master of M/T Libra Sun
            �--------------------------------------------------------
            VSAT Tel:+442037693022
            Iridium :+881677105202
            Sat C Telex: 463714789
            Email: LibraSun.D5EJ4@maritimevessel.com
            --------------------------------------------------------
            (In case of any Urgent Messages, Please follow-up with a telephone call)

            *********************************************
            To all concerned parties. This is to notify you that the vessel business 
            email has changed to: LibraSun.D5EJ4@maritimevessel.com
            Please make sure that you have updated your contact list accordingly
            *********************************************
            ```

            **Example of expected output:**:
            {
                "date": "2025-01-24",
                "fuel_consumed": {
                    "VLSFO": 0.1,
                    "MGO": 2.4
                }
            </FEW_SHOT_EXAMPLES>
            '''
        )
    )
    return response.text

def main(gcs_path):
    plain_text = download_and_parse_eml(gcs_path)
    if not plain_text:
        return {}
    print(plain_text)

    response = llm_keywrds(plain_text)
    if not response:
        return {}

    return response
    
if __name__ == "__main__":
    # Example usage
    gcs_path = "gs://noon-reports-dev/year=2025/month=01/day=24/LIBRA SUN RICHMOND TO LONG BEACH_108SV32_ Q88 - Daily Noon Report.eml"

    parsed_response = main(gcs_path)
    print(parsed_response)

