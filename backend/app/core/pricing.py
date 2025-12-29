# Pricing Configuration (Prices in the currency configured in Prodamus, usually RUB/USD)

# USD (International)
PRICE_PRO_MONTHLY_USD = 9.99
PRICE_PRO_YEARLY_USD = 99.00
PRICE_PREMIUM_MONTHLY_USD = 19.00
PRICE_PREMIUM_YEARLY_USD = 190.00

# RUB (Russia)
PRICE_PRO_MONTHLY_RUB = 490.00
PRICE_PRO_YEARLY_RUB = 3990.00
PRICE_PREMIUM_MONTHLY_RUB = 990.00
PRICE_PREMIUM_YEARLY_RUB = 7990.00

# Legacy mapping (defaulting to RUB for backward compatibility in some internal checks if needed, 
# but mostly we will switch to currency-aware lookups)
TIER_PRICES = {
    # Defaulting internal TIER_PRICES check to RUB for now as a fallback, 
    # but actual logic will check based on currency.
    "pro_monthly": PRICE_PRO_MONTHLY_RUB,
    "pro_yearly": PRICE_PRO_YEARLY_RUB,
    "premium_monthly": PRICE_PREMIUM_MONTHLY_RUB,
    "premium_yearly": PRICE_PREMIUM_YEARLY_RUB,
}

# Mapping of product names or IDs to internally used tier identifiers
PRODUCT_TO_TIER = {
    "VoiceBrain Pro Monthly": "pro_monthly",
    "VoiceBrain Pro Yearly": "pro_yearly",
}

def get_pricing_config():
    return {
        "usd": {
            "pro": { "monthly": PRICE_PRO_MONTHLY_USD, "yearly": PRICE_PRO_YEARLY_USD },
            "premium": { "monthly": PRICE_PREMIUM_MONTHLY_USD, "yearly": PRICE_PREMIUM_YEARLY_USD }
        },
        "rub": {
            "pro": { "monthly": PRICE_PRO_MONTHLY_RUB, "yearly": PRICE_PRO_YEARLY_RUB },
            "premium": { "monthly": PRICE_PREMIUM_MONTHLY_RUB, "yearly": PRICE_PREMIUM_YEARLY_RUB }
        }
    }
