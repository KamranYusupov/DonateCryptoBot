from sqlalchemy import Column, Float, text, CheckConstraint, Integer

from app.db.base import Base


class AdminStatistic(Base):
    __tablename__ = "admin_statistic"

    id = Column(Integer, primary_key=True, default=1)

    __table_args__ = (
        CheckConstraint("id = 1", name="admin_statistic_singleton"),
    )

    system_bill = Column(Float, default=0.0)
    triumph_system_bill = Column(Float, default=0.0)
    donates_sum_for_registration = Column(Float, default=0.0)