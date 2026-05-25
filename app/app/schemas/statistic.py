from typing import Optional

from pydantic import BaseModel, ConfigDict

digit_type = float | int


class AdminStatisticSchema(BaseModel):
    system_bill: digit_type
    triumph_system_bill: digit_type
    donates_sum_for_registration: digit_type

    model_config = ConfigDict(from_attributes=True)


class UpdateAdminStatisticSchema(BaseModel):
    system_bill: Optional[digit_type] = None
    triumph_system_bill: Optional[digit_type] = None
    donates_sum_for_registration: Optional[digit_type] = None

