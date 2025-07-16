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
            * ** Engines should be 1-indexed, meaning the first engine is referred to as "me1", the second as "me2", and so on.
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
                "fuel_consumed": [
                    {
                        "fuel_type": "VLSFO",
                        "value": 0.1
                    },
                    {
                        "fuel_type": "MGO",
                        "value": 2.4
                    }
                ]
            }


            2. **Example of an email text:**
            ```
            [REPORT TYPE : NOON]
            [VCVNIVer : 1.7]
            [Vessel : Libra Sun]
            [PositionDate : 2025/01/24 2000]
            [NOONOffset : -8]
            [ETA : 2025/01/26 0300]
            [NextPortOffset : -8]
            [NOONLat : 37-12.4N]
            [NOONLon : 122-41.9W]
            [TimeSLR : 2.70]
            [Course : 165.00]
            [AvgSpdSLR : 11.10]
            [AvgSpdSinceCOSP : 11.10]
            [DistSinceCOSP : 30.00]
            [DistToGo : 345.00]
            [WindBF : 3]
            [WindDir : 315]
            [SwellDir : 315]
            [SwellHt : 2.0]
            [SeasHt : 0.5]
            [SpdInst : 11.00]
            [WarrantedCons : ]
            [Remarks : ]
            [NextPort : LONG BEACH]
            [DistSLR : 30.00]
            [ECADistSLR : 30.00]
            [ECAZone : US]
            [AvgRpmSLR : 70.20]
            [SlipSLR : -6.3]
            [MCR : 39.000]
            [CargoTemp : ]
            [FreshWaterBROB : 476.000]
            [DraftAft : 8.00]
            [DraftFore : 6.00]
            [mt_LSBF : 418.500]
            [mt_LSGO : 343.700]
            [tank_LSBF : 0]
            [tank_LSGO : 0]
            [slr_LSBF : 0]
            [slr_LSGO : 2.850]
            [scosp_LSBF : 0]
            [scosp_LSGO : 2.850]
            [slrNet_LSBF : 0]
            [slrNet_LSGO : 0.000]
            [scospNet_LSBF : 0]
            [scospNet_LSGO : 0.000]
            [slr_Usage_0 : Maneuver]
            [slr_Engine_0 : Main]
            [slr_LSBF_0 : 0]
            [slr_LSGO_0 : 2.500]
            [slr_Usage_1 : Maneuver]
            [slr_Engine_1 : Aux]
            [slr_LSBF_1 : 0]
            [slr_LSGO_1 : 0.350]
            [slr_Usage_2 : Maneuver]
            [slr_Engine_2 : Boiler]
            [slr_LSBF_2 : 0]
            [slr_LSGO_2 : 0.000]
            [scosp_Usage_0 : Maneuver]
            [scosp_Engine_0 : Main]
            [scosp_LSBF_0 : 0]
            [scosp_LSGO_0 : 2.500]
            [scosp_Usage_1 : Maneuver]
            [scosp_Engine_1 : Aux]
            [scosp_LSBF_1 : 0]
            [scosp_LSGO_1 : 0.350]
            [scosp_Usage_2 : Maneuver]
            [scosp_Engine_2 : Boiler]
            [scosp_LSBF_2 : 0]
            [scosp_LSGO_2 : 0]
            ```

            **Example of expected output:**:
            {
                "date": "2025-01-24",
                "fuel_consumed": [
                    {
                        "fuel_type": "LSBF",
                        "value": {"me1": 0.0, "me2": 0.0, "me3": 0.0}
                    },
                    {
                        "fuel_type": "LSGO",
                        "value": {"me1": 2.5, "me2": 0.35, "me3": 0.0}
            </FEW_SHOT_EXAMPLES>
            '''
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

