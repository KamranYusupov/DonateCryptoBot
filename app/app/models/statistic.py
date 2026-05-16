from sqlalchemy import Column, BigInteger, text, CheckConstraint, Integer

from app.db.base import Base


class AdminStatistic(Base):
    __tablename__ = "admin_statistic"

    id = Column(Integer, primary_key=True, default=1)

    __table_args__ = (
        CheckConstraint("id = 1", name="admin_statistic_singleton"),
    )

    system_bill = Column(BigInteger, default=0, server_default=text("0"))
    donates_for_registration = Column(BigInteger, default=0, server_default=text("0"))