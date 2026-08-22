from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Hunt, HuntResult, Notification, ScoutRecommendation, Event, User

class AutomationService:
    """V1 synchronous automation runner.

    This gives SpinningLicorice the job contracts now. A real queue/cron worker can
    invoke these methods later without changing domain behavior.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def generate_hunter_notifications(self) -> int:
        count = 0
        hunts = self.db.execute(
            select(Hunt).where(
                Hunt.user_id == self.user.id,
                Hunt.is_active.is_(True),
                Hunt.is_auto.is_(True),
            )
        ).scalars().all()

        for hunt in hunts:
            results = self.db.execute(
                select(HuntResult)
                .where(HuntResult.hunt_id == hunt.id, HuntResult.spinninglicorice_score >= 85)
                .order_by(HuntResult.spinninglicorice_score.desc())
                .limit(3)
            ).scalars().all()

            for result in results:
                key = f"hunt:{hunt.id}:result:{result.id}"
                exists = self.db.scalar(
                    select(Notification.id).where(
                        Notification.user_id == self.user.id,
                        Notification.notification_type == "hunter_match",
                        Notification.payload["dedupe_key"].astext == key,
                    ).limit(1)
                )
                if exists:
                    continue
                self.db.add(
                    Notification(
                        user_id=self.user.id,
                        notification_type="hunter_match",
                        title=f"🔥 {hunt.name}",
                        body=result.explanation or f"SpinningLicorice Score {result.spinninglicorice_score}",
                        payload={
                            "dedupe_key": key,
                            "hunt_id": str(hunt.id),
                            "hunt_result_id": str(result.id),
                            "score": result.spinninglicorice_score,
                        },
                    )
                )
                count += 1

        self.db.commit()
        return count

    def generate_scout_notifications(self) -> int:
        count = 0
        rows = self.db.execute(
            select(ScoutRecommendation, Event)
            .join(Event, ScoutRecommendation.event_id == Event.id)
            .where(
                ScoutRecommendation.user_id == self.user.id,
                ScoutRecommendation.match_score >= 88,
            )
            .order_by(ScoutRecommendation.match_score.desc())
            .limit(5)
        ).all()

        for rec, event in rows:
            key = f"scout:{rec.id}"
            exists = self.db.scalar(
                select(Notification.id).where(
                    Notification.user_id == self.user.id,
                    Notification.notification_type == "scout_match",
                    Notification.payload["dedupe_key"].astext == key,
                ).limit(1)
            )
            if exists:
                continue
            self.db.add(
                Notification(
                    user_id=self.user.id,
                    notification_type="scout_match",
                    title=f"🎸 {event.name}",
                    body=rec.reason or f"{rec.match_score}% Scout match",
                    payload={
                        "dedupe_key": key,
                        "scout_recommendation_id": str(rec.id),
                        "event_id": str(event.id),
                        "score": rec.match_score,
                    },
                )
            )
            count += 1

        self.db.commit()
        return count
