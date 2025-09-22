from typing import Literal, Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import cast

load_dotenv()


# -----------------------------
# 1️⃣ Define the structured schema
# -----------------------------
class TradeCommand(BaseModel):
    amount: Optional[float] = None
    token: Optional[Literal["BTC", "ETH", "SOL", "ADA", "XRP"]] = None
    leverage: Optional[int] = None
    position: Optional[Literal["long", "short"]] = None
    edit: bool  # always required


# -----------------------------
# 2️⃣ System prompt explaining rules
# -----------------------------
SYSTEM_PROMPT = """
You are a trading assistant. Only output JSON with the following fields:
- amount: float
- token: one of ['BTC', 'ETH', 'SOL', 'ADA', 'XRP']
- leverage: int
- position: 'long' or 'short'
- edit: boolean

Rules:
1. If the user prompt is a new trade (normal), set edit=false and fill all fields.
2. If the user prompt is an edit of a previous trade, set edit=true. Only include fields being changed; other fields should be null.
3. Never output extra text, only JSON.

Notes:
The input text comes from speech-to-text (STT), which may contain errors. For example, “Open one hundred dollar BTC long” might be transcribed as “open 100$ BTC lunch” or “line.”
if user mentioned all field except  leaverage  Consider this as normal trade command and fill all commands if user mentioned all field except leverage set leaverage to 1 (default)
user may set/edit  amount to zero  or clear amount in this conditons you should fill amount field 0 and assign null/none to other fields
maximum leverage is 1 and max is 50
"""

# -----------------------------
# 3️⃣ Initialize OpenAI client
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = cast("str", os.getenv("OPENAI_MODEL"))


# -----------------------------
# 4️⃣ Function to generate trade commands
# -----------------------------
def generate_trade_command(user_input: str) -> TradeCommand | None:
    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        response_format=TradeCommand,
    )
    return response.choices[0].message.parsed


# -----------------------------
# 5️⃣ Example Usage
# -----------------------------
if __name__ == "__main__":
    # Normal trade
    user_request = "Buy 1 ETH  long."
    trade_normal = generate_trade_command(user_request)
    if trade_normal:
        print("Normal Trade:", trade_normal.model_dump_json())

    # Edit trade (stateless)
    user_edit_request = "set amount to zero"
    trade_edit = generate_trade_command(user_edit_request)
    if trade_edit:
        print("Edit Trade:", trade_edit.model_dump_json())
