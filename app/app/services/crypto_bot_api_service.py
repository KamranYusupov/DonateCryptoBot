from decimal import Decimal
from typing import Dict, Optional

import aiohttp
import loguru

from app.core.config import settings


class CryptoBotAPIService:

    def __init__(
        self,
        base_url: str = settings.crypto_bot_api_base_url,
        api_token: str = settings.crypto_bot_api_token,
    ):
        self.base_url = base_url
        self.__api_token = api_token

    async def create_invoice(
            self,
            amount: Decimal,
            description: str,
            payload: str,
            asset: str = "USDT",
    ):
        method = "createInvoice"
        url = f"{self.base_url}{method}"

        headers = {"Crypto-Pay-API-Token": self.__api_token}

        data = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "payload": payload,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as resp:
                return await resp.json()

    async def get_invoices(self):
        method = "getInvoices"
        url = f"{self.base_url}{method}"

        headers = {"Crypto-Pay-API-Token": self.__api_token}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                return await resp.json()

    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict]:
        response_data = await self.get_invoices()
        invoices = response_data.get("result", {}).get("items")

        if not invoices:
            return None

        for iv in invoices:
            if iv["invoice_id"] == invoice_id:
                return iv

        return None