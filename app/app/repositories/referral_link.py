import uuid

from app.models.referral_link import ReferralLink
from app.repositories.base import RepositoryBase
from app.exceptions.referral_link import ActiveLinkAlreadyExistsError


class RepositoryReferralLink(
    RepositoryBase[ReferralLink],
):
    """Репозиторий реферальных ссылок"""

    def generate_referral_link(
            self,
            telegram_user_id: uuid.UUID,
    ) -> ReferralLink:
        try:
            with self._session.begin_nested():
                referral_link = ReferralLink(
                    telegram_user_id=telegram_user_id
                )
                self._session.add(referral_link)
                self._session.flush()
                return referral_link

        except IntegrityError:
            raise ActiveLinkAlreadyExistsError(
                "У пользователя уже есть активная ссылка."
            )

