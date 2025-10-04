import sys
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import cast
import json

load_dotenv()

# -----------------------------
# 1️⃣ Load supported tokens from markets.json
# -----------------------------
TOKENS_FILE = "markets.json"


class Market(BaseModel):
    id: int
    name: str
    symbol: str
    asset: str
    pricePrecision: int
    quantityPrecision: int
    isValid: bool
    minAcceptableQuoteValue: float
    minAcceptablePortionLF: str
    tradingFee: str
    maxLeverage: int
    maxNotionalValue: int
    maxFundingRate: str
    rfqAllowed: bool
    hedgerFeeOpen: str
    hedgerFeeClose: str
    autoSlippage: float


with open(TOKENS_FILE, "r") as f:
    raw_data = json.load(f)

markets = [Market(**entry) for entry in raw_data]

# Extract list of (SYMBOL, NAME)
SUPPORTED_TOKENS_WITH_NAMES = [(m.symbol.upper(), m.name) for m in markets]
SUPPORTED_TOKENS = [sym for sym, _ in SUPPORTED_TOKENS_WITH_NAMES]


# -----------------------------
# 2️⃣ Define structured schema
# -----------------------------
class TradeCommand(BaseModel):
    amount: Optional[float] = None
    token: Optional[str] = None
    leverage: Optional[int] = None
    position: Optional[str] = None  # "long" or "short"
    edit: bool


# -----------------------------
# 3️⃣ System prompt with symbol + name
# -----------------------------
SYSTEM_PROMPT = f"""
You are a trading assistant. Only output JSON with the following fields:
- amount: float
- token: symbol string (must be one of the supported coins)
- leverage: int (1 to 50, default=1 if missing)
- position: "long" or "short"
- edit: boolean

Rules:
1. If user starts a new trade → edit=false. Fill all fields.
2. If user edits a trade → edit=true. Only include changed fields, others must be null.
3. If amount is zero → amount=0 and all other fields=null.
4. If token is not clearly one of the supported tokens → token=null.
5. User may mention coin by name (e.g., 'Ethereum') or by symbol (e.g., 'ETH') or with typos. Always resolve to the correct symbol.
6. Never output extra text, only JSON.

Supported tokens (symbol – name):
{", ".join(f"{sym} – {name}" for sym, name in SUPPORTED_TOKENS_WITH_NAMES)}
"""

print(SYSTEM_PROMPT)
# -----------------------------
# 4️⃣ Initialize OpenAI client
# -----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = cast("str", os.getenv("OPENAI_MODEL"))


# -----------------------------
# 5️⃣ Generate trade commands
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
    trade = response.choices[0].message.parsed

    # ✅ Normalize and validate token
    if trade and trade.token:
        token_upper = trade.token.upper()
        if token_upper in SUPPORTED_TOKENS:
            trade.token = token_upper
        else:
            trade.token = None

    return trade


# -----------------------------
# 6️⃣ Example Usage
# -----------------------------
if __name__ == "__main__":
    # Normal trade
    user_request = "Buy 1 Ethereum long."  # should resolve to ETH
    trade_normal = generate_trade_command(user_request)
    if trade_normal:
        print("Normal Trade:", trade_normal.model_dump_json())

    # Edit trade
    user_edit_request = "set amount to zero"
    trade_edit = generate_trade_command(user_edit_request)
    if trade_edit:
        print("Edit Trade:", trade_edit.model_dump_json())
