import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.models import Campaign, CampaignSendingAccount, SendingAccount
from app.services.billing import UsageService


class RotationService:
    @staticmethod
    def get_next_sending_account(db: Session, org_id: uuid.UUID, campaign_id: uuid.UUID) -> Optional[SendingAccount]:
        """
        Stateful round-robin rotation.
        MANDATORY: Uses ROW LEVEL LOCKING (FOR UPDATE) to prevent race conditions when updating the index.
        """
        # 1. Lock the campaign row
        campaign = db.query(Campaign).filter(
            Campaign.org_id == org_id, 
            Campaign.id == campaign_id
        ).with_for_update().first()

        if not campaign or campaign.status != "ACTIVE":
            return None

        # 2. Fetch all ordered campaign sending accounts
        accounts = db.query(CampaignSendingAccount).join(SendingAccount).filter(
            CampaignSendingAccount.org_id == org_id,
            CampaignSendingAccount.campaign_id == campaign_id,
            CampaignSendingAccount.is_active == True,
            SendingAccount.is_active == True
        ).order_by(CampaignSendingAccount.rotation_order).all()

        if not accounts:
            return None

        num_accounts = len(accounts)
        start_index = campaign.last_rotation_index % num_accounts

        # 3. Find the first eligible account (checking usage limits)
        for i in range(num_accounts):
            current_index = (start_index + i) % num_accounts
            candidate_account_assoc = accounts[current_index]

            if UsageService.check_limits_before_send(db, org_id, candidate_account_assoc.sending_account_id):
                # We found a valid account! Update the state index to point to the next theoretical one
                campaign.last_rotation_index = current_index + 1
                db.commit()

                # Fetch and return the actual sending account model
                return db.query(SendingAccount).filter_by(id=candidate_account_assoc.sending_account_id).first()

        # Unlock / release if none found
        db.rollback()
        return None
