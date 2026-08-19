import logging
from typing import Any, Dict, List, Optional

from app.config import CONFIG
from app.helpers import safe_float, safe_int
from app.keyboards import pricing_keyboard


logger = logging.getLogger(
    "telegram-test-series-bot.pricing"
)


# ============================================================
# PRICING SERVICE
# ============================================================

class PricingService:
    """
    Premium pricing management.

    Features:
    - Multiple plans
    - Add / update / remove plans
    - Enable / disable plans
    - User-facing pricing
    - Admin pricing management
    """

    def __init__(self):

        self.plans: Dict[
            str,
            Dict[str, Any]
        ] = {}

        self._load_default_plans()

    # ========================================================
    # DEFAULT PLANS
    # ========================================================

    def _load_default_plans(self):

        default_price = safe_float(
            getattr(
                CONFIG,
                "TEST_PRICE",
                0,
            )
        )

        if default_price > 0:

            self.plans["premium"] = {
                "id": "premium",
                "name": "Premium",
                "price": default_price,
                "days": 30,
                "description": (
                    "Premium Test Series access"
                ),
                "enabled": True,
            }

        else:

            self.plans["premium"] = {
                "id": "premium",
                "name": "Premium",
                "price": 99,
                "days": 30,
                "description": (
                    "Premium Test Series access"
                ),
                "enabled": True,
            }

    # ========================================================
    # GET PLANS
    # ========================================================

    def get_plans(
        self,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:

        plans = list(
            self.plans.values()
        )

        if enabled_only:

            plans = [
                plan
                for plan in plans
                if plan.get(
                    "enabled",
                    True,
                )
            ]

        return sorted(
            plans,
            key=lambda item: safe_float(
                item.get(
                    "price",
                    0,
                )
            ),
        )

    # ========================================================
    # GET PLAN
    # ========================================================

    def get_plan(
        self,
        plan_id: str,
    ) -> Optional[Dict[str, Any]]:

        return self.plans.get(
            str(plan_id)
        )

    # ========================================================
    # ADD PLAN
    # ========================================================

    def add_plan(
        self,
        plan_id: str,
        name: str,
        price: float,
        days: int,
        description: str = "",
    ) -> Dict[str, Any]:

        plan_id = str(
            plan_id
        ).strip().lower()

        if not plan_id:

            raise ValueError(
                "Plan ID is required."
            )

        if plan_id in self.plans:

            raise ValueError(
                "यह plan पहले से मौजूद है।"
            )

        price = safe_float(
            price
        )

        days = max(
            1,
            safe_int(
                days,
                30,
            ),
        )

        if price < 0:

            raise ValueError(
                "Price negative नहीं हो सकती।"
            )

        plan = {
            "id": plan_id,
            "name": str(
                name
            ).strip() or plan_id,
            "price": price,
            "days": days,
            "description": str(
                description
            ).strip(),
            "enabled": True,
        }

        self.plans[
            plan_id
        ] = plan

        logger.info(
            "Pricing plan added: %s",
            plan_id,
        )

        return plan

    # ========================================================
    # UPDATE PLAN
    # ========================================================

    def update_plan(
        self,
        plan_id: str,
        *,
        name: Optional[str] = None,
        price: Optional[float] = None,
        days: Optional[int] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:

        plan = self.get_plan(
            plan_id
        )

        if not plan:

            return None

        if name is not None:

            plan["name"] = (
                str(name).strip()
                or plan["name"]
            )

        if price is not None:

            price = safe_float(
                price
            )

            if price < 0:

                raise ValueError(
                    "Price negative नहीं हो सकती।"
                )

            plan["price"] = price

        if days is not None:

            plan["days"] = max(
                1,
                safe_int(
                    days,
                    plan.get(
                        "days",
                        30,
                    ),
                ),
            )

        if description is not None:

            plan["description"] = (
                str(description).strip()
            )

        if enabled is not None:

            plan["enabled"] = bool(
                enabled
            )

        logger.info(
            "Pricing plan updated: %s",
            plan_id,
        )

        return plan

    # ========================================================
    # REMOVE PLAN
    # ========================================================

    def remove_plan(
        self,
        plan_id: str,
    ) -> bool:

        plan_id = str(
            plan_id
        )

        if plan_id not in self.plans:

            return False

        # कम से कम एक plan हमेशा available रहे।
        if len(self.plans) <= 1:

            raise ValueError(
                "कम से कम एक pricing plan रखना जरूरी है।"
            )

        del self.plans[
            plan_id
        ]

        logger.info(
            "Pricing plan removed: %s",
            plan_id,
        )

        return True

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def enable_plan(
        self,
        plan_id: str,
    ) -> bool:

        plan = self.get_plan(
            plan_id
        )

        if not plan:
            return False

        plan["enabled"] = True

        return True

    def disable_plan(
        self,
        plan_id: str,
    ) -> bool:

        plan = self.get_plan(
            plan_id
        )

        if not plan:
            return False

        plan["enabled"] = False

        return True

    # ========================================================
    # USER PRICING
    # ========================================================

    def user_keyboard(self):

        return pricing_keyboard(
            self.get_plans(
                enabled_only=True
            )
        )

    def user_text(self) -> str:

        plans = self.get_plans(
            enabled_only=True
        )

        if not plans:

            return (
                "💎 <b>PREMIUM PLANS</b>\n\n"
                "अभी कोई active plan available नहीं है।"
            )

        lines = [
            "💎 <b>PREMIUM PLANS</b>",
            "",
        ]

        for plan in plans:

            name = plan.get(
                "name",
                "Premium",
            )

            price = safe_float(
                plan.get(
                    "price",
                    0,
                )
            )

            days = safe_int(
                plan.get(
                    "days",
                    30,
                ),
                30,
            )

            description = plan.get(
                "description",
                "",
            )

            lines.append(
                f"💎 <b>{name}</b>"
            )

            lines.append(
                f"💰 Price: "
                f"<b>₹{price:g}</b>"
            )

            lines.append(
                f"⏳ Validity: "
                f"<b>{days} Days</b>"
            )

            if description:

                lines.append(
                    f"📝 {description}"
                )

            lines.append("")

        lines.append(
            "👇 अपना plan select करें।"
        )

        return "\n".join(
            lines
        )

    # ========================================================
    # ADMIN PRICING
    # ========================================================

    def admin_text(self) -> str:

        plans = self.get_plans(
            enabled_only=False
        )

        if not plans:

            return (
                "💰 <b>PRICING SETTINGS</b>\n\n"
                "कोई plan configured नहीं है।"
            )

        lines = [
            "💰 <b>PRICING SETTINGS</b>",
            "",
        ]

        for index, plan in enumerate(
            plans,
            start=1,
        ):

            status = (
                "🟢 ON"
                if plan.get(
                    "enabled",
                    True,
                )
                else "🔴 OFF"
            )

            lines.append(
                (
                    f"<b>{index}.</b> "
                    f"{plan.get('name')}\n"
                    f"🆔 <code>{plan.get('id')}</code>\n"
                    f"💰 ₹{safe_float(plan.get('price', 0)):g}\n"
                    f"⏳ {safe_int(plan.get('days', 30), 30)} days\n"
                    f"📌 {status}"
                )
            )

            lines.append("")

        return "\n".join(
            lines
        )

    # ========================================================
    # SELECT PLAN
    # ========================================================

    def select_plan(
        self,
        plan_id: str,
    ) -> Optional[Dict[str, Any]]:

        plan = self.get_plan(
            plan_id
        )

        if not plan:

            return None

        if not plan.get(
            "enabled",
            True,
        ):

            return None

        return plan

    # ========================================================
    # PURCHASE TEXT
    # ========================================================

    def purchase_text(
        self,
        plan_id: str,
    ) -> str:

        plan = self.select_plan(
            plan_id
        )

        if not plan:

            return (
                "❌ यह plan available नहीं है।"
            )

        name = plan.get(
            "name",
            "Premium",
        )

        price = safe_float(
            plan.get(
                "price",
                0,
            )
        )

        days = safe_int(
            plan.get(
                "days",
                30,
            ),
            30,
        )

        description = plan.get(
            "description",
            "",
        )

        text = (
            "💎 <b>PLAN DETAILS</b>\n"
            "\n"
            f"📦 Plan: <b>{name}</b>\n"
            f"💰 Price: <b>₹{price:g}</b>\n"
            f"⏳ Validity: <b>{days} Days</b>\n"
        )

        if description:

            text += (
                f"📝 {description}\n"
            )

        text += (
            "\n"
            "💳 Payment करने के बाद "
            "payment screenshot भेजें।\n"
            "Admin verification के बाद premium access मिलेगा।"
        )

        return text


# ============================================================
# GLOBAL SERVICE
# ============================================================

pricing_service = PricingService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_pricing_plans():

    return pricing_service.get_plans()


def get_plan(
    plan_id: str,
):

    return pricing_service.get_plan(
        plan_id
    )


def add_pricing_plan(
    plan_id: str,
    name: str,
    price: float,
    days: int,
    description: str = "",
):

    return pricing_service.add_plan(
        plan_id=plan_id,
        name=name,
        price=price,
        days=days,
        description=description,
    )


def update_pricing_plan(
    plan_id: str,
    **kwargs,
):

    return pricing_service.update_plan(
        plan_id,
        **kwargs,
    )


def remove_pricing_plan(
    plan_id: str,
):

    return pricing_service.remove_plan(
        plan_id
    )


# ============================================================
# TELEGRAM DISPLAY
# ============================================================

async def show_pricing(
    update,
    context,
):

    try:

        text = pricing_service.user_text()

        keyboard = (
            pricing_service.user_keyboard()
        )

        if update.callback_query:

            query = (
                update.callback_query
            )

            try:

                await query.answer()

            except Exception:

                pass

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

            return

        if update.effective_message:

            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    except Exception:

        logger.exception(
            "Failed to show pricing."
        )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "PricingService",
    "pricing_service",
    "get_pricing_plans",
    "get_plan",
    "add_pricing_plan",
    "update_pricing_plan",
    "remove_pricing_plan",
    "show_pricing",
]
