from app.use_cases.base.contest import BaseContestUseCase
from app.services.registration_contest_service import RegistrationContestService

class RegistrationContestUseCase(
    BaseContestUseCase[RegistrationContestService]
):
    pass