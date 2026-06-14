from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AdminStatisticSchema(BaseModel):
    system_bill: Decimal
    triumph_system_bill: Decimal
    donates_sum_for_registration: Decimal

    model_config = ConfigDict(from_attributes=True)


class UpdateAdminStatisticSchema(BaseModel):
    system_bill: Optional[Decimal] = None
    triumph_system_bill: Optional[Decimal] = None
    donates_sum_for_registration: Optional[Decimal] = None

