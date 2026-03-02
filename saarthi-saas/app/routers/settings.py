from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, SendingAccount, Subscription
from app.core.deps import get_current_user

router = APIRouter()


@router.get("")
async def get_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get sending accounts
    sa_q = await db.execute(
        select(SendingAccount).where(SendingAccount.user_id == user.id)
    )
    accounts = sa_q.scalars().all()

    # Get subscription
    sub_q = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = sub_q.scalar_one_or_none()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name or "",
            "company_name": user.company_name or "",
            "created_at": user.created_at.isoformat() if user.created_at else "",
        },
        "sending_accounts": [
            {
                "id": str(a.id),
                "provider": a.provider,
                "email": a.email,
                "is_active": a.is_active,
            }
            for a in accounts
        ],
        "subscription": {
            "plan_type": sub.plan_type if sub else "free",
            "subscription_status": sub.subscription_status if sub else "active",
            "monthly_limit": sub.monthly_limit if sub else 100,
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else "",
        } if sub else {
            "plan_type": "free",
            "subscription_status": "active",
            "monthly_limit": 100,
            "current_period_end": "",
        },
    }
